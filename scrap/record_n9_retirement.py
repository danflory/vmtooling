#!/usr/bin/env python3
"""Record the N9 item-4 retirement: the guest native Postgres was purged on
2026-09-18, so the MemoryMax drop-in that bounded it is inert and has been
removed. Idempotent."""
from __future__ import annotations

import pathlib

DOC = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/04_Implementation/"
    "01_N9_Memory_Containment_Apply.md"
)

MARKER = "Item 4 retired 2026-09-18"
NOTE = f"""
## {MARKER} (target no longer exists)

Item 4 bounded `postgresql@16-main.service` at `MemoryMax=1G`. That unit no longer exists:
the guest's vestigial native Postgres was purged on 2026-09-18 (packages, cluster, data dir,
config and log dirs all removed; port 5432 freed; see `04_N17_Guest_Runtime_Apply.md`, udrs
50229). The drop-in `/etc/systemd/system/postgresql@16-main.service.d/10-memory-limit.conf`
therefore had no target and was **removed** (with its now-empty drop-in directory), followed
by `systemctl daemon-reload`.

The containment intent is unaffected: the database that actually serves the guest runs
in-cluster (`firecontrol-db-0` StatefulSet) and is bounded by its Kubernetes resource
limits, not by a systemd drop-in. Item 4 is therefore **retired as vacuous**, not failed —
there is no longer a systemd Postgres to bound.
"""


def main() -> None:
    t = DOC.read_text()
    if MARKER in t:
        print("already recorded")
        return
    if not t.endswith("\n"):
        t += "\n"
    DOC.write_text(t + NOTE)
    print(f"recorded the item-4 retirement in {DOC.name}")


if __name__ == "__main__":
    main()
