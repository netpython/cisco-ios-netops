"""Strict parser for the classic IPv4 'show ip arp' table."""
import ipaddress
import re

from ios_netops.collect import CollectionError

HEADER = re.compile(r"^Protocol\s+Address\s+Age\s+\(min\)\s+Hardware Addr\s+Type\s+Interface$", re.I)
MAC = re.compile(r"^(?:[0-9a-f]{4}\.){2}[0-9a-f]{4}$", re.I)


def arp_entries(output):
    """Return normalized rows; reject unknown layouts rather than silently truncate."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or not HEADER.fullmatch(lines[0]):
        raise CollectionError("Unsupported ARP table header; retain the raw output for review")
    rows = []
    for number, line in enumerate(lines[1:], 2):
        fields = line.split()
        if len(fields) not in (5, 6) or fields[0] != "Internet":
            raise CollectionError(f"Unsupported ARP row at line {number}")
        _, address, age, hardware, kind, *interface = fields
        try:
            address = str(ipaddress.IPv4Address(address))
        except ipaddress.AddressValueError as exc:
            raise CollectionError(f"Invalid IPv4 address at line {number}") from exc
        if age != "-" and not age.isdecimal():
            raise CollectionError(f"Invalid ARP age at line {number}")
        incomplete = hardware.lower() == "incomplete"
        if not incomplete and not MAC.fullmatch(hardware):
            raise CollectionError(f"Unsupported MAC format at line {number}")
        if kind != "ARPA":
            raise CollectionError(f"Unsupported ARP encapsulation at line {number}")
        if not incomplete and not interface:
            raise CollectionError(f"Missing interface at line {number}")
        mac = "" if incomplete else ":".join(
            hardware.replace(".", "").lower()[i:i + 2] for i in range(0, 12, 2)
        )
        rows.append({
            "address": address, "mac": mac,
            "age_minutes": "" if age == "-" else age,
            "interface": interface[0] if interface else "",
            "state": "incomplete" if incomplete else "resolved",
        })
    return rows
