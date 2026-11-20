"""Export the global IPv4 ARP table to CSV without clearing neighbor state."""
import argparse
import sys
from pathlib import Path

from ios_netops.arp import arp_entries
from ios_netops.collect import add_source, collector, run
from ios_netops.report import csv_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with collector(args) as read:
        rows = arp_entries(read("arp"))
    csv_report(args.output, ("address", "mac", "age_minutes", "interface", "state"), rows)
    print(f"{args.output} ({len(rows)} ARP entries)")


if __name__ == "__main__":
    try:
        run(main)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
