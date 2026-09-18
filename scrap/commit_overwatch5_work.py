#!/usr/bin/env python3
"""Commit Overwatch_5's uncommitted work, holding one item for operator decision.

Commits: 3 modified DAR docs + 1 modified SPR doc, the 12 SR-2124..2127 session
records, and the 2 pgTAP 339 scripts. Registers every new path first (A20 gate).

HOLDS: the untracked `docs/praca/SPR/SPR-1133_.../` directory. It is a STALE
DUPLICATE of CI 50045, whose canonical storage_path in the DB is
`docs/praca/SPR/closed/SPR-1133_.../SPR-1133.md`. Committing it would create a
second, unregistered path for the same CI id (and the A20 gate would reject it).

Run from Overwatch_5's root.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
HOLD = "docs/praca/SPR/SPR-1133_EFSM_DRAFT_phase_supersession_gap__CI_50034_cannot_be_superseded_via_governed_path"

TRACKED = [
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research/20_Closure_Sync_Tooling_Requirements.md",
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/02_Research/21_JCode_Config_State_Sync.md",
    "docs/praca/DAR_Constellation.md",
    "docs/praca/SPR/closed/SPR-1133_EFSM_DRAFT_phase_supersession_gap__CI_50034_cannot_be_superseded_via_governed_path/SPR-1133.md",
]

NEW_MD = [f"docs/SR/{n}_{d}.md" for n in (2124, 2125, 2126, 2127)
          for d in ("decisions", "findings", "results_log")]

NEW_CODE = [
    "firecontrol/tests/pgtap/339_spr1133_draft_supersession_delta_e2e.sql",
    "firecontrol/tests/pgtap/339_spr1133_draft_supersession_delta_smoke.sql",
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr).strip()


def register() -> None:
    for p in NEW_MD:
        if not (ROOT / p).exists():
            print(f"  MISSING {p}")
            continue
        rc, out = run(".venv/bin/python", "OW_tools/db_write.py", "sync_ci", "--path", p)
        ok = "assigned_id" in out or "PATCHED" in out
        print(f"  sync_ci {pathlib.Path(p).name}: {'OK' if ok else out[-120:]}")
    for p in NEW_CODE:
        if not (ROOT / p).exists():
            print(f"  MISSING {p}")
            continue
        rc, out = run(".venv/bin/python", "OW_tools/db_write.py", "ow_write_ci", "--path", p,
                      "--field", "doc_type=CODE")
        print(f"  ow_write_ci {pathlib.Path(p).name}: {'OK' if 'REGISTERED' in out else out[-120:]}")


def main() -> int:
    if (ROOT / HOLD).exists():
        print(f"HOLDING (stale duplicate of CI 50045): {HOLD}")
    print("registering new paths:")
    register()

    paths = [p for p in TRACKED + NEW_MD + NEW_CODE if (ROOT / p).exists()]
    rc, out = run("git", "add", "--", *paths)
    if rc != 0:
        print("git add failed:", out, file=sys.stderr)
        return 1
    rc, out = run("git", "status", "--short", "--", *paths)
    print("staged:\n" + out)

    msg = (
        "DAR-OW-158: commit Overwatch_5 pending work (SR-2124..2127, pgTAP 339, DAR docs)\n"
        "\n"
        "- SR session records 2124-2127 (decisions/findings/results_log)\n"
        "- pgTAP 339 SPR-1133 draft-supersession delta (e2e + smoke)\n"
        "- DAR-OW-158 research 20/21, DAR_Constellation, closed SPR-1133 frontmatter\n"
        "\n"
        "Held back: docs/praca/SPR/SPR-1133_.../ is a stale duplicate of CI 50045 whose\n"
        "canonical path is docs/praca/SPR/closed/SPR-1133_.../SPR-1133.md\n"
    )
    rc, out = run("git", "commit", "-m", msg)
    print("commit:", out[-600:])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
