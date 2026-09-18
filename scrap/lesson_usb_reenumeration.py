#!/usr/bin/env python3
"""Log the FIDO key re-enumeration lesson (surfaced during the SPR-1137 approval sign)."""
from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"


def main() -> int:
    r = subprocess.run(
        [".venv/bin/python", "OW_tools/db_write.py", "log_lesson",
         "--source-ci-id", "50249", "--key", "usb-passthrough-reenumerates",
         "--title", "A USB-passthrough YubiKey can re-enumerate; the hostdev address goes stale",
         "--finding",
         "The in-guest ow_sign for CI 50249 failed with `OSError: [Errno 5] Input/output error` "
         "and the follow-up probe reported `devices: 0`. The key was still on the host bus but at "
         "a new address (bus 5 device 6, previously device 5), so qemu had lost it while "
         "`virsh dumpxml sandbox` still showed a `hostdev ... type='usb' managed='yes'` entry "
         "bound to the old address. The guest saw no key at all, and a naive re-run would have "
         "failed again.",
         "--reuse",
         "When a passthrough USB device disappears mid-operation, do not retry: check "
         "`lsusb -d <vid:pid>` on the host for a NEW device number and the host's FIDO hidraw "
         "node. Recover by detaching the stale entry and re-attaching by vendor/product rather "
         "than by bus/device (that is what `sandbox-fido off && sandbox-fido on` does), then "
         "confirm the guest sees it and that a non-touching CTAP2 getInfo succeeds before "
         "re-requesting the operator's button press. Matching by vendor/product is what makes "
         "re-enumeration survivable.",
         "--node-type", "SCRIPT", "--topic", "fido_usb_passthrough", "--grade", "ADVISORY"],
        capture_output=True, text=True, cwd=REPO)
    ok = '"status": "success"' in (r.stdout + r.stderr)
    print("lesson logged:", ok)
    if not ok:
        print((r.stdout + r.stderr)[-300:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
