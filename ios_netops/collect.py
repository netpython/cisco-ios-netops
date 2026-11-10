"""Read-only command collection with live and replay sources."""

import argparse
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

COMMANDS = {
    "version": "show version",
    "inventory": "show inventory",
    "ports": "show interfaces status",
    "lldp": "show lldp neighbors detail",
    "trunks": "show interfaces trunk",
    "config": "show running-config",
}
CLI_ERROR = re.compile(
    r"^\s*%\s*(?:invalid input|incomplete command|ambiguous command|"
    r"authorization|access denied|unrecognized command|.*not enabled)",
    re.IGNORECASE | re.MULTILINE,
)


class CollectionError(RuntimeError):
    """An output was unavailable or unusable."""


def add_source(parser, *, fleet=False):
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", type=Path, help="Replay a directory of raw command outputs")
    source.add_argument("--inventory" if fleet else "--host")
    parser.add_argument("--username", default=os.getenv("IOS_USERNAME"))
    parser.add_argument("--key-file")
    parser.add_argument("--port", type=int, default=22)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


@contextmanager
def collector(args, *, host=None, fixture=None):
    fixture = fixture or args.fixture
    if fixture:
        def read(key):
            path = fixture / (key + ".txt")
            try:
                return validate(key, path.read_text(encoding="utf-8"))
            except OSError as exc:
                raise CollectionError(f"Missing replay output: {key}") from exc
        yield read
        return

    if not args.username:
        raise CollectionError("Set IOS_USERNAME or pass --username")
    password = os.getenv("IOS_PASSWORD")
    if not password and not args.key_file:
        raise CollectionError("Set IOS_PASSWORD or pass --key-file")
    try:
        from netmiko import ConnectHandler
        from netmiko.exceptions import NetmikoBaseException
        from paramiko import SSHException
    except ImportError as exc:
        raise CollectionError("Install requirements.txt for live SSH") from exc

    connection = None
    try:
        connection = ConnectHandler(
            device_type="cisco_ios", host=host or args.host, port=args.port,
            username=args.username, password=password, use_keys=bool(args.key_file),
            key_file=args.key_file, allow_agent=False, ssh_strict=True,
            system_host_keys=True, conn_timeout=10, auth_timeout=15, banner_timeout=15,
        )

        def read(key):
            try:
                return validate(key, connection.send_command(COMMANDS[key], read_timeout=45))
            except (NetmikoBaseException, SSHException, OSError) as exc:
                raise CollectionError(f"{COMMANDS[key]} failed ({type(exc).__name__})") from exc

        yield read
    except (NetmikoBaseException, SSHException, OSError) as exc:
        raise CollectionError(f"SSH failed ({type(exc).__name__})") from exc
    finally:
        if connection:
            connection.disconnect()


def validate(key, output):
    if not output.strip() or CLI_ERROR.search(output):
        raise CollectionError(f"{COMMANDS[key]} returned no usable output")
    return output


def run(main):
    try:
        raise SystemExit(main())
    except (CollectionError, OSError, ValueError) as exc:
        import sys
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
