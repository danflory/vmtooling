#!/usr/bin/env python3
"""SPR-1135 teardown, host side: detach the withdrawn jcode/session virtiofs
devices from the `sandbox` domain.

Targets removed:
  - `vm_sandbox_jcode`  -> the N10/N11 host-SSD jcode home share
  - `vm_sessions`       -> jcode session data on the host SSD (never mounted in the guest)

Untouched: `host_dev_env` (ro, RD-6) and `vm_backups` (rw).

Needs no root (user `d` is in group libvirt). Idempotent.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

DOMAIN = "sandbox"
TARGETS = {"vm_sandbox_jcode", "vm_sessions"}
TMP = pathlib.Path("/home/d/dev_env/vmtooling/backups")


def virsh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["virsh", *args], capture_output=True, text=True)


def main() -> int:
    dump = virsh("dumpxml", DOMAIN)
    if dump.returncode != 0:
        print("ERROR: dumpxml failed:", dump.stderr.strip(), file=sys.stderr)
        return 1

    root = ET.fromstring(dump.stdout)
    devices = root.find("devices")
    assert devices is not None
    live_xml = dump.stdout

    wanted = []
    for fs in devices.findall("filesystem"):
        target = fs.find("target")
        if target is not None and target.get("dir") in TARGETS:
            wanted.append((target.get("dir"), fs))

    if not wanted:
        print("already detached: no jcode/session filesystem device present")
        return 0

    TMP.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name, fs in wanted:
        # Emit the device fragment as a standalone detach document.
        frag = ET.tostring(fs, encoding="unicode")
        path = TMP / f"detach_{name}.xml"
        path.write_text(frag + "\n")

        live = virsh("detach-device", DOMAIN, str(path), "--live", "--config")
        if live.returncode == 0:
            print(f"detached {name}: live + config")
            continue
        cfg = virsh("detach-device", DOMAIN, str(path), "--config")
        if cfg.returncode == 0:
            print(f"detached {name}: config only (live unsupported: {live.stderr.strip()[:80]})")
            print(f"  note: the running domain keeps it until the next VM restart;"
                  f" the guest no longer mounts it")
        else:
            print(f"FAILED {name}: live={live.stderr.strip()[:120]} config={cfg.stderr.strip()[:120]}",
                  file=sys.stderr)
            rc = 1

    after = virsh("dumpxml", DOMAIN).stdout
    print("remaining filesystem targets:", [
        t.get("dir") for t in ET.fromstring(after).find("devices").findall("filesystem")
    ] if "filesystem" in after else [])
    if "vm_sandbox_jcode" in after or "vm_sessions" in after:
        print("WARNING: a withdrawn target is still present in the live XML")
    _ = live_xml
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
