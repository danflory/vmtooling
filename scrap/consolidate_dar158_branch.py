#!/usr/bin/env python3
"""Consolidate the two sibling DAR-OW-158 tips and push the result.

Overwatch_2's DAR-OW-158 (65 commits ahead of origin/DAR-OW-158) and
Overwatch_5's DAR-OW-158 (now 8 ahead, after its pending work was committed) are
SIBLINGS off the same origin tip: neither is an ancestor of the other, so both
cannot be pushed to the same branch. A merge-tree dry run showed the merge is
clean (0 conflicts), so the consolidation is: merge _5's tip into _2's tip and
push the merged branch.

Done in a THROWAWAY WORKTREE so neither clone's existing worktree is touched.
Then a merge-tree dry run of the merged tip against `main`.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

P2 = pathlib.Path.home() / "dev_env/clones/Overwatch_2"
P5 = pathlib.Path.home() / "dev_env/clones/Overwatch_5"
WT = pathlib.Path("/tmp/ow2-merge-wt")
BRANCH = "DAR-OW-158"


def run(cwd: pathlib.Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=cwd)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    print("=== _2 dirty state (its worktree stays untouched) ===")
    print(run(P2, "git", "status", "--short")[1] or "(clean)")

    print("=== fetch _5's branch into _2 ===")
    rc, out = run(P2, "git", "fetch", str(P5), f"{BRANCH}:refs/remotes/local5/{BRANCH}")
    print(f"exit={rc} {out[:200]}")

    print("=== re-test the merge with the NEW _5 tip ===")
    rc, out = run(P2, "git", "merge-tree", "--write-tree", BRANCH, f"refs/remotes/local5/{BRANCH}")
    conflicts = out.count("CONFLICT")
    print(f"exit={rc} conflicts={conflicts}")
    if conflicts:
        print(out[:1500])
        print("STOP: conflicts present, not merging")
        return 1

    print("=== merge in a throwaway worktree ===")
    if WT.exists():
        run(P2, "git", "worktree", "remove", "--force", str(WT))
        shutil.rmtree(WT, ignore_errors=True)
    rc, out = run(P2, "git", "worktree", "add", str(WT), BRANCH)
    print(f"worktree add: exit={rc} {out[:200]}")

    rc, out = run(WT, "git", "merge", "--no-edit", "-m",
                  "Merge Overwatch_5 DAR-OW-158 into DAR-OW-158 (consolidate the sibling tips)",
                  f"refs/remotes/local5/{BRANCH}")
    print(f"merge: exit={rc} {out[-300:]}")
    if rc != 0:
        print("STOP: merge failed in the worktree")
        return 1

    rc, out = run(WT, "git", "log", "--oneline", "-1")
    print("merged tip:", out)
    rc, out = run(WT, "git", "push", "origin", BRANCH)
    print(f"push: exit={rc} {out[-300:]}")

    print("=== can main merge the consolidated tip? (dry run) ===")
    rc, out = run(P2, "git", "merge-tree", "--write-tree", "main", f"refs/remotes/local5/{BRANCH}")
    print(f"exit={rc} conflicts={out.count('CONFLICT')}")

    print("=== clean up the worktree ===")
    run(P2, "git", "worktree", "remove", "--force", str(WT))
    print(run(P2, "git", "worktree", "list")[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
