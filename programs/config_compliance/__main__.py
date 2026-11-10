"""Evaluate an IOS configuration against explicit YAML policies."""

import argparse
from pathlib import Path
import re

from ios_netops.collect import run
from ios_netops.report import csv_report

COLUMNS = ("rule", "status", "scope", "line", "evidence")
REDACT = re.compile(r"\b(?:password|secret|community|key-string|authentication-key|key)\b", re.I)


def parse_config(text):
    sections = {"global": {"global": []}, "vty": {}, "interface": {}}
    active = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if raw[0].isspace():
            if active is not None:
                active.append((number, line))
            continue
        active = None
        if line.startswith("line vty ") or line.startswith("interface "):
            scope = "vty" if line.startswith("line vty ") else "interface"
            active = sections[scope].setdefault(line, [])
        elif line != "!" and not line.startswith(("Building configuration", "Current configuration")):
            sections["global"]["global"].append((number, line))
    if not sections["global"]["global"] or not re.search(r"(?m)^end\s*$", text):
        raise ValueError("Expected a complete running configuration ending in 'end'")
    return sections


def load_rules(path):
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("Install requirements.txt to read YAML policies") from exc
    try:
        rules = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError("Invalid policy YAML") from exc
    if not isinstance(rules, list) or not rules:
        raise ValueError("Policy must be a nonempty list of rules")
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict) or any(
            not isinstance(rule.get(key), str) or not rule[key].strip()
            for key in ("id", "scope", "pattern", "mode")
        ):
            raise ValueError("Rules require id, scope, pattern and mode strings")
        if rule["id"] in seen or rule["scope"] not in {"global", "vty", "interface"}:
            raise ValueError(f"Duplicate rule or invalid scope: {rule['id']}")
        if rule["mode"] not in {"require", "forbid"}:
            raise ValueError(f"Invalid mode for rule {rule['id']}")
        seen.add(rule["id"])
        try:
            rule["compiled"] = re.compile(rule["pattern"], re.I)
        except re.error as exc:
            raise ValueError(f"Invalid regex for rule {rule['id']}") from exc
    return rules


def evaluate(sections, rules):
    for rule in rules:
        blocks = sections[rule["scope"]]
        if not blocks:
            yield dict(rule=rule["id"], status="unavailable", scope=rule["scope"],
                       evidence="No matching configuration blocks")
            continue
        for label, lines in blocks.items():
            match = next(((number, text) for number, text in lines
                          if rule["compiled"].search(text)), None)
            passed = bool(match) == (rule["mode"] == "require")
            evidence = "No matching command"
            if match:
                evidence = "[redacted]" if REDACT.search(match[1]) else match[1]
            yield dict(rule=rule["id"], status="pass" if passed else "fail",
                       scope=label, line=match[0] if match else None, evidence=evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("config", "policy", "output"):
        parser.add_argument("--" + argument, type=Path, required=True)
    args = parser.parse_args()
    rules = load_rules(args.policy)
    sections = parse_config(args.config.read_text(encoding="utf-8"))
    rows = list(evaluate(sections, rules))
    csv_report(args.output, COLUMNS, rows)
    for status in ("pass", "fail", "unavailable"):
        print(f"{status}: {sum(row['status'] == status for row in rows)}")
    print(args.output)
    return 2 if any(row["status"] == "unavailable" for row in rows) else int(
        any(row["status"] == "fail" for row in rows)
    )


if __name__ == "__main__":
    run(main)
