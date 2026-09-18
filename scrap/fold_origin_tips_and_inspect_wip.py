#!/usr/bin/env python3
"""Fold the three content-identical origin tips, then inspect the guest_5 WIP snapshot.

The three origin tips each carry exactly one commit that head lacks — the
"Merge remote-tracking branch 'origin/main' into X" merge commit — and their merges are
content-identical to head (0 conflicts, same tree), so folding them is pure ancestry
satisfaction: it makes every branch tip an ancestor of main with no content change.

The guest_5 `backup/pre-sync-6ffc0861b` WIP snapshot is inspected, not folded yet: it is a
stash-style backup, so its content is reported before any decision.
"""
from __future__ import annotations

import pathlib
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
HEAD = "401af47d4"
FOLD = [
    ("origin/RFC-WF-026", "RFC-WF-026 (origin tip, host Overwatch/_1/_2/_3)"),
    ("origin/SPR-1117", "SPR-1117 (origin tip, host Overwatch_4)"),
    ("origin/DAR-OW-157_Fork_Rebase_Process_Public_Open_Source/03_Synthesis/01_Mikado_Graph",
     "DAR-OW-157 fork/rebase graph (origin tip, host Overwatch_2)"),
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    print("=== fold the three content-identical origin tips ===")
    for ref, label in FOLD:
        rc, out = run("git", "merge-tree", "--write-tree", "main", ref)
        if out.count("CONFLICT"):
            print(f"  {label}: CONFLICT appeared, skipping")
            continue
        rc, out = run("git", "merge", "--no-edit", "-m",
                      f"Fold {label} into main (ancestry satisfaction; content identical)", ref)
        print(f"  {label}: exit={rc} {(out.splitlines() or [''])[-1][:80]}")

    print("\n=== guest_5 WIP snapshot: fetch + inspect ===")
    wip_src = pathlib.Path.home() / "dev_env/clones/Overwatch_5"
    rc, out = run("git", "fetch", "--quiet", str(wip_src),
                  "backup/pre-sync-6ffc0861b:refs/fold/wip-snapshot")
    print(f"  fetch: exit={rc} {out[:120]}")
    if rc == 0:
        rc, log = run("git", "log", "--oneline", f"{HEAD}..refs/fold/wip-snapshot")
        print(f"  unique commits:\n{log}")
        rc, stat = run("git", "diff", "--stat", HEAD, "refs/fold/wip-snapshot")
        print(f"  diff vs head (stat, tail):\n" + "\n".join(stat.splitlines()[-8:]))
        rc, mt = run("git", "merge-tree", "--write-tree", HEAD, "refs/fold/wip-snapshot")
        print(f"  merge-tree conflicts: {mt.count('CONFLICT')}")

    rc, out = run("git", "log", "--oneline", "-4")
    print("\nmain now:\n" + out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
