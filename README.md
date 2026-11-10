# Cisco IOS NetOps

**Read-only automation for Cisco IOS and IOS XE.**

Collect inventory over SSH, audit a fleet against software targets, and verify what changed after a network intervention.

`Python 3.11+` · `Netmiko` · `Offline replay` · `CSV / JSON / HTML`

## Try it in two minutes

A planned uplink change moves the LLDP neighbor from `dist-a` to `dist-b`. The post-change capture also reveals that VLAN 30 disappeared from the trunk. The validator separates the planned change from the regression.

```bash
git clone https://github.com/netpython/cisco-ios-netops.git
cd cisco-ios-netops

python3 -m programs.change_validation capture --fixture examples/before --output out/before.json
python3 -m programs.change_validation capture --fixture examples/after --output out/after.json
python3 -m programs.change_validation compare --before out/before.json --after out/after.json \
  --expected examples/expected-change.json --output out/changes.html
```

Open `out/changes.html` in a browser. This replay needs Python and the included fictional data. The compare command exits with status **1** because the demo contains a regression.

| Status | Check | Observed result |
| --- | --- | --- |
| Expected | LLDP | Neighbor `dist-a` removed from `Gi1/0/24` |
| Expected | LLDP | Neighbor `dist-b` added to `Gi1/0/24` |
| **Unexpected** | Trunk | **VLAN 30 removed from `Gi1/0/24`** |

## Scripts · one task per command

| Entry point | Command collected | Output |
| --- | --- | --- |
| [collect_device_inventory.py](scripts/collect_device_inventory.py) | `show version`, `show inventory` | JSON with hostname, software version and component PIDs, revisions and serials |
| [export_switchport_status.py](scripts/export_switchport_status.py) | `show interfaces status` | CSV with port names, link states, VLANs, speed, duplex and media |
| [export_lldp_neighbors.py](scripts/export_lldp_neighbors.py) | `show lldp neighbors detail` | CSV with local and remote ports, chassis ID and system name |
| [backup_running_config.py](scripts/backup_running_config.py) | `show running-config` | UTC-stamped local backup with owner-only permissions on POSIX |

```bash
python3 -m scripts.collect_device_inventory --fixture examples/before --output out/inventory.json
python3 -m scripts.export_switchport_status --fixture examples/before --output out/ports.csv
python3 -m scripts.export_lldp_neighbors --fixture examples/before --output out/lldp.csv
python3 -m scripts.backup_running_config --fixture examples/before --output-dir out/backups
```

## Programs · operational workflows

| Program | Workflow | Deliverables |
| --- | --- | --- |
| [Fleet audit](programs/fleet_audit/) | Audit switches concurrently against per-device version targets. Preserve partial results if an individual device or command fails. | Per-device CSV and HTML with software drift, port totals and collection errors |
| [Change validation](programs/change_validation/) | Capture state twice and compare trunk allowed VLANs and LLDP neighbors against a JSON change plan. | HTML report with expected, unexpected, missing expected and unavailable checks |
| [Configuration compliance](programs/config_compliance/) | Audit a saved running config with YAML regex policies. Evaluate global commands and individual VTY or interface blocks. | CSV with rule outcomes, block names, line numbers and evidence |

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

python -m programs.fleet_audit --fixture examples/fleet --output-dir out/fleet
python -m programs.config_compliance --config examples/configs/edge-a.txt \
  --policy examples/policy.yml --output out/compliance.csv
```

The fleet example exits with **2** and still produces a report. It includes a conforming switch, a version mismatch and a missing device capture. The compliance example exits with **1** and reports a missing NTP server and a VTY block permitting Telnet.

## Connect to a lab switch

Use an SSH account authorized for the required show commands. Verify the device host key and add it to your system known-hosts file before connecting. For password authentication, provide `IOS_PASSWORD` through your shell environment. For key authentication, use `--key-file` with a dedicated lab key.

```bash
export IOS_USERNAME=netops
python -m scripts.collect_device_inventory --host 192.0.2.10 --key-file ~/.ssh/ios_lab \
  --output out/inventory.json

python -m programs.fleet_audit --inventory examples/fleet/inventory.json \
  --key-file ~/.ssh/ios_lab --workers 4 --output-dir out/fleet
```

Replace the documentation IP address and sample inventory with your lab values. To capture a live change snapshot, use `capture --host HOST --key-file PATH --output FILE` in place of the replay command.

| Exit | Meaning |
| --- | --- |
| `0` | Success or all evaluated checks passed |
| `1` | Drift, noncompliance or an unexpected change |
| `2` | Input error, SSH failure or incomplete coverage. See the report when one was produced. |

## Scope and validation

- The SSH collector uses Netmiko with host-key verification and runs only the listed show commands.
- The parsers target the IOS and IOS XE output shapes shown in [the fixtures](examples/). Verify the command output on your hardware and software release before relying on a check. The current tests replay fixtures. Live SSH on hardware is pending lab validation.
- The trunk check compares configured allowed VLANs on reported trunks. Forwarding state and spanning tree are outside the comparison.
- Config backups can contain credentials and infrastructure details. Compliance evidence masks common secret-bearing lines and can still contain sensitive configuration. Keep real outputs in a restricted location and outside Git.
- Policy files use Python regex search against individual lines. Use policy files you trust and anchor patterns for exact matching.

```bash
python -m unittest discover -s tests -v
```

[Netmiko project](https://github.com/ktbyers/netmiko)
