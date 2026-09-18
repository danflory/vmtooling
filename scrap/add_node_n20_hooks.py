#!/usr/bin/env python3
"""Add node N20 to the DAR-OW-158 graph: wire the enforcement hooks into every clone.

Rationale (demonstrated 2026-09-18): only the Overwatch and Overwatch_2 clones carry the
pre-commit dispatcher and gates/; Overwatch_1/_3/_4/_5 have none. Unregistered paths and
gate violations therefore commit freely in the hookless clones and only surface when the
work reaches a hooked clone — which is exactly what happened when _2's
`OW_tools/redact_audit/session_patterns.txt` and _5's `setup_venv.sh` tripped A20 only during
the consolidation merges into main. Complements N18 (server-side push-time enforcement).
"""
from __future__ import annotations

import pathlib
import subprocess

GRAPH = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/03_Synthesis/01_Mikado_Graph.md"
)
GRAPH_CI = 49871
DESC = (
    "[TOOL] Wire the enforcement hooks into all guest clones - DONE 2026-09-18. Only Overwatch and "
    "Overwatch_2 carried the pre-commit dispatcher + gates/; Overwatch_1/_3/_4/_5 had none, so "
    "unregistered paths and gate violations committed freely there and only surfaced when the work "
    "reached a hooked clone (demonstrated: _2's OW_tools/redact_audit/session_patterns.txt and _5's "
    "setup_venv.sh tripped A20 only during the consolidation merges). FIX: ran the governed installer "
    "OW_tools/hooks/install.sh in all six clones, so every clone now carries the canonical set (18 "
    "gate scripts, 13 enabled incl. A24) from the tracked source; Overwatch additionally needed its "
    "pre-commit-signature-gate symlink replaced with the deployed real file (cp refused source == "
    "target) and one stale gate removed. VERIFIED: in the previously-hookless Overwatch_1 a staged "
    "unregistered path is now BLOCKED by A20 (exit 1). Residual: install.sh does not deploy the "
    "git-lfs pre-push guard (not in the tracked source), and the install is per-clone local, so a "
    "fresh clone still needs it - that is N18's per-deploy concern. Complements N18 (server-side "
    "push-time enforcement)."
)

ROW_ANCHOR = (
    "| 19 | N19 — SPR-1135: guest jcode deployment rework (N10/N11 host-SSD home removal) | SPR | SPR-1135 (50221) | N1 | ⚙️ SPR scaffolded 2026-09-18 (anchor 50221, V-1 gap vs TP-188); teardown + TP-188 coverage in progress |"
)
ROW_NEW = (
    ROW_ANCHOR
    + "\n| 20 | N20 — Wire the enforcement hooks into all guest clones (per-clone pre-commit gates) | "
    "TOOL | — | N1, N18 | ✅ DONE 2026-09-18: governed installer run in all six clones (canonical 18 gates / "
    "13 enabled, incl. A24); Overwatch's signature-gate symlink replaced with the deployed file and one stale "
    "gate removed; enforcement verified in a previously-hookless clone (unregistered path BLOCKED by A20). "
    "Residual: no git-lfs pre-push in the tracked installer; the install is per-clone local |"
)

MERMAID_ANCHOR = '    N19["N19 [SPR] SPR-1135 jcode<br/>deployment rework ⚙️"]'
MERMAID_NEW = (
    MERMAID_ANCHOR
    + '\n    N20["N20 [TOOL] Enforcement hooks<br/>in all clones ⚙️"]'
)

EDGE_ANCHOR = "    N1 --> N19\n"
EDGE_NEW = EDGE_ANCHOR + "    N1 --> N20\n    N18 --> N20\n"


def main() -> int:
    r = subprocess.run(
        [".venv/bin/python", "OW_tools/db_write.py", "upsert_mikado_node",
         "--graph-ci-id", str(GRAPH_CI), "--node-id", "N20", "--node-type", "SPR",
         "--description", DESC, "--status", "CLOSED", "--depends-on", "N1,N18",
         "--execution-order", "20"],
        capture_output=True, text=True)
    ok = '"status": "success"' in r.stdout
    print("db node N20:", "OK" if ok else (r.stdout + r.stderr)[-300:])

    text = GRAPH.read_text()
    applied = 0
    for old, new in ((ROW_ANCHOR, ROW_NEW), (MERMAID_ANCHOR, MERMAID_NEW), (EDGE_ANCHOR, EDGE_NEW)):
        if new.split("\n")[0] in text and old not in text:
            continue
        if old in text:
            text = text.replace(old, new, 1)
            applied += 1
        else:
            print(f"  MISS: {old[:60]!r}")
    GRAPH.write_text(text)
    print(f"graph edits applied: {applied}/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
