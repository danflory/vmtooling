#!/usr/bin/env python3
"""Resolve the main + ow5/DAR-OW-158 conflict in research 20.

The only conflict is the `title:` field:
  main  : "DAR-OW-158 — Temporary host→sandbox closure sync tool: requirements + process"
  ow5   : 20_Closure_Sync_Tooling_Requirements   (filename-derived regression)
The DB registers CI 50051 with main's descriptive title, so keep OURS and preserve
ow5's auto-merged content elsewhere in the file.
"""
from __future__ import annotations

import pathlib

P = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research/"
    "20_Closure_Sync_Tooling_Requirements.md"
)


def main() -> int:
    lines = P.read_text().splitlines()
    out, i, resolved = [], 0, 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            ours, theirs = [], []
            i += 1
            while not lines[i].startswith("======="):
                ours.append(lines[i]); i += 1
            i += 1
            while not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i]); i += 1
            i += 1
            out.extend(ours)          # keep main's descriptive title (DB-canonical)
            resolved += 1
        else:
            out.append(lines[i]); i += 1
    P.write_text("\n".join(out) + "\n")
    print(f"{P.name}: {resolved} conflict resolved (kept OURS)")
    print("title now:", [l for l in out if l.startswith("title:")][:1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
