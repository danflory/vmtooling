#!/usr/bin/env python3
"""Full branch audit: is EVERY branch tip on either estate contained in the unified head?

Covers, from the guest's authoritative clone:
  - all origin/* branches (the pushed tips)
  - every local branch in each guest clone
  - every local branch in each HOST clone, reached read-only via the guest's
    /mnt/host/dev_env/<clone> mount (the host estate is intentionally frozen at 0555,
    which does not prevent reading or fetching FROM it)
Nothing is modified: fetches land in the guest clone's object store only.
"""
from __future__ import annotations

import pathlib
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
GUEST = pathlib.Path.home() / "dev_env/clones"
HOST_MNT = pathlib.Path("/mnt/host/dev_env")
HEAD = "origin/main"


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=MAIN)
    return r.returncode, (r.stdout + r.stderr).strip()


def ancestors(ref: str) -> tuple[bool, int]:
    present = run("git", "cat-file", "-e", f"{ref}^{{commit}}")[0] == 0
    if not present:
        return False, -1
    in_head = run("git", "merge-base", "--is-ancestor", ref, HEAD)[0] == 0
    uniq = int(run("git", "rev-list", "--count", f"{HEAD}..{ref}")[1].splitlines()[-1] or 0)
    return in_head, uniq


def main() -> None:
    print("=== origin/* tips ===")
    rc, out = run("git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    for ref in sorted(l for l in out.splitlines() if l and "HEAD" not in l):
        in_head, uniq = ancestors(ref)
        flag = "IN HEAD" if in_head else "*** NOT FOLDED ***"
        print(f"  {ref:<64} {flag:22s} unique={uniq}")

    print("\n=== guest local branches ===")
    for clone in ["Overwatch", "Overwatch_1", "Overwatch_2", "Overwatch_3", "Overwatch_4", "Overwatch_5"]:
        p = GUEST / clone
        if not (p / ".git").exists():
            continue
        out = subprocess.run(["git", "-C", str(p), "for-each-ref", "--format=%(refname:short)",
                              "refs/heads"], capture_output=True, text=True).stdout
        for b in sorted(x for x in out.splitlines() if x):
            tip = subprocess.run(["git", "-C", str(p), "rev-parse", b], capture_output=True,
                                 text=True).stdout.strip()
            if not tip or run("git", "cat-file", "-e", f"{tip}^{{commit}}")[0] != 0:
                print(f"  {clone:<12} {b:<52} (tip object not in the guest store) tip={tip[:9]}")
                continue
            in_head, uniq = ancestors(tip)
            if not in_head:
                print(f"  {clone:<12} {b:<52} NOT FOLDED  unique={uniq} tip={tip[:9]}")

    print("\n=== host local branches (read-only via /mnt/host) ===")
    for clone in ["Overwatch", "Overwatch_1", "Overwatch_2", "Overwatch_3", "Overwatch_4", "Overwatch_5"]:
        src = HOST_MNT / clone
        if not (src / ".git").exists():
            print(f"  {clone:<12} (not visible at {src})")
            continue
        out = subprocess.run(["git", "-C", str(src), "for-each-ref", "--format=%(refname:short)",
                              "refs/heads"], capture_output=True, text=True).stdout
        for b in sorted(x for x in out.splitlines() if x):
            tip = subprocess.run(["git", "-C", str(src), "rev-parse", b], capture_output=True,
                                 text=True).stdout.strip()
            if not tip:
                continue
            # bring the object into the guest object store, then judge it there
            run("git", "fetch", "--quiet", str(src), f"{b}:refs/hostaudit/{clone}-{b.replace('/', '_')}")
            in_head, uniq = ancestors(f"refs/hostaudit/{clone}-{b.replace('/', '_')}")
            if not in_head:
                print(f"  {clone:<12} {b:<52} NOT FOLDED  unique={uniq} tip={tip[:9]}")
    print("\n(done: only NOT-FOLDED rows are listed; absence of a clone above means all its branches are in head)")


if __name__ == "__main__":
    main()
