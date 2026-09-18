#!/usr/bin/env python3
"""Record the concrete failure mode of the N10/N11 share in the governed record.

Operator-supplied root cause (2026-09-18): host and guest shared the same jcode
session files through the `vm_sessions` virtiofs share, and with frequent guest
server restarts the two jcode instances collided over the same sessions/
directory. The symptom presented as "connections keep closing" (DeepInfra), which
had been misread as a network/timeout problem.

Targets: research 23 (findings) and SPR-1135 (anchor root cause + deficiency).
Idempotent. Run from the workspace root on the guest.
"""
from __future__ import annotations

import pathlib

RESEARCH = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research/"
    "23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md"
)
SPR = pathlib.Path(
    "docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/SPR-1135.md"
)
DEFICIENCY = SPR.parent / "01_Deficiency_Report.md"

MECHANISM = (
    "host and guest shared the same jcode session files through the `vm_sessions` share "
    "(host `/data/jcode-vm-sessions` → guest `/var/lib/libvirt/virtiofs/vm_sessions`), and with "
    "the guest server restarting frequently, two jcode instances mutated the same `sessions/` "
    "directory. It surfaced as repeated *\"connections keep closing\"* errors that were initially "
    "misread as a DeepInfra network/timeout problem."
)

EDITS: dict[pathlib.Path, list[tuple[str, str]]] = {
    RESEARCH: [
        # Problem section: state the mechanism up front
        (
            "was reverted on 2026-09-16/17, and the operator reports that it caused two days of\n"
            "confusion. This research records the error fully, the requirement it violated, and\n"
            "the residue that still contradicts the requirement.",
            "was reverted on 2026-09-16/17, and the operator reports that it caused two days of\n"
            "confusion. The mechanism of the failure is now known and is recorded as F7: "
            + MECHANISM
            + "\nThis research records the error fully, the requirement it violated, and the residue\n"
            "that still contradicts the requirement.",
        ),
        # F4 evidence: point at the mechanism
        (
            "| Operator statement; measured state above |",
            "| Operator statement; measured state above; concrete mechanism in F7 |",
        ),
        # New finding row after F6
        (
            "| F6 | **The host half is correct.** The host's own `~/.jcode` is a bind of `/data/jcode-home` (1.4 GB on `/dev/sdb1`) and works well. It is the host's jcode, not the guest's, so it does not associate the guest with the host. No change is required or wanted there. | Host `findmnt`, host `/etc/fstab`, operator statement |",
            "| F6 | **The host half is correct.** The host's own `~/.jcode` is a bind of `/data/jcode-home` (1.4 GB on `/dev/sdb1`) and works well. It is the host's jcode, not the guest's, so it does not associate the guest with the host. No change is required or wanted there. | Host `findmnt`, host `/etc/fstab`, operator statement |\n"
            "| F7 | **The concrete failure mechanism** (operator, 2026-09-18): "
            + MECHANISM
            + " This is why the idea \"did not work out at all\" rather than merely being untidy: a live shared session store with two writers is a correctness bug, and it presents as a *network* symptom, which is what made it expensive to diagnose. | Operator statement; the `vm_sessions` share existed and was exported by the domain (F3) |",
        ),
    ],
    SPR: [
        (
            "Consequence: for a period the guest had **two plausible jcode homes** — the host-SSD share\n"
            "and the guest-local `~/.jcode` — with neither authoritative and nothing in fstab to\n"
            "disambiguate. The operator attributes two days of confusion to exactly this. The DAR's own\n"
            "closure gate cannot see it (see the TP Change Report), so the residue can survive a\n"
            "passing TP-188.",
            "Consequence: for a period the guest had **two plausible jcode homes** — the host-SSD share\n"
            "and the guest-local `~/.jcode` — with neither authoritative and nothing in fstab to\n"
            "disambiguate. The operator attributes two days of confusion to exactly this, and the\n"
            "concrete failure mechanism is known: "
            + MECHANISM
            + "\nThe DAR's own closure gate cannot see it (see the TP Change Report), so the residue can\n"
            "survive a passing TP-188.",
        ),
        (
            "The underlying process gap is the same one that let a vestigial native Postgres survive on",
            "The design was also not merely untidy — it was a correctness bug. A single writable session\n"
            "store with two writers (host and guest jcode) cannot be made safe by documentation; the\n"
            "collision surfaced as *\"connections keep closing\"*, a network-shaped symptom that cost the\n"
            "operator days and pointed attention away from the actual cause (see F7 of\n"
            "`02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md`, UDRS 50216).\n"
            "\n"
            "The underlying process gap is the same one that let a vestigial native Postgres survive on",
        ),
    ],
    DEFICIENCY: [
        (
            "| Expose it as a read-write virtiofs share | Read-write exposure means the guest and host can diverge silently; nothing arbitrates. The same mechanism is fine for `vm_backups` (write-only destination) and for `host_dev_env` (read-only reference) precisely because those directions are unambiguous. |",
            "| Expose it as a read-write virtiofs share | Read-write exposure means the guest and host can diverge silently; nothing arbitrates. The same mechanism is fine for `vm_backups` (write-only destination) and for `host_dev_env` (read-only reference) precisely because those directions are unambiguous. **Confirmed failure**: the shared `vm_sessions` store gave two jcode instances (host and guest) the same `sessions/` directory, and with frequent guest restarts they collided; the operator saw repeated *\"connections keep closing\"* errors and the cause was initially sought in the network. A writable share of live application state is a correctness bug, not a hygiene issue. |",
        ),
    ],
}


def main() -> None:
    for path, edits in EDITS.items():
        text = path.read_text()
        applied = 0
        for old, new in edits:
            if new.split("\n")[0] in text and old not in text:
                continue
            if old in text:
                text = text.replace(old, new, 1)
                applied += 1
            else:
                print(f"  MISS in {path.name}: {old[:70]!r}")
        path.write_text(text)
        print(f"{path.name}: {applied}/{len(edits)} edits applied")


if __name__ == "__main__":
    main()
