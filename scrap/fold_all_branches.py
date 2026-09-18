#!/usr/bin/env python3
"""Fold every branch that carries work not in main.

Eight candidates, all verified conflict-free by a merge-tree dry run. The ninth
(`backup/pre-sync-6ffc0861b`, a stash-WIP snapshot) has 5 conflicts and is NOT folded
here — it is reported for an operator decision.

Re-checks containment and re-dry-runs before each merge, so later merges that are
already covered become no-ops instead of duplicating history. Stops on any conflict.
"""
from __future__ import annotations

import pathlib
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"

ORDER = [
    ("rfc-wf-026-ow1", "RFC-WF-026 (Overwatch_1 tip)"),
    ("rfc-wf-026-ow2", "RFC-WF-026 (Overwatch_2 tip)"),
    ("rfc-wf-026-ow3", "RFC-WF-026 (Overwatch_3 tip)"),
    ("rfc-wf-027-ow3", "RFC-WF-027 (Overwatch_3)"),
    ("dar-ow-157-ow2", "DAR-OW-157 fork/rebase graph (Overwatch_2)"),
    ("spr-1117-ow4", "SPR-1117 (Overwatch_4)"),
    ("dar-ow-151-ow5", "DAR-OW-151 (Overwatch_5)"),
    ("dar-ow-71-ow5", "DAR-OW-71 (Overwatch_5)"),
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    rc, dirty = run("git", "status", "--short")
    if dirty:
        print("WORKTREE DIRTY — refusing:", dirty[:200])
        return 1

    folded, skipped = [], []
    for name, label in ORDER:
        ref = f"refs/remotes/fold/{name}"
        if run("git", "rev-parse", "--verify", "--quiet", ref)[0] != 0:
            print(f"SKIP {label}: ref missing")
            skipped.append(label)
            continue
        if run("git", "merge-base", "--is-ancestor", ref, "main")[0] == 0:
            print(f"already in main: {label}")
            folded.append(label + " (already contained)")
            continue
        _, mt = run("git", "merge-tree", "--write-tree", "main", ref)
        n = mt.count("CONFLICT")
        if n:
            print(f"CONFLICTS ({n}) for {label} — not folded")
            skipped.append(label)
            continue
        rc, out = run("git", "merge", "--no-edit", "-m",
                      f"Fold {label} into main (final consolidation)", ref)
        tail = out.splitlines()[-1] if out else ""
        print(f"folded {label}: exit={rc} {tail[:90]}")
        if rc != 0:
            skipped.append(label)
            print("  STOPPING on merge failure")
            break
        folded.append(label)

    print("\n=== folded ===")
    for f in folded:
        print("  " + f)
    if skipped:
        print("=== skipped ===")
        for s in skipped:
            print("  " + s)
    rc, out = run("git", "log", "--oneline", "-6")
    print("\nmain now:\n" + out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
