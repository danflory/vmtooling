#!/usr/bin/env python3
"""Final reference repoints for the N10/N11 reclassification (4 lingering spots)."""
from __future__ import annotations

import pathlib

DAR = pathlib.Path("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation")
SPR_DIR = pathlib.Path(
    "docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association"
)

EDITS: list[tuple[pathlib.Path, str, str]] = [
    (
        DAR / "02_Research/00_What_I_Read.md",
        "Guest jcode deployment review (this research, 23) - N10/N11 host-SSD home error and its abandonment",
        "Guest jcode deployment review (N10/N11 rework apply note, 04_Implementation/03) - host-SSD home error and its abandonment",
    ),
    (
        DAR / "03_Synthesis/01_Mikado_Graph.md",
        "teardown + TP-188 coverage. See research 23",
        "teardown + TP-188 coverage. See the N10/N11 rework apply note",
    ),
    (
        DAR / "03_Synthesis/01_Mikado_Graph.md",
        "**research 23 (udrs 50216)**",
        "**the N10/N11 rework apply note (udrs 50216)**",
    ),
    (
        SPR_DIR / "README.md",
        "| `02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md` | 50216 | research record for this rework |",
        "| `04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md` | 50216 | apply record for this rework |",
    ),
]


def main() -> None:
    for path, old, new in EDITS:
        t = path.read_text()
        if old in t:
            path.write_text(t.replace(old, new, 1))
            print(f"updated {path.name}")
        elif new in t:
            print(f"already updated {path.name}")
        else:
            print(f"MISS in {path.name}: {old[:70]!r}")


if __name__ == "__main__":
    main()
