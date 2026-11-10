"""Export LLDP neighbor details to CSV."""

import argparse
from pathlib import Path

from ios_netops.collect import add_source, collector, run
from ios_netops.parse import lldp
from ios_netops.report import csv_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with collector(args) as read:
        rows = lldp(read("lldp"))
    csv_report(args.output, ("local_port", "remote_port", "chassis_id", "system_name"), rows)
    print(f"{args.output} ({len(rows)} neighbors)")


if __name__ == "__main__":
    run(main)
