#!/usr/bin/env python3
"""Dry-run: what does folding each not-yet-folded tip into head actually do?

For each candidate, report the merge-tree conflict count and whether the merged tree is
IDENTICAL to head's tree (i.e. the tip is pure ancestry with no content change).
"""
from __future__ import annotations

import pathlib
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
HEAD = "401af47d4"

CANDIDATES = [
    ("origin/RFC-WF-026", "origin/RFC-WF-026"),
    ("origin/SPR-1117", "origin/SPR-1117"),
    ("origin/DAR-OW-157_..._Mikado_Graph",
     "origin/DAR-OW-157_Fork_Rebase_Process_Public_Open_Source/03_Synthesis/01_Mikado_Graph"),
    ("guest_5 backup/pre-sync-6ffc0861b", "refs/hostaudit/Overwatch_5-backup_pre-sync-6ffc0861b"),
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> None:
    head_tree = run("git", "rev-parse", f"{HEAD}^{{tree}}")[1]
    for label, ref in CANDIDATES:
        if run("git", "cat-file", "-e", f"{ref}^{{commit}}")[0] != 0:
            print(f"{label:<40} ref not present")
            continue
        rc, out = run("git", "merge-tree", "--write-tree", HEAD, ref)
        conflicts = out.count("CONFLICT")
        tree = out.splitlines()[0].strip() if out else "?"
        try:
            same = int(tree, 16) and tree == head_tree
        except ValueError:
            same = False
        uniq = run("git", "rev-list", "--count", f"{HEAD}..{ref}")[1]
        verdict = ("content-identical (pure ancestry, merge is a no-op)"
                   if conflicts == 0 and same else
                   f"CHANGES CONTENT (merged tree differs){' + CONFLICTS' if conflicts else ''}")
        print(f"{label:<40} conflicts={conflicts} unique={uniq} -> {verdict}")
        if conflicts:
            for line in out.splitlines():
                if "CONFLICT" in line or line.startswith("  "):
                    print("     ", line[:130])
                    if "CONFLICT" in line:
                        pass
    print(f"\nhead tree: {head_tree[:12]}")


if __name__ == "__main__":
    main()
