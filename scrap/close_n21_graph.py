#!/usr/bin/env python3
"""Update DAR-OW-158 node N21 (SPR-1137) to CLOSED after the SPR's closure.

Run AFTER the swarm writers finish, to avoid contending with them.
Idempotent.
"""
from __future__ import annotations

import pathlib
import subprocess

GRAPH = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/03_Synthesis/01_Mikado_Graph.md"
)
GRAPH_CI = 49871
N21 = "N21"

OLD_ROW_MARKER = "| 21 | N21 — SPR-1137: one squawk, one version, one source"
NEW_ROW = (
    "| 21 | N21 — SPR-1137: one squawk, one version, one source "
    "(migration lint gate vs runtime sidecar) | SPR | SPR-1137 (50249, CLOSED) | N1, N12 | "
    "✅ DONE 2026-09-18: the gate now resolves squawk from the repository-vendored artifact "
    "(pinned SHA-256, shared with the sidecar image) instead of a hand-placed venv copy, so a "
    "fresh clone runs the gate (verified in a clone with no venv squawk); sqlfluff pinned and "
    "resolved explicitly; the vendored binary registered as CI 50251; TP-206 pre-fix FAIL → "
    "post-fix PASS; CR 50253; FIDO-sealed closure |"
)
MERMAID_OLD = '    N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ⚙️"]'
MERMAID_NEW = '    N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ✅"]'


def db(*args: str) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True)
    ok = '"status": "success"' in (r.stdout + r.stderr)
    print(f"  {'OK' if ok else 'FAIL'}: {' '.join(args[:3])}")
    if not ok:
        print("   ", (r.stdout + r.stderr)[-200:])
    return ok


def main() -> int:
    db("upsert_mikado_node", "--graph-ci-id", str(GRAPH_CI), "--node-id", N21,
       "--node-type", "SPR",
       "--description",
       "SPR-1137 - one squawk, one version, one source. CLOSED 2026-09-18: the migration lint "
       "gate resolves its squawk engine from the repository-vendored artifact (pinned SHA-256, "
       "shared with the migration-sidecar image) instead of a hand-placed venv copy, so a fresh "
       "clone can run the gate; sqlfluff is pinned in setup_venv.sh and resolved explicitly; the "
       "vendored binary is registered as CI 50251. Evidence: TP-206 (50250) pre-fix FAIL -> "
       "post-fix PASS; CR 50253 (review_scope python); FIDO-sealed closure via ow_close_ci.",
       "--status", "CLOSED", "--artifact-ci-id", "50249",
       "--depends-on", "N1,N12", "--execution-order", "21")

    t = GRAPH.read_text()
    applied = 0
    if OLD_ROW_MARKER in t:
        lines = t.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(OLD_ROW_MARKER):
                lines[i] = NEW_ROW
                applied += 1
                break
        t = "\n".join(lines) + "\n"
    if MERMAID_OLD in t:
        t = t.replace(MERMAID_OLD, MERMAID_NEW, 1)
        applied += 1
    GRAPH.write_text(t)
    print(f"graph edits applied: {applied}/2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
