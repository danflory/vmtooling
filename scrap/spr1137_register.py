#!/usr/bin/env python3
"""SPR-1137: fix the scaffolded EFSM state and register all four files.

The scaffolder emits the invalid pair (DEVELOPMENT, DRAFT); the EFSM's valid pairs
are (DRAFT, ACTIVE) initial and (DEVELOPMENT, ACTIVE) activated, so `status: ACTIVE`
is the minimal correct fix (learned on SPR-1135, recorded in 04_Implementation/04).
"""
from __future__ import annotations

import pathlib
import subprocess

FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries"
)


def main() -> int:
    files = sorted(FOLDER.glob("*.md"))
    for f in files:
        lines = f.read_text().splitlines()
        out, in_fm = [], False
        for line in lines:
            if line.strip() == "---":
                in_fm = not in_fm
            if in_fm and line.startswith("status: DRAFT"):
                line = "status: ACTIVE"
            out.append(line)
        f.write_text("\n".join(out) + "\n")
        print(f"patched {f.name}")

    for f in files:
        r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", "sync_ci", "--path", str(f)],
                           capture_output=True, text=True)
        ok = "assigned_id" in r.stdout or "PATCHED" in r.stdout
        line = [x for x in r.stdout.splitlines() if "assigned_id" in x]
        print(f"  {f.name}: {'OK ' + (line[0].strip()[:80] if line else '') if ok else (r.stdout + r.stderr)[-160:]}")

    for f in files:
        for line in f.read_text().splitlines()[:6]:
            if line.startswith("id:"):
                print(f"  {f.name} id={line.split(':', 1)[1].strip()}")
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
