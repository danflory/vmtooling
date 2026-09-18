#!/usr/bin/env python3
"""Fix-ups for the N10/N11 reclassification:
 1. DB doc_type/title for CI 50216 (sync_ci repointed the path but not the type).
 2. Reference repoints, with CORRECT paths (the SPR lives at docs/praca/SPR/).
Idempotent.
"""
from __future__ import annotations

import pathlib
import subprocess

DAR = pathlib.Path("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation")
SPR = pathlib.Path(
    "docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/SPR-1135.md"
)
OLD_REF = "02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md"
NEW_REF = "04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md"
CI_ID = 50216
NEW_TITLE = "DAR-OW-158 N10/N11 - Guest JCode Home Rework (host-SSD association removed)"
NEW_PATH = str(DAR / "04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md")


def db(*args: str) -> tuple[bool, str]:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True)
    return '"status": "success"' in r.stdout, (r.stdout + r.stderr).strip()


def main() -> None:
    ok, out = db("ow_write_ci", "--path", NEW_PATH,
                 "--field", "doc_type=DAR.RESEARCH.IMPLEMENTATION",
                 "--field", f"title={NEW_TITLE}")
    print(f"ow_write_ci (doc_type/title): {'OK' if ok else out[-200:]}")
    ok, out = db("query_ci_by_id", "--ci-id", str(CI_ID))
    for line in out.splitlines():
        if '"title"' in line:
            print("DB now:", line.strip()[:260])

    for path in (SPR, DAR / "02_Research/00_What_I_Read.md", DAR / "03_Synthesis/01_Mikado_Graph.md"):
        t = path.read_text()
        if OLD_REF in t:
            path.write_text(t.replace(OLD_REF, NEW_REF))
            print(f"repointed {path.name}")
        elif NEW_REF in t:
            print(f"already repointed {path.name}")
        else:
            print(f"no reference in {path.name}")

    # graph narrative: name the apply note
    g = DAR / "03_Synthesis/01_Mikado_Graph.md"
    t = g.read_text()
    old = "records the requirement and the findings."
    new = ("records the requirement and the findings; the executed teardown is recorded in\n"
           "04_Implementation/03 (udrs 50216).")
    if old in t and new not in t:
        g.write_text(t.replace(old, new, 1))
        print("graph narrative updated")


if __name__ == "__main__":
    main()
