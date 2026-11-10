"""Parsers for IOS command output. Unexpected formats fail explicitly."""

import re

from .collect import CollectionError


def software(text):
    matches = re.findall(r"(?mi)^Cisco IOS(?: XE)? Software[^\n]*?\bVersion\s+([^,\s]+)", text)
    if not matches:
        raise CollectionError("Unrecognized show version output")
    hostname = re.search(r"(?m)^(\S+) uptime is ", text)
    return {"hostname": hostname[1] if hostname else None, "version": matches[0]}


def inventory(text):
    pattern = (
        r'(?m)^NAME:\s*"([^"]+)"\s*,\s*DESCR:\s*"([^"]*)"\s*\n'
        r'PID:\s*([^,]*),\s*VID:\s*([^,]*),\s*SN:[ \t]*([^\r\n]*)'
    )
    keys = ("name", "description", "model", "revision", "serial")
    rows = [dict(zip(keys, (field.strip() or None for field in row)))
            for row in re.findall(pattern, text)]
    if not rows or len(rows) != len(re.findall(r"(?m)^NAME:", text)):
        raise CollectionError("Unrecognized or incomplete show inventory output")
    return rows


def ports(text):
    header = re.search(r"(?m)^Port\s+Name\s+Status\s+Vlan\s+Duplex\s+Speed\s+Type\s*$", text)
    if not header:
        raise CollectionError("Unrecognized show interfaces status output")
    columns = ["Port", "Name", "Status", "Vlan", "Duplex", "Speed", "Type"]
    offsets = [header[0].index(key) for key in columns]
    rows = []
    for line in text[header.end():].splitlines():
        if not line.strip():
            continue
        values = [line[start:end].strip() for start, end in zip(offsets, offsets[1:] + [None])]
        if not all(values[index] for index in (0, 2, 3, 4, 5)):
            raise CollectionError("Incomplete switchport status row")
        rows.append(dict(zip((key.lower() for key in columns), values)))
    return rows


def lldp(text):
    count = re.search(r"(?mi)^\s*Total entr(?:y|ies) displayed:\s*(\d+)\s*$", text)
    rows = []
    for match in re.finditer(r"(?ms)^Local Intf:[ \t]*(\S+)(.*?)(?=^Local Intf:|\Z)", text):
        body = match[2]
        remote = re.search(r"(?m)^Port id:[ \t]*(\S.*)$", body)
        chassis = re.search(r"(?m)^Chassis id:[ \t]*(\S.*)$", body)
        name = re.search(r"(?m)^System Name:[ \t]*(\S.*)$", body)
        if not remote or not chassis:
            raise CollectionError("Incomplete LLDP neighbor record")
        rows.append({"local_port": match[1], "remote_port": remote[1].strip(),
                     "chassis_id": chassis[1].strip(), "system_name": name[1].strip() if name else None})
    if (count and int(count[1]) != len(rows)) or (not rows and not count):
        raise CollectionError("Unrecognized or incomplete LLDP output")
    return sorted(rows, key=lambda row: (row["local_port"], row["chassis_id"], row["remote_port"]))


def vlan_set(value):
    if value.lower() == "none":
        return []
    if value.lower() == "all":
        return list(range(1, 4095))
    result = set()
    for item in value.split(","):
        low, separator, high = item.partition("-")
        start = int(low)
        end = int(high) if separator else start
        if not 1 <= start <= end <= 4094:
            raise ValueError(f"Invalid VLAN range: {item}")
        result.update(range(start, end + 1))
    return sorted(result)


def trunks(text):
    header = re.search(r"(?mi)^Port\s+Vlans allowed on trunk[ \t]*$", text)
    if not header:
        if re.search(r"(?mi)^Port\s+Mode\s+Encapsulation\s+Status\s+Native vlan\s*$", text.strip()):
            return {}
        raise CollectionError("Unrecognized show interfaces trunk output")
    rows = {}
    for line in text[header.end():].strip().splitlines():
        if not line.strip() or re.match(r"(?i)^Port\s+Vlans", line):
            break
        match = re.fullmatch(r"(\S+)\s+([\d,\-]+|none|all)", line.strip(), re.IGNORECASE)
        if not match:
            raise CollectionError("Incomplete allowed VLAN row")
        rows[match[1]] = vlan_set(match[2])
    return rows
