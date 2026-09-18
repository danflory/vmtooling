#!/usr/bin/env python3
"""Pull the consolidated origin/main into all six guest clones.

For each clone:
  - resolve the remote that points at the Overwatch GitHub URL (clones use `origin`,
    except Overwatch_5 which uses `Overwatch`);
  - fetch;
  - report branch, dirty count, ahead/behind vs <remote>/main;
  - if the worktree is clean: on `main` fast-forward; on any other branch merge
    <remote>/main in (that is "pulling the sync in" for a feature branch);
  - if dirty: fetch only and report, never touching a dirty worktree.
"""
from __future__ import annotations

import pathlib
import subprocess

CLONES = ["Overwatch", "Overwatch_1", "Overwatch_2", "Overwatch_3", "Overwatch_4", "Overwatch_5"]
BASE = pathlib.Path.home() / "dev_env/clones"


def run(cwd: pathlib.Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=cwd)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> None:
    for name in CLONES:
        p = BASE / name
        if not (p / ".git").exists():
            print(f"=== {name}: no git repo, skipped")
            continue
        remotes = run(p, "git", "remote")[1].split()
        remote = "origin" if "origin" in remotes else (remotes[0] if remotes else "")
        if not remote:
            print(f"=== {name}: no remote, skipped")
            continue
        branch = run(p, "git", "rev-parse", "--abbrev-ref", "HEAD")[1]
        run(p, "git", "fetch", "--quiet", remote, "main")
        dirty = run(p, "git", "status", "--porcelain")[1]
        dirty_n = len(dirty.splitlines()) if dirty else 0
        ab = run(p, "git", "rev-list", "--left-right", "--count", f"HEAD...{remote}/main")[1]
        print(f"=== {name}: branch={branch} remote={remote} dirty={dirty_n} ahead/behind={ab}")

        if dirty_n:
            print("    fetched only (dirty worktree left untouched)")
            continue
        if branch == "main":
            rc, out = run(p, "git", "merge", "--ff-only", f"{remote}/main")
            print(f"    fast-forward: exit={rc} {out[-160:]}")
        else:
            rc, out = run(p, "git", "merge", "--no-edit",
                          "-m", f"Merge {remote}/main into {branch} (final sync)",
                          f"{remote}/main")
            tail = out.splitlines()[-3:] if out else []
            print(f"    merge main into {branch}: exit={rc} {' | '.join(tail)[-200:]}")
        ab = run(p, "git", "rev-list", "--left-right", "--count", f"HEAD...{remote}/main")[1]
        print(f"    now ahead/behind={ab}")


if __name__ == "__main__":
    main()
