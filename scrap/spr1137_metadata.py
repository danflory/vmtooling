#!/usr/bin/env python3
"""SPR-1137: install the content, then populate PRACA metadata, success criteria,
CI links, and the DAR-OW-158 implementation node (N21).
"""
from __future__ import annotations

import pathlib
import re
import subprocess

FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries"
)
ANCHOR = 50249
GRAPH = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/03_Synthesis/01_Mikado_Graph.md"
)
GRAPH_CI = 49871

LINKS = [
    (50249, 40175, "authorized-by"),
    (50249, 39275, "impacts"),
    (50249, 42098, "impacts"),
    (50249, 42031, "references"),
    (50249, 40080, "references"),
    (50249, 49825, "references"),
    (50249, 49871, "impacts"),
    (50246, 50249, "belongs-to"),
    (50247, 50249, "belongs-to"),
    (50248, 50249, "belongs-to"),
]

N21_DESC = (
    "[SPR] SPR-1137 - one squawk, one version, one source. The commit-time A6 migration lint "
    "gate (firecontrol/gates/gate_sql_lint.py) resolves squawk from the Python venv (hand-placed "
    "2.65.0, not in requirements, not installed by setup_venv.sh), while the migration sidecar's "
    "runtime lint runs the RFC-OW-271 vendored 2.59.0 baked into the image. The two stages can "
    "therefore disagree about the same migration, and a fresh clone has no gate binary at all. "
    "Governed by SPR-1137 (udrs 50249): make the vendored binary the single source, point the "
    "gate at it, make it reproducible via setup_venv.sh, assert gate==image version, and register "
    "the vendored binary as a CI."
)

ROW_ANCHOR = (
    "| 20 | N20 — Wire the enforcement hooks into all guest clones (per-clone pre-commit gates) |"
)
MERMAID_ANCHOR = '    N20["N20 [TOOL] Enforcement hooks<br/>in all clones ⚙️"]'
EDGE_ANCHOR = "    N18 --> N20\n"


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def db(*args: str) -> bool:
    rc, out = run(".venv/bin/python", "OW_tools/db_write.py", *args)
    ok = '"status": "success"' in out
    if not ok:
        print("   FAIL:", out[-200:])
    return ok


def main() -> int:
    print("=== PRACA metadata ===")
    print("  upsert_praca:", db("upsert_praca", "--artifact-id", "SPR-1137",
                                "--domain", "INFRASTRUCTURE", "--severity", "3",
                                "--ci-ids", str(ANCHOR)))

    print("=== success criteria (VCL) ===")
    text = (FOLDER / "SPR-1137.md").read_text()
    sec = text.split("## Verification Completion", 1)[1]
    rows = re.findall(r"^\|\s*(V-\d+)\s*\|\s*(.+?)\s*\|\s*⬜\s*\|", sec, re.M)
    for num, desc in rows:
        d = " ".join(desc.split())[:900]
        print(f"  {num}:", db("upsert_sc", "--ci-id", str(ANCHOR), "--sc-num", num.split("-")[1],
                              "--desc", d, "--checked", "false"))

    print("=== links ===")
    for src, tgt, kind in LINKS:
        print(f"  {src} -[{kind}]-> {tgt}:", db("insert_link", "--source", str(src),
                                                "--target", str(tgt), "--type", kind))

    print("=== DAR-OW-158 implementation node N21 ===")
    print("  node:", db("upsert_mikado_node", "--graph-ci-id", str(GRAPH_CI), "--node-id", "N21",
                        "--node-type", "SPR", "--description", N21_DESC,
                        "--status", "IN_PROGRESS", "--artifact-ci-id", str(ANCHOR),
                        "--depends-on", "N1,N12", "--execution-order", "21"))

    g = GRAPH.read_text()
    applied = 0
    if "| 21 | N21" not in g:
        row = (ROW_ANCHOR + "\n| 21 | N21 — SPR-1137: one squawk, one version, one source "
               "(migration lint gate vs runtime sidecar) | SPR | SPR-1137 (50249) | N1, N12 | "
               "⚙️ SPR scaffolded 2026-09-18; gate runs a hand-placed venv squawk 2.65.0 while the "
               "sidecar runs the vendored 2.59.0 — consolidation pending |")
        if ROW_ANCHOR in g:
            g = g.replace(ROW_ANCHOR, row, 1)
            applied += 1
    if 'N21["N21 [SPR]' not in g and MERMAID_ANCHOR in g:
        g = g.replace(MERMAID_ANCHOR, MERMAID_ANCHOR + '\n    N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ⚙️"]', 1)
        applied += 1
    if "N12 --> N21" not in g and EDGE_ANCHOR in g:
        g = g.replace(EDGE_ANCHOR, EDGE_ANCHOR + "    N12 --> N21\n", 1)
        applied += 1
    GRAPH.write_text(g)
    print(f"  graph edits applied: {applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
