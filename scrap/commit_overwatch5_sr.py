#!/usr/bin/env python3
"""Register and commit the SR-2124..2127 session records in Overwatch_5.

The real filenames carry a date (`2124_2026-09-17_decisions.md`), so they are
matched by glob rather than by a constructed name. Run from Overwatch_5's root.
"""
from __future__ import annotations

import pathlib
import subprocess

ROOT = pathlib.Path.cwd()


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    files = sorted(str(p) for p in ROOT.glob("docs/SR/212[4-7]_*.md"))
    if not files:
        print("no SR 2124-2127 files found")
        return 0
    print(f"found {len(files)} SR files")
    for p in files:
        rc, out = run(".venv/bin/python", "OW_tools/db_write.py", "sync_ci", "--path", p)
        ok = "assigned_id" in out or "PATCHED" in out
        print(f"  sync_ci {pathlib.Path(p).name}: {'OK' if ok else out[-140:]}")
    rc, out = run("git", "add", "--", *files)
    if rc != 0:
        print("git add failed:", out)
        return 1
    rc, out = run("git", "commit", "-m",
                  "DAR-OW-158: add SR-2124..2127 session records (Overwatch_5 pending work)")
    print("commit:", out[-400:])
    rc, out = run("git", "status", "--short")
    print("remaining dirty:\n" + out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
