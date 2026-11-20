# Export the IPv4 ARP table

Collect the global table with `show ip arp`, or replay a fictional capture. No clear, ping, debug or configuration command is sent. ARP evidence maps an IPv4 address to a link-layer neighbor; it is not a list of every endpoint behind a routed next hop.

## Offline example

Python 3.11+; the replay uses only the standard library.

```bash
python -m scripts.export_arp_table --fixture examples/arp --output out/arp.csv
python -m unittest discover -s tests -p test_arp.py -v
```

The fixture is simulated and includes a local entry, a learned neighbor and an unresolved address. CSV columns: address, normalized MAC, age in minutes, interface, state. A dash age becomes an empty field; it must not be treated as proof of a static entry. Incomplete entries preserve their IP and have no fabricated MAC.

## Authorized lab collection

Follow the repository SSH setup and verify the host key first.

```bash
python -m scripts.export_arp_table --host 192.0.2.10 --username netops --key-file ~/.ssh/ios_lab --output out/arp.csv
```

Replace the documentation address. Existing Netmiko timeouts and host-key checking are reused. Exit 0 means exported, 2 means input/collection/parser failure, and 130 means user interruption.

## Scope

Classic IOS/IOS XE `Internet ... ARPA` table format only, global IPv4 table. No VRF enumeration, IPv6 ND or duplicate-address verdict. Unsupported headers or rows fail explicitly rather than producing a partial success. The collector rejects empty or known CLI-error responses. A header-only table is a valid empty table.

The CSV contains topology and device identities; retain it outside Git. Device output varies with release. Offline replay and parser tests do not establish live SSH compatibility.

Reference: [Cisco ARP command reference](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/ipaddr/command/ipaddr-cr-book/ipaddr-r1.html).
