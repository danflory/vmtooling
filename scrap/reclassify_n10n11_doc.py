#!/usr/bin/env python3
"""Reclassify the N10/N11 jcode-home doc from research to implementation.

Operator direction (2026-09-18): its centre of gravity is "what was done about a
deployment error", so it belongs in 04_Implementation as an apply record.

  move : 02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md
      -> 04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md
  type : DAR.RESEARCH -> DAR.RESEARCH.IMPLEMENTATION
  CI   : repoint 50216 to the new storage_path (keeps the same serial)

Also repoints every reference to the old path. Idempotent.
"""
from __future__ import annotations

import pathlib
import subprocess

DAR = pathlib.Path("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation")
OLD = DAR / "02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md"
NEW = DAR / "04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md"
CI_ID = 50216
NEW_TITLE = "DAR-OW-158 N10/N11 - Guest JCode Home Rework (host-SSD association removed)"

OLD_PATH = str(OLD)
NEW_PATH = str(NEW)

REFERENCES: list[tuple[pathlib.Path, str, str]] = [
    (
        DAR / "04_Implementation/../../SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/SPR-1135.md",
        "- `02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md` = UDRS\n  **50216** (the research record for this rework).",
        "- `04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md` = UDRS **50216** (the apply\n  record for this rework).",
    ),
    (
        DAR / "04_Implementation/../../SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/SPR-1135.md",
        "`02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md`, UDRS 50216",
        "`04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md`, UDRS 50216",
    ),
    (
        DAR / "04_Implementation/../../SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/SPR-1135.md",
        "`02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md`",
        "`04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md`",
    ),
    (
        DAR / "02_Research/00_What_I_Read.md",
        "Guest jcode deployment review (this research, 23)",
        "Guest jcode deployment review (N10/N11 rework apply note, 04_Implementation/03)",
    ),
    (
        DAR / "03_Synthesis/01_Mikado_Graph.md",
        "Governed by SPR-1135 (udrs 50221) — teardown + TP-188 coverage. See research 23\n"
        "│       │   (udrs 50216).",
        "Governed by SPR-1135 (udrs 50221) — teardown + TP-188 coverage. See the N10/N11 rework\n"
        "│       │   apply note (udrs 50216).",
    ),
    (
        DAR / "03_Synthesis/01_Mikado_Graph.md",
        "records the requirement and the findings.",
        "records the requirement and the findings; the apply record is 04_Implementation/03 (udrs 50216).",
    ),
]


def run(*args: str) -> tuple[bool, str]:
    r = subprocess.run(list(args), capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def main() -> None:
    if OLD.exists():
        NEW.parent.mkdir(parents=True, exist_ok=True)
        ok, out = run("git", "mv", str(OLD), str(NEW))
        print(f"git mv: {'OK' if ok else out}")
    elif NEW.exists():
        print("already moved")
    else:
        raise SystemExit("ERROR: neither source nor destination exists")

    # frontmatter: type + title
    text = NEW.read_text()
    text = text.replace("type: DAR.RESEARCH\n", "type: DAR.RESEARCH.IMPLEMENTATION\n", 1)
    text = text.replace(
        "title: Guest JCode Deployment Standard Install No Host Association",
        f"title: {NEW_TITLE}", 1)
    NEW.write_text(text)
    print("frontmatter: type -> DAR.RESEARCH.IMPLEMENTATION, title updated")

    # repoint the CI
    ok, out = run(".venv/bin/python", "OW_tools/db_write.py", "update_ci_path",
                  "--ci-id", str(CI_ID), "--path", NEW_PATH)
    print(f"update_ci_path: {'OK' if ok else out}")

    # refresh the registered fields from the file
    ok, out = run(".venv/bin/python", "OW_tools/db_write.py", "sync_ci", "--path", NEW_PATH)
    print(f"sync_ci: {'OK' if ok else out[-200:]}")
    ok, out = run(".venv/bin/python", "OW_tools/db_write.py", "query_ci_by_id", "--ci-id", str(CI_ID))
    for line in out.splitlines():
        if '"title"' in line and '"storage_path"' in line:
            print("DB now:", line.strip()[:300])

    # references
    for path, old, new in REFERENCES:
        t = path.read_text()
        if old in t:
            path.write_text(t.replace(old, new))
            print(f"ref updated in {path.name}: {old[:60]!r}")
        elif new in t:
            print(f"ref already updated in {path.name}")
        else:
            print(f"REF MISS in {path.name}: {old[:60]!r}")


if __name__ == "__main__":
    main()
