"""Capture trunk and LLDP state, then classify changes against an approved plan."""

import argparse
from pathlib import Path

from ios_netops.collect import CollectionError, add_source, collector, load_json, run, write_json
from ios_netops.parse import lldp, trunks
from ios_netops.report import html_report

COLUMNS = ("status", "check", "key", "change", "detail")
CHECKS = {"trunks": trunks, "lldp": lldp}


def capture(args):
    snapshot = {"checks": {}, "errors": {}}
    try:
        with collector(args) as read:
            for check, parse in CHECKS.items():
                try:
                    snapshot["checks"][check] = parse(read(check))
                except (CollectionError, ValueError) as exc:
                    snapshot["errors"][check] = str(exc)
    except CollectionError as exc:
        snapshot["errors"].update(dict.fromkeys(CHECKS, str(exc)))
    write_json(args.output, snapshot)
    print(args.output)
    return 2 if snapshot["errors"] else 0


def trunk_changes(before, after):
    for port in sorted(before.keys() | after.keys()):
        if port not in before:
            yield "trunks", port, "trunk_added"
        elif port not in after:
            yield "trunks", port, "trunk_removed"
        else:
            previous, current = set(before[port]), set(after[port])
            for vlan in sorted(previous - current):
                yield "trunks", f"{port}:{vlan}", "vlan_removed"
            for vlan in sorted(current - previous):
                yield "trunks", f"{port}:{vlan}", "vlan_added"


def lldp_changes(before, after):
    def neighbors(rows):
        return {f"{row['local_port']}|{row['chassis_id']}|{row['remote_port']}|"
                f"{row['system_name'] or ''}" for row in rows}

    previous, current = neighbors(before), neighbors(after)
    yield from (("lldp", key, "neighbor_removed") for key in sorted(previous - current))
    yield from (("lldp", key, "neighbor_added") for key in sorted(current - previous))


def compare(args):
    before, after = load_json(args.before), load_json(args.after)
    planned = load_json(args.expected) if args.expected else []
    if not isinstance(planned, list) or any(
        not isinstance(row, dict) or any(not isinstance(row.get(key), str)
                                         for key in ("check", "key", "change"))
        or row["check"] not in CHECKS for row in planned
    ):
        raise ValueError("Expected changes must be a list with check, key and change strings")
    expected = {(row["check"], row["key"], row["change"]) for row in planned}
    rows = []
    unavailable = set()
    actual = set()
    for check, changes in (("trunks", trunk_changes), ("lldp", lldp_changes)):
        missing = []
        for label, snapshot in (("before", before), ("after", after)):
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("checks"), dict):
                raise ValueError(f"Invalid {label} snapshot; use the capture command")
            error = snapshot.get("errors", {}).get(check)
            if error or check not in snapshot["checks"]:
                missing.append(f"{label}: {error or 'missing check'}")
        if missing:
            unavailable.add(check)
            rows.append({"status": "unavailable", "check": check, "detail": " | ".join(missing)})
        else:
            try:
                actual.update(changes(before["checks"][check], after["checks"][check]))
            except (KeyError, TypeError, AttributeError) as exc:
                raise ValueError(f"Invalid snapshot data for {check}") from exc

    for check, key, change in sorted(actual | expected):
        item = check, key, change
        if check in unavailable:
            continue
        status = "expected" if item in actual and item in expected else (
            "unexpected" if item in actual else "missing_expected"
        )
        rows.append(dict(status=status, check=check, key=key, change=change))
    for check in sorted(CHECKS.keys() - unavailable - {item[0] for item in actual | expected}):
        rows.append(dict(status="unchanged", check=check))
    html_report(args.output, "IOS change validation", COLUMNS, rows)
    print(f"{args.output} ({len(rows)} results)")
    if unavailable:
        return 2
    return int(any(row["status"] in {"unexpected", "missing_expected"} for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    capture_parser = sub.add_parser("capture")
    add_source(capture_parser)
    capture_parser.add_argument("--output", type=Path, required=True)
    capture_parser.set_defaults(handler=capture)
    compare_parser = sub.add_parser("compare")
    for argument in ("before", "after", "output"):
        compare_parser.add_argument("--" + argument, type=Path, required=True)
    compare_parser.add_argument("--expected", type=Path)
    compare_parser.set_defaults(handler=compare)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    run(main)
