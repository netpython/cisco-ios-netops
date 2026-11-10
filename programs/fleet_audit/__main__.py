"""Collect fleet health and publish per-device CSV and HTML reports."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ios_netops.collect import CollectionError, add_source, collector, load_json, run
from ios_netops.parse import ports, software
from ios_netops.report import csv_report, html_report

COLUMNS = ("device", "status", "hostname", "version", "target_version",
           "ports_up", "ports_total", "detail")


def audit(args, entry, fixture):
    row = {"device": entry["host"], "target_version": entry["target_version"]}
    errors = []
    try:
        with collector(args, host=entry["host"], fixture=fixture) as read:
            try:
                row.update(software(read("version")))
            except (CollectionError, ValueError) as exc:
                errors.append(str(exc))
            try:
                interfaces = ports(read("ports"))
                row.update(ports_total=len(interfaces),
                           ports_up=sum(port["status"] == "connected" for port in interfaces))
            except (CollectionError, ValueError) as exc:
                errors.append(str(exc))
    except CollectionError as exc:
        errors.append(str(exc))

    mismatch = bool(row.get("version") and row["version"] != row["target_version"])
    if mismatch:
        errors.append("Software version differs from inventory target")
    row["status"] = (
        "incomplete" if "version" not in row or "ports_total" not in row
        else "drift" if mismatch else "ok"
    )
    row["detail"] = " | ".join(errors)
    return row


def read_inventory(path):
    entries = load_json(path)
    if not isinstance(entries, list) or not entries:
        raise ValueError("Inventory must be a nonempty JSON list")
    hosts = set()
    for entry in entries:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(key), str) or not entry[key].strip()
            for key in ("host", "target_version")
        ):
            raise ValueError("Every inventory entry needs a host and target_version")
        if entry["host"] in hosts:
            raise ValueError(f"Duplicate host: {entry['host']}")
        hosts.add(entry["host"])
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser, fleet=True)
    parser.add_argument("--workers", type=int, default=5, choices=range(1, 21), metavar="1..20")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    entries = read_inventory(args.fixture / "inventory.json" if args.fixture else args.inventory)

    def worker(entry):
        replay = None
        if args.fixture:
            host = entry["host"]
            if Path(host).name != host or host in {".", ".."}:
                return {"device": host, "status": "incomplete", "detail": "Invalid replay host label"}
            replay = args.fixture / host
        return audit(args, entry, replay)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(worker, entries))
    csv_report(args.output_dir / "fleet.csv", COLUMNS, rows)
    html_report(args.output_dir / "fleet.html", "IOS fleet audit", COLUMNS, rows)
    print(f"{args.output_dir} ({len(rows)} devices)")
    return 2 if any(row["status"] == "incomplete" for row in rows) else int(
        any(row["status"] == "drift" for row in rows)
    )


if __name__ == "__main__":
    run(main)
