"""Save a running configuration locally using owner-only file permissions."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re

from ios_netops.collect import add_source, collector, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source(parser)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    with collector(args) as read:
        config = read("config")
    label = re.sub(r"[^A-Za-z0-9_.-]", "_", args.host or args.fixture.name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = args.output_dir / f"{label}-{timestamp}.cfg"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(config.rstrip() + "\n")
    except OSError:
        path.unlink(missing_ok=True)
        raise
    print(path)


if __name__ == "__main__":
    run(main)
