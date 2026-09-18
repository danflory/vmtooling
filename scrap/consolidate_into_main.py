#!/usr/bin/env python3
"""Consolidate everything into `main` and push, so origin/main is the single
authoritative head that every clone can pull from for the final sync.

Operator direction (2026-09-18): "the only goal is that origin main be
authoritative head that all pull from for the final sync."

So the two sibling DAR-OW-158 tips (Overwatch_2: 65 commits; Overwatch_5: 8 commits,
both descending from origin/DAR-OW-158) are merged INTO main, one after the other.
Each merge is dry-run with merge-tree first; the script stops on any conflict.

Runs in the guest's authoritative clone (clean worktree, on main).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
SOURCES = [
    ("ow2", pathlib.Path.home() / "dev_env/clones/Overwatch_2"),
    ("ow5", pathlib.Path.home() / "dev_env/clones/Overwatch_5"),
]
BRANCH = "DAR-OW-158"


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def conflicts(a: str, b: str) -> tuple[int, str]:
    rc, out = run("git", "merge-tree", "--write-tree", a, b)
    return out.count("CONFLICT"), out


def main() -> int:
    rc, out = run("git", "status", "--short")
    if out:
        print("WORKTREE NOT CLEAN — refusing to merge:", out[:300], file=sys.stderr)
        return 1
    print("worktree clean; on", run("git", "rev-parse", "--abbrev-ref", "HEAD")[1])

    for tag, path in SOURCES:
        rc, out = run("git", "fetch", "--quiet", str(path), f"{BRANCH}:refs/remotes/{tag}/{BRANCH}")
        print(f"fetch {tag}: exit={rc} {out[:160]}")

    for tag, _ in SOURCES:
        n, out = conflicts("main", f"refs/remotes/{tag}/{BRANCH}")
        print(f"merge-tree main + {tag}/{BRANCH}: conflicts={n}")
        if n:
            print(out[:1500])
            print("STOP: conflict — operator decision needed")
            return 1

    for tag, _ in SOURCES:
        rc, out = run("git", "merge", "--no-edit",
                      "-m", f"Merge {tag} {BRANCH} into main (final sync consolidation)",
                      f"refs/remotes/{tag}/{BRANCH}")
        print(f"merge {tag}: exit={rc} {out[-200:]}")
        if rc != 0:
            print("STOP: merge failed")
            return 1

    rc, out = run("git", "log", "--oneline", "-3")
    print("main now:\n" + out)

    rc, out = run("git", "push", "origin", "main")
    print(f"push: exit={rc} {out[-300:]}")
    rc, out = run("git", "fetch", "--quiet", "origin")
    rc, out = run("git", "rev-list", "--left-right", "--count", "HEAD...origin/main")
    print("ahead/behind vs origin/main:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
