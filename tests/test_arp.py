import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ios_netops.arp import arp_entries
from ios_netops.collect import CollectionError
from scripts.export_arp_table import main

HEADER = "Protocol  Address  Age (min)  Hardware Addr  Type  Interface\n"


class ArpTests(unittest.TestCase):
    def test_resolved_local_and_incomplete(self):
        rows = arp_entries(Path("examples/arp/arp.txt").read_text())
        self.assertEqual(rows[0]["age_minutes"], "")
        self.assertEqual(rows[1]["mac"], "02:00:00:00:00:50")
        self.assertEqual(rows[2]["state"], "incomplete")
        self.assertEqual(rows[2]["interface"], "")
        self.assertEqual(rows[2]["mac"], "")

    def test_empty_table(self):
        self.assertEqual(arp_entries(HEADER), [])

    def test_duplicate_ip_on_distinct_interfaces_preserved(self):
        row = "Internet 192.0.2.50 2 0200.0000.0050 ARPA "
        rows = arp_entries(HEADER + row + "Gi0/0\n" + row + "Gi0/1\n")
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["interface"], rows[1]["interface"])

    def test_invalid_rows_rejected(self):
        for row in [
            "Internet 999.0.2.50 2 0200.0000.0050 ARPA Gi0/0",
            "Internet 192.0.2.50 age 0200.0000.0050 ARPA Gi0/0",
            "Internet 192.0.2.50 2 bad-mac ARPA Gi0/0",
            "Internet 192.0.2.50 2 0200.0000.0050 ARPA",
            "Internet 192.0.2.50 2 0200.0000.0050 SNAP Gi0/0",
            "unexpected trailing output",
        ]:
            with self.subTest(row=row), self.assertRaises(CollectionError):
                arp_entries(HEADER + row)

    def test_bad_header_rejected(self):
        for value in ["", "% Invalid input detected", "Address Hardware"]:
            with self.subTest(value=value), self.assertRaises(CollectionError):
                arp_entries(value)

    def test_cli_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "arp.csv"
            result = subprocess.run([sys.executable, "-m", "scripts.export_arp_table",
                                     "--fixture", "examples/arp", "--output", str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with target.open(newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 3)

    def test_cli_missing_input(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "arp.csv"
            result = subprocess.run([sys.executable, "-m", "scripts.export_arp_table",
                                     "--fixture", folder, "--output", str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())

    def test_interrupt_propagates_to_cli_handler(self):
        with patch("sys.argv", ["export_arp_table", "--fixture", "examples/arp",
                                "--output", "unused.csv"]), patch(
                "scripts.export_arp_table.collector", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                main()
