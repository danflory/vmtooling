#!/usr/bin/env python3
"""doSPR2 step 7a: mark SPR-1137's VCL success criteria checked (V-1..V-5)."""
from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"
SPR_CI = "50249"


def main() -> int:
    for n in range(1, 6):
        r = subprocess.run(
            [".venv/bin/python", "OW_tools/db_write.py", "upsert_sc", "--ci-id", SPR_CI,
             "--sc-num", str(n),
             "--desc", f"V-{n} verified 2026-09-18 (SPR-1137 fix implemented, TP-206 post-fix PASS)",
             "--checked", "true"],
            capture_output=True, text=True, cwd=REPO)
        ok = '"status": "success"' in (r.stdout + r.stderr)
        print(f"  V-{n}: {'OK' if ok else (r.stdout + r.stderr)[-140:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
