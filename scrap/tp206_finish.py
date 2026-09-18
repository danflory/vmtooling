#!/usr/bin/env python3
"""Finish the TP-206 setup: SC rows for its six steps, link it in SPR-1137's frontmatter,
and report the state for commit."""
from __future__ import annotations

import pathlib
import re
import subprocess

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
TP = MAIN / "docs/praca/TP/TP-206.md"
SPR = MAIN / ("docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_"
              "squawk_binaries/SPR-1137.md")
TP_CI = 50250
TP_REF = "TP-206 (50250)"


def db(*args: str) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True, cwd=MAIN)
    ok = '"status": "success"' in r.stdout + r.stderr
    if not ok:
        print("   FAIL:", (r.stdout + r.stderr)[-160:])
    return ok


def main() -> int:
    t = TP.read_text()
    steps = re.findall(r"^## Step (\d) — (.+?)$", t, re.M)
    print(f"TP-206 steps found: {len(steps)}")
    for num, title in steps:
        ok = db("upsert_sc", "--ci-id", str(TP_CI), "--sc-num", num,
                "--desc", f"Step {num}: {title}", "--checked", "false")
        print(f"  step {num}: {'OK' if ok else 'FAIL'}")

    s = SPR.read_text()
    if f"tp_gap_reference: {TP_REF}" not in s:
        s = re.sub(r"^tp_gap_reference:.*$", f"tp_gap_reference: {TP_REF}", s, count=1, flags=re.M)
        # annotate that the gap was resolved by scaffolding
        s = s.replace("## Root Cause",
                      "> **TP gap resolved**: the `no_tp` finding at creation was resolved by\n"
                      f"> scaffolding **{TP_REF}** (six steps, one per VCL), which was executed against the\n"
                      "> pre-fix tree and recorded as a `pre_fix` FAIL before any fix was applied.\n\n"
                      "## Root Cause", 1)
        SPR.write_text(s)
        print("SPR frontmatter: tp_gap_reference ->", TP_REF)

    print("\nSPR frontmatter now:")
    for line in SPR.read_text().splitlines()[:22]:
        if line.startswith(("tp_gap", "severity", "change_class", "status", "id:")):
            print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
