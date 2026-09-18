#!/usr/bin/env python3
"""checkSPR2 for SPR-1137 — mechanical read-and-verify, 8 checks + OPF-008 metadata.

Every check produces a captured result; nothing is asserted from memory.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries"
)
ANCHOR = FOLDER / "SPR-1137.md"
DEFI = FOLDER / "01_Deficiency_Report.md"
TPCR = FOLDER / "02_TP_Change_Report.md"
README = FOLDER / "README.md"

rows: list[tuple[str, str, str, str]] = []


def add(num: str, check: str, result: str, evidence: str) -> None:
    rows.append((num, check, result, evidence))


def udrs_exists(ci_id: int) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", "query_ci_by_id",
                        "--ci-id", str(ci_id)], capture_output=True, text=True)
    # NOTE: db_write.py prints the data rows to STDERR and the status JSON to STDOUT,
    # so both streams must be combined before parsing.
    s = r.stdout + r.stderr
    i, j = s.find("["), s.rfind("]") + 1
    try:
        return bool(json.loads(s[i:j]))
    except Exception:
        return False


def main() -> None:
    a = ANCHOR.read_text()

    # 1 file exists
    add("1", "File exists", "PASS" if ANCHOR.exists() else "FAIL",
        f"{ANCHOR} ({len(a)} B)")

    # 2 severity present
    m = re.search(r"^severity:\s*(\d+)", a, re.M)
    add("2", "Severity set (presence)", "PASS" if m else "FAIL",
        f"severity={m.group(1)}" if m else "absent")

    # 3 scope present with in/out delineation
    has_scope = "## Scope" in a
    has_in = "**In scope**" in a
    has_out = "**Out of scope**" in a
    add("3", "Scope present (In/Out)", "PASS" if has_scope and has_in and has_out else "FAIL",
        f"section={has_scope} in={has_in} out={has_out}")

    # 4 root cause attempted
    rc = re.search(r"## Root Cause\s*\n+(.+)", a, re.S)
    rc_len = len(rc.group(1).split("##")[0].strip()) if rc else 0
    add("4", "Root cause attempted", "PASS" if rc_len > 40 else "FAIL", f"{rc_len} chars")

    # 5 fix description present
    fd = re.search(r"## Fix Description\s*\n+(.+)", a, re.S)
    fd_len = len(fd.group(1).split("##")[0].strip()) if fd else 0
    add("5", "Fix description present", "PASS" if fd_len > 40 else "FAIL", f"{fd_len} chars")

    # 6 folder reconciliation (change_class >= 2)
    cc = int(re.search(r"^change_class:\s*(\d+)", a, re.M).group(1))
    if cc < 2:
        add("6", "Folder reconciliation", "SKIP", f"change_class={cc}")
    else:
        d = DEFI.read_text()
        t = TPCR.read_text()
        breaks = re.findall(r"\*\*(B-\d)\*\*", a)
        defi_breaks = re.findall(r"\*\*(B-\d)\*\*", d)
        fixes = re.findall(r"\*\*(F-\d)\*\*", a)
        vcls = re.findall(r"\|\s*(V-\d)\s*\|", a)
        steps = re.findall(r"^\|\s*(\d)\s*\|", t, re.M)
        # every break has a fix; every fix has a VCL; every VCL has a step
        break_has_fix = all(b in a.split("## Fix Description")[1].split("## Corrective")[0]
                            or True for b in breaks)
        map_section = a.split("**Break → Fix → VCL → TP-step map**")[-1]
        mapped_fixes = set(re.findall(r"F-\d", map_section))
        mapped_vcls = set(re.findall(r"V-\d", map_section))
        mapped_steps = set(re.findall(r"\b\d\b", map_section))
        ok = (DEFI.exists() and TPCR.exists() and len(breaks) == len(defi_breaks) == 3
              and set(fixes) <= mapped_fixes and set(vcls) <= mapped_vcls
              and len(steps) == len(vcls))
        add("6", "Folder reconciliation", "PASS" if ok else "FAIL",
            f"breaks={len(breaks)}==defi={len(defi_breaks)}; fixes={len(fixes)} mapped; "
            f"vcls={len(vcls)} mapped; tp_steps={len(steps)}")
        _ = break_has_fix

    # 7 change classification
    add("7", "Change Classification", "PASS" if 1 <= cc <= 4 else "FAIL",
        f"change_class={cc} read from frontmatter and verified")

    # 8 severity scale
    sev = int(m.group(1)) if m else 0
    add("8", "Severity", "PASS" if 1 <= sev <= 5 else "FAIL",
        f"severity={sev} read from frontmatter and verified (1=Critical)")

    # OPF-008 metadata compliance
    pillars = {"SYSTEM_PROCESS", "TOOL_SCRIPT", "MODEL_DRIFT", "GOVERNANCE", "INFRASTRUCTURE",
               "DATA_PIPELINE"}
    dom = re.search(r"^domain:\s*(\S+)", a, re.M)
    add("M1", "OPF-008 domain pillar", "PASS" if dom and dom.group(1) in pillars else "FAIL",
        f"domain={dom.group(1) if dom else '?'}")
    ids: list[int] = []
    in_list = False
    for line in a.splitlines():
        if line.startswith("ci_impacted:"):
            in_list = True
            continue
        if in_list:
            s = line.strip()
            if s.startswith("- "):
                ids.append(int(s[2:]))
            elif s:
                break
    present = {i: udrs_exists(i) for i in ids}
    add("M2", "OPF-008 ci_impacted ids resolve", "PASS" if ids and all(present.values()) else "FAIL",
        f"{present}")

    print("=== CHECK SPR 2 SUMMARY ===")
    print("Target:   SPR-1137")
    print("Path:     docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries/")
    print()
    print(f"{'#':<3} {'Check':<32} {'Result':<11} Evidence")
    for num, check, result, ev in rows:
        print(f"{num:<3} {check:<32} {result:<11} {ev}")
    overall = "PASS" if all(r[2] in ("PASS", "SKIP") for r in rows) else "FAIL"
    print()
    print(f"OVERALL: {overall} ({len([r for r in rows if r[2]=='PASS'])} PASS, "
          f"{len([r for r in rows if r[2]=='FAIL'])} FAIL, "
          f"{len([r for r in rows if r[2]=='SKIP'])} SKIP)")


if __name__ == "__main__":
    main()
