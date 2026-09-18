#!/usr/bin/env python3
"""Update DAR-OW-158 reading log + research phase decisions for research 22.

Idempotent: appends only if the marker text is absent. Bumps `version` (OPF-008 §1.1).
Run from the workspace root.
"""
from __future__ import annotations

import datetime as dt
import pathlib

ROOT = pathlib.Path("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research")
VERSION = dt.datetime.now().strftime("%Y_%m_%d_%H_%M")

DECISION_ROWS = [
    "| RD-14 | YubiKey passthrough is **live/transient by default** (`sandbox-fido on`/`off`); "
    "persistent domain config only on explicit operator request | A persistent USB hostdev makes "
    "`virsh start sandbox` fail whenever the key is absent, and a long-lived VM would otherwise hold "
    "the operator key permanently, breaking host-side WebAuthn | The domain stays bootable without the "
    "key; custody of the key is an explicit operator action | 2026-09-18 |",
    "| RD-15 | The in-guest Admin-UI sign sidecar must connect as **`overwatch_agent`** with the agent "
    "credential, never as the database superuser | The superuser password is rejected for the agent roles "
    "anyway, and connecting as superuser would defeat the RFC-OW-370 / D3 containment that keeps "
    "signature logging out of agent reach | Sidecar deployment must carry the agent credential as a "
    "secret; the FIDO2 grant set already present in the guest is exactly what the flow needs | 2026-09-18 |",
    "| RD-16 | The sidecar DSN is corrected for the guest topology (**guest DB service, no pgbouncer**) "
    "instead of mirroring the host manifest verbatim | The guest runs no pgbouncer; the host-era DSN "
    "targets `pgbouncer:51729`, which cannot resolve in the guest | The deployment deviates from the "
    "committed manifest in exactly one field; recorded so the deviation is intentional and auditable | "
    "2026-09-18 |",
]

READ_ROWS = [
    "| 2026-09-18 | In-guest FIDO2 signing enablement (this research, 22) - host/guest live audit, then "
    "fix and verification | The guest had no USB hostdev at all (the N17 Part A gap). Attaching one was "
    "necessary but not sufficient: stock Ubuntu grants `uaccess` only, so the seat-less SSH session that "
    "runs `ow_sign` got `EACCES` on the FIDO hidraw node, and a `plugdev` rule on the FIDO interface "
    "closed it. Passthrough is exclusive (the host loses the key while attached) and a persistent "
    "hostdev breaks `virsh start` when the key is absent, so live attach is the default. The sidecar "
    "image, the FIDO2 RBAC grants and the DB secret already exist in the guest; only the "
    "Deployment/Service is missing, and its DSN still targets the host-era `pgbouncer:51729`, which does "
    "not exist in the guest. |",
    "| 2026-09-18 | Host artifacts written for N17 Part A (`~/dev_env/vmtooling`) | "
    "`yubikey_usb_hostdev.xml` + `docs/yubikey-fido-passthrough.md` committed as vmtooling `47aee40` "
    "(1 commit ahead of `origin/main`, unpushed at time of writing); operator helper "
    "`~/.local/bin/sandbox-fido`; guest rule `/etc/udev/rules.d/70-yubikey-fido.rules`; pre-change domain "
    "XML snapshot kept uncommitted under `backups/`. |",
]

DECISION_MARKER = "RD-14"
READ_MARKER = "In-guest FIDO2 signing enablement (this research, 22)"


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
    decisions = ROOT / "01_Research_Phase_Decisions.md"
    reading = ROOT / "00_What_I_Read.md"
    print(append_rows(decisions, DECISION_ROWS, DECISION_MARKER))
    print(append_rows(reading, READ_ROWS, READ_MARKER))


if __name__ == "__main__":
    main()
