#!/usr/bin/env python3
"""Landscape: every branch tip that carries work not in main, and whether it merges cleanly.

Fetches each candidate tip from its source clone into the authoritative clone as
refs/remotes/fold/<name>, then reports:
  - whether the tip is already an ancestor of main (redundant)
  - how many unique commits it carries
  - a merge-tree dry run against main (conflict count, no worktree change)
Nothing is modified.
"""
from __future__ import annotations

import pathlib
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
C = pathlib.Path.home() / "dev_env/clones"

CANDIDATES = [
    ("rfc-wf-026-ow1", C / "Overwatch_1", "RFC-WF-026"),
    ("rfc-wf-026-ow2", C / "Overwatch_2", "RFC-WF-026"),
    ("rfc-wf-026-ow3", C / "Overwatch_3", "RFC-WF-026"),
    ("dar-ow-157-ow2", C / "Overwatch_2",
     "DAR-OW-157_Fork_Rebase_Process_Public_Open_Source/03_Synthesis/01_Mikado_Graph"),
    ("rfc-wf-027-ow3", C / "Overwatch_3", "RFC-WF-027"),
    ("spr-1117-ow4", C / "Overwatch_4", "SPR-1117"),
    ("dar-ow-151-ow5", C / "Overwatch_5", "DAR-OW-151"),
    ("dar-ow-71-ow5", C / "Overwatch_5", "DAR-OW-71"),
    ("backup-presync-ow5", C / "Overwatch_5", "backup/pre-sync-6ffc0861b"),
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> None:
    for name, src, branch in CANDIDATES:
        rc, out = run("git", "fetch", "--quiet", str(src), f"{branch}:refs/remotes/fold/{name}")
        if rc != 0:
            print(f"{name:22s} FETCH FAILED: {out[:120]}")
            continue
        ref = f"refs/remotes/fold/{name}"
        tip = run("git", "rev-parse", "--short", ref)[1]
        subj = run("git", "log", "-1", "--format=%s", ref)[1][:60]
        contained = run("git", "merge-base", "--is-ancestor", ref, "main")[0] == 0
        uniq = run("git", "rev-list", "--count", f"main..{ref}")[1]
        conflicts = "-"
        if not contained:
            _, mt = run("git", "merge-tree", "--write-tree", "main", ref)
            conflicts = str(mt.count("CONFLICT"))
        print(f"{name:22s} {tip}  in-main={contained!s:5s} unique={uniq:>4s} merge-conflicts={conflicts}  {subj}")


if __name__ == "__main__":
    main()
