#!/usr/bin/env python3
"""closeSPR2 lessons gate: log the distilled lessons from SPR-1137."""
from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"
SRC = "50249"


def db(*args: str) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True, cwd=REPO)
    ok = '"status": "success"' in (r.stdout + r.stderr)
    print(f"  {'OK' if ok else 'FAIL'} {' '.join(args[:2])}")
    if not ok:
        print("   ", (r.stdout + r.stderr)[-200:])
    return ok


def main() -> int:
    db("log_lesson", "--source-ci-id", SRC, "--key", "gate-engine-provenance",
       "--title", "A gate's rule engine is a governed artifact - pin one version for every consumer",
       "--finding",
       "squawk ran at two stages of the DB migration pipeline: the commit-time A6 gate resolved "
       "it from the Python venv (hand-placed 2.65.0, absent from requirements and from "
       "setup_venv.sh) while the migration sidecar ran the RFC-OW-271 vendored 2.59.0 baked into "
       "the image. Nothing asserted the two matched, and a fresh clone had no gate binary at all: "
       "the gate raised FileNotFoundError and blocked every migration commit in 3 of the 6 clones.",
       "--reuse",
       "Treat any binary whose version changes a gate's verdict as a governed artifact. Vendor it "
       "in the repository with a pinned SHA-256, resolve every consumer from that single artifact, "
       "assert the hash at gate time so drift fails loudly, and keep pip-installable engines in the "
       "venv with pinned versions resolved by explicit path (never a bare PATH lookup). Two "
       "consumers may keep two runtime copies; they must never have two sources or two versions.",
       "--node-type", "CODE", "--topic", "gate_engine_provenance", "--grade", "CRITICAL")

    db("log_lesson", "--source-ci-id", SRC, "--key", "closespr2-cr-status-predicate",
       "--title", "closeSPR2's CR gate filters on status=APPROVED, but every CR is stored ACTIVE",
       "--finding",
       "closeSPR2's Code Review gate requires a CR with review_scope python and runs "
       "`lookup_ci --status APPROVED --type cr`. Every CR row in auth.udrs carries status=ACTIVE "
       "with phase RELEASED or DRAFT, so the predicate returns 0 rows and the gate can never pass "
       "as written. The approved verdict lives in the document (review_verdict, title), not in the "
       "EFSM status: the frontmatter `status: APPROVED` is documentary and sync_ci rejects "
       "(RELEASED, APPROVED) as an EFSM violation.",
       "--reuse",
       "When a closure gate demands a CR, query by parent_ci plus doc_type and read the "
       "document's review_verdict; do not filter on status=APPROVED. If you must register such a "
       "CR, use the EFSM-valid pair (RELEASED, ACTIVE) and keep the verdict in review_verdict.",
       "--node-type", "WORKFLOW", "--topic", "closure_gate_defect", "--grade", "ADVISORY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
