#!/usr/bin/env python3
"""Update DAR-OW-158 reading log + research phase decisions for research 23.

Idempotent. Bumps `version` (OPF-008 §1.1). Run from the workspace root.
"""
from __future__ import annotations

import datetime as dt
import pathlib

ROOT = pathlib.Path("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research")
VERSION = dt.datetime.now().strftime("%Y_%m_%d_%H_%M")

DECISION_ROWS = [
    "| RD-17 | jcode in the sandbox is a **standard self-contained install** on the guest's own "
    "`~/.jcode` on the guest disk: no host-SSD home, no host-backed share, no `JCODE_HOME` "
    "redirection, no association with the host | The N11/N10 host-SSD home produced two plausible "
    "jcode homes and two days of confusion; the operator requirement is a normal install | Guest "
    "jcode deployment is fully local; host/guest state alignment uses the snapshot sync only | "
    "2026-09-18 |",
    "| RD-18 | The withdrawn N11/N10 wiring is **removed**, not retained: domain export, guest mount, "
    "host binds, fstab lines and backing directories all go | A withdrawn design left half-wired keeps "
    "a stale mechanism reachable and plausible; the export and the ad-hoc mount survived the revert | "
    "The guest ends with exactly one jcode home; the host's own home is untouched | 2026-09-18 |",
    "| RD-19 | The host's own `~/.jcode` on the host SSD **stays as it is** | It is deliberate and "
    "working well, and it does not associate the guest with the host | The fix is strictly "
    "guest-scoped; no host jcode migration | 2026-09-18 |",
]

READ_ROWS = [
    "| 2026-09-18 | Guest jcode deployment review (this research, 23) - N10/N11 host-SSD home error "
    "and its abandonment | The dedicated jcode sandbox home on the host SSD, exposed to the guest as a "
    "writable virtiofs share, was a deployment error: for a period the guest had two plausible jcode "
    "homes (the host-SSD share and the guest-local `~/.jcode`) with neither authoritative, costing two "
    "days. The requirement is now explicit: jcode in the guest is a standard self-contained install on "
    "the guest's own `~/.jcode`, with no host association. The guest already runs that way, but the "
    "domain still exports `vm_sandbox_jcode` (and an unused `vm_sessions`), the guest still holds an "
    "ad-hoc rw mount at `/mnt/vm-sandbox-jcode` with stale 15-16 Sep content, and the host still holds "
    "the backing directories. The host's own `~/.jcode` bind on the SSD is correct and stays. |",
    "| 2026-09-18 | Same-day twin defect: the vestigial native guest Postgres | The guest ran a "
    "systemd Postgres on 5432 holding no application data while the pod DB held the real 508 MB; the "
    "decoy port was the root cause of a wrong-endpoint DSN and a silent 15s hang during sidecar "
    "deployment. Removed the same day (operator-authorized, no dump). Same failure class as the jcode "
    "home: two plausible stores, one stale, nothing marking which is real. |",
]

DECISION_MARKER = "RD-17"
READ_MARKER = "Guest jcode deployment review (this research, 23)"


def bump_version(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith("version:"):
            out.append(f'version: "{VERSION}"')
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def append_rows(path: pathlib.Path, rows: list[str], marker: str) -> str:
    text = path.read_text()
    if marker in text:
        return f"SKIP {path.name}: marker present"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(bump_version(text + "\n".join(rows) + "\n"))
    return f"UPDATED {path.name}: +{len(rows)} row(s), version -> {VERSION}"


def main() -> None:
    print(append_rows(ROOT / "01_Research_Phase_Decisions.md", DECISION_ROWS, DECISION_MARKER))
    print(append_rows(ROOT / "00_What_I_Read.md", READ_ROWS, READ_MARKER))


if __name__ == "__main__":
    main()
