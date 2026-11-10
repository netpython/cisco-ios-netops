"""Export software and hardware inventory as JSON."""

import argparse
from pathlib import Path

from ios_netops.collect import add_source, collector, run, write_json
from ios_netops.parse import inventory, software


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with collector(args) as read:
        result = software(read("version"))
        result["components"] = inventory(read("inventory"))
    write_json(args.output, result)
    print(args.output)


if __name__ == "__main__":
    run(main)
