"""Export the switchport status table to CSV."""

import argparse
from pathlib import Path

from ios_netops.collect import add_source, collector, run
from ios_netops.parse import ports
from ios_netops.report import csv_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with collector(args) as read:
        rows = ports(read("ports"))
    csv_report(args.output, ("port", "name", "status", "vlan", "duplex", "speed", "type"), rows)
    print(f"{args.output} ({len(rows)} ports)")


if __name__ == "__main__":
    run(main)
