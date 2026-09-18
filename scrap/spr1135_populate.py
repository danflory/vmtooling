#!/usr/bin/env python3
"""Populate SPR-1135: success criteria from the anchor VCL table, and CI links.

createSPR2 Step 3 + the operator's emphasis on relating as many documents as are
genuinely related. Run from the workspace root on the guest.
"""
from __future__ import annotations


import pathlib
import re
import subprocess

ANCHOR_ID = 50221
FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association"
)

# (source, target, link_type) — link types drawn from the live vocabulary:
# impacts / authorized-by / belongs-to / references / implements / evidence-for
LINKS: list[tuple[int, int, str]] = [
    (50221, 49825, "authorized-by"),   # SPR <- DAR-OW-158 (authorizing artifact)
    (50221, 49841, "impacts"),         # SPR changes TP-188 (the closure gate)
    (50221, 49871, "impacts"),         # SPR marks N10/N11 in the DAR graph
    (50221, 50034, "references"),      # withdrawn N10/RES-14 design
    (50221, 50052, "references"),      # superseding snapshot-sync mechanism
    (50221, 50215, "references"),      # same-class twin defect (native Postgres)
    (50216, 50221, "evidence-for"),    # research 23 is the evidence record
    (50222, 50221, "belongs-to"),      # deficiency report
    (50223, 50221, "belongs-to"),      # TP change report
    (50224, 50221, "belongs-to"),      # README
]


def db(*args: str) -> tuple[bool, str]:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True)
    ok = '"status": "success"' in r.stdout
    return ok, (r.stdout + r.stderr).strip()


def main() -> None:
    anchor = (FOLDER / "SPR-1135.md").read_text()
    sec = anchor.split("## Verification Completion", 1)[1]
    rows = re.findall(r"^\|\s*(V-\d+)\s*\|\s*(.+?)\s*\|\s*(?:⬜|✅)", sec, re.M)
    print(f"VCL rows found: {len(rows)}")
    for num, desc in rows:
        desc = " ".join(desc.split())[:900]
        ok, out = db("upsert_sc", "--ci-id", str(ANCHOR_ID), "--sc-num", num.split("-")[1],
                     "--desc", desc, "--checked", "false")
        print(f"  {num}: {'OK' if ok else 'FAIL ' + out[-200:]}")

    print("links:")
    for src, tgt, kind in LINKS:
        ok, out = db("insert_link", "--source", str(src), "--target", str(tgt), "--type", kind)
        print(f"  {src} -[{kind}]-> {tgt}: {'OK' if ok else 'FAIL ' + out[-200:]}")

    print("sub-doc parents:")
    for f in sorted(FOLDER.glob("0*.md")):
        parent = re.search(r"^parent:\s*(\S+)", f.read_text(), re.M)
        print(f"  {f.name}: parent={parent.group(1) if parent else '?'}")


if __name__ == "__main__":
    main()
