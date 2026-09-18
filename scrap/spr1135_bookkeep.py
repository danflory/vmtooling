#!/usr/bin/env python3
"""SPR-1135 bookkeeping: tick the corrective actions that are done and mark
V-1/V-2 verified (teardown executed 2026-09-18). Idempotent."""
from __future__ import annotations

import pathlib
import subprocess

FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association"
)
ANCHOR = FOLDER / "SPR-1135.md"
ANCHOR_ID = 50221

DONE = [
    "Detach the `vm_sandbox_jcode` filesystem device from the `sandbox` domain",
    "Unmount `/mnt/vm-sandbox-jcode` in the guest and verify nothing references it",
    "Remove the host binds and `/etc/fstab` lines for `vm_sandbox_jcode` and `vm_sessions`",
    "Mark N10/N11 in the DAR graph with the rework/abandonment and this SPR's id",
]

VCL_NOTES = {
    "V-1": "The `sandbox` domain no longer exports a jcode filesystem device: `virsh dumpxml sandbox` contains no `vm_sandbox_jcode` target and no unused `vm_sessions` target. | ✅ 2026-09-18",
    "V-2": "The guest has no jcode-related virtiofs mount: `mount \\| grep virtiofs` shows only `host_dev_env` (ro) and `vm_backups` (rw); `/mnt/vm-sandbox-jcode` is unmounted and absent, and the guest's jcode processes still run from the local `~/.jcode`. | ✅ 2026-09-18",
}


def main() -> None:
    text = ANCHOR.read_text()
    for item in DONE:
        text = text.replace(f"- [ ] {item}", f"- [x] {item} — 2026-09-18")
    for key, note in VCL_NOTES.items():
        old_marker = f"| {key} | "
        # replace the whole row's trailing status cell
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(old_marker) and line.rstrip().endswith("| ⬜ |"):
                body = line.rstrip()[:-4].rstrip()  # drop '| ⬜ |'
                lines[i] = body + " | ✅ 2026-09-18 |"
        text = "\n".join(lines) + "\n"
    ANCHOR.write_text(text)
    print("anchor updated")
    print("checkboxes now:")
    for line in text.splitlines():
        if line.startswith("- ["):
            print("  " + line[:100])

    for num, key in ((1, "V-1"), (2, "V-2")):
        r = subprocess.run(
            [".venv/bin/python", "OW_tools/db_write.py", "upsert_sc", "--ci-id", str(ANCHOR_ID),
             "--sc-num", str(num), "--desc", f"{key} verified 2026-09-18 (teardown executed)",
             "--checked", "true"],
            capture_output=True, text=True)
        ok = '"status": "success"' in r.stdout
        print(f"  SC {key}: {'OK' if ok else 'FAIL ' + (r.stdout + r.stderr)[-160:]}")


if __name__ == "__main__":
    main()
