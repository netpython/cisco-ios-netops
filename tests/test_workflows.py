import csv
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

from ios_netops.collect import CollectionError
from ios_netops.parse import lldp, ports, trunks, vlan_set


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name)

    def cli(self, module, *args, status=0):
        result = subprocess.run(
            [sys.executable, "-m", module, *map(str, args)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, status, result.stderr)
        return result.stdout

    def test_scripts(self):
        root = "examples/before"
        target = self.output / "inventory.json"
        self.cli("scripts.collect_device_inventory", "--fixture", root, "--output", target)
        self.assertEqual(len(json.loads(target.read_text())["components"]), 2)
        for module, expected in (("export_switchport_status", 3), ("export_lldp_neighbors", 1)):
            target = self.output / (module + ".csv")
            self.cli("scripts." + module, "--fixture", root, "--output", target)
            with target.open(newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), expected)
        self.cli("scripts.backup_running_config", "--fixture", root, "--output-dir", self.output)
        backup, = self.output.glob("*.cfg")
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertIn("hostname edge-a", backup.read_text())

    def test_change_validation(self):
        module = "programs.change_validation"
        before, after = self.output / "before.json", self.output / "after.json"
        report = self.output / "changes.html"
        for label, target in (("before", before), ("after", after)):
            self.cli(module, "capture", "--fixture", "examples/" + label, "--output", target)
        self.cli(module, "compare", "--before", before, "--after", after,
                 "--expected", "examples/expected-change.json", "--output", report, status=1)
        self.assertIn("vlan_removed", report.read_text())
        self.assertIn("Gi1/0/24:30", report.read_text())
        self.assertIn("<td>expected</td>", report.read_text())
        self.cli(module, "compare", "--before", before, "--after", before, "--output", report)
        self.assertIn("unchanged", report.read_text())
        self.cli(module, "capture", "--fixture", self.output, "--output", after, status=2)
        self.cli(module, "compare", "--before", before, "--after", after,
                 "--output", report, status=2)
        self.assertIn("unavailable", report.read_text())

    def test_fleet_report_preserves_partial_results(self):
        self.cli("programs.fleet_audit", "--fixture", "examples/fleet",
                 "--output-dir", self.output, status=2)
        with (self.output / "fleet.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["status"] for row in rows], ["ok", "drift", "incomplete"])
        self.assertEqual(rows[2]["ports_total"], "")

    def test_compliance_evaluates_each_vty_range(self):
        report = self.output / "compliance.csv"
        self.cli("programs.config_compliance", "--config", "examples/configs/edge-a.txt",
                 "--policy", "examples/policy.yml", "--output", report, status=1)
        with report.open(newline="") as handle:
            vty = [row for row in csv.DictReader(handle) if row["rule"] == "VTY_SSH_ONLY"]
        self.assertEqual([row["status"] for row in vty], ["fail", "pass"])

    def test_empty_and_invalid_output_are_distinct(self):
        self.assertEqual(lldp("Total entries displayed: 0"), [])
        self.assertEqual(trunks("Port Mode Encapsulation Status Native vlan"), {})
        self.assertEqual(vlan_set("2-4,3,10"), [2, 3, 4, 10])
        with self.assertRaises(CollectionError):
            lldp("% Invalid input")
        with self.assertRaises(CollectionError):
            ports("Command rejected")


if __name__ == "__main__":
    unittest.main()
