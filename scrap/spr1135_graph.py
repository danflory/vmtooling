#!/usr/bin/env python3
"""SPR-1135: register the SPR's own graph + node, add the SPR node to the DAR
graph, and mark N10/N11 in the DAR graph document.

Idempotent (string replacements skip when the marker is already present).
Run from the workspace root on the guest.
"""
from __future__ import annotations

import pathlib
import subprocess

GRAPH = pathlib.Path(
    "docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/03_Synthesis/01_Mikado_Graph.md"
)
SPR_ANCHOR = 50221
DAR_GRAPH_CI = 49871

S1_DESC = (
    "Tear down the withdrawn N10/N11 jcode host-SSD home wiring: detach the "
    "vm_sandbox_jcode (and unused vm_sessions) filesystem device from the sandbox domain, "
    "unmount /mnt/vm-sandbox-jcode in the guest, remove the host binds and /etc/fstab lines, "
    "and remove the backing directories."
)
S2_DESC = (
    "Add the TP-188 step that asserts a guest-local jcode home and the absence of any "
    "host-backed jcode share (fails pre-fix, passes post-fix), and mark N10/N11 in the DAR "
    "graph so the written record matches the running topology."
)

EDITS: list[tuple[str, str]] = [
    # 1. N10 node header
    (
        "├── N10 [RES] JCode Home State on Host SSD (RES-14) ⛔ SUPERSEDED",
        "├── N10 [RES] JCode Home State on Host SSD (RES-14) ⛔ SUPERSEDED / REMOVED (SPR-1135)",
    ),
    # 2. N10 closing bullet -> record the residue and the rework
    (
        "│       ├── Source: 02_Research/14_JCode_Home_On_Host_SSD.md (udrs 50034)\n"
        "│       └── ⛔ SUPERSEDED — no live dependencies run through this node",
        "│       ├── Source: 02_Research/14_JCode_Home_On_Host_SSD.md (udrs 50034)\n"
        "│       ├── ⚠️ REWORK 2026-09-18: the revert was a documentation + environment change only;\n"
        "│       │   the deployed wiring survived (domain still exported `vm_sandbox_jcode` and an\n"
        "│       │   unused `vm_sessions`; the guest held an ad-hoc rw mount at /mnt/vm-sandbox-jcode;\n"
        "│       │   host binds + backing dirs remained). Two plausible jcode homes existed at once.\n"
        "│       │   Governed by SPR-1135 (udrs 50221) — teardown + TP-188 coverage. See research 23\n"
        "│       │   (udrs 50216).\n"
        "│       └── ⛔ SUPERSEDED — no live dependencies run through this node",
    ),
    # 3. N11 node header (operator attributes the jcode-home error to N11; the staged
    #    device is n11_jcode_sandbox_device.xml)
    (
        "├── N11 [RFC] Guest k3s (D1 resolved) + full dev toolset ⚙️",
        "├── N11 [RFC] Guest k3s (D1 resolved) + full dev toolset ⚙️ / jcode-home rework (SPR-1135)",
    ),
    # 4. Mermaid labels
    (
        '    N10["N10 [RES] JCode Home on<br/>Host SSD (14) ⛔ SUPERSEDED"]',
        '    N10["N10 [RES] JCode Home on<br/>Host SSD (14) ⛔ SUPERSEDED/REMOVED"]',
    ),
    (
        '    N11["N11 [RFC] Guest k3s (D1 resolved) +<br/>dev toolset ⚙️"]',
        '    N11["N11 [RFC] Guest k3s (D1 resolved) +<br/>dev toolset ⚙️ / jcode rework"]',
    ),
    # 5. Execution-order table rows
    (
        "| 10 | N10 — JCode Home State on Host SSD | RES | RES-14 (50034) | N1, N4 | ⛔ SUPERSEDED — operator reversed the host-SSD mapping idea; sandbox jcode installs as a normal self-contained install |",
        "| 10 | N10 — JCode Home State on Host SSD | RES | RES-14 (50034) | N1, N4 | ⛔ SUPERSEDED + REMOVED 2026-09-18 (SPR-1135) — operator reversed the host-SSD mapping idea; sandbox jcode is a normal self-contained install; the leftover wiring (domain export, guest ad-hoc mount, host binds, backing dirs) is being torn down under SPR-1135 |",
    ),
    (
        "| 11 | N11 — Guest k3s (D1 resolved) + full dev toolset | RFC | (D1/RFC-OW-421) | N1 | ⚙️ k3s installed live 2026-09-16 (v1.34.3+k3s3, Ready); toolset install pending |",
        "| 11 | N11 — Guest k3s (D1 resolved) + full dev toolset | RFC | (D1/RFC-OW-421) | N1 | ⚙️ k3s installed live 2026-09-16 (v1.34.3+k3s3, Ready); toolset install pending. jcode-home rework: the host-SSD home association (`n11_jcode_sandbox_device.xml`) is abandoned and removed under SPR-1135 |",
    ),
    # 6. N17 row: Part A + sidecar are now done (was ⬜ not started)
    (
        "| 17 | N17 — Provision FIDO2/USB signing into sandbox (future deployment) | ANA | — | N1, N12 | ⬜ |",
        "| 17 | N17 — Provision FIDO2/USB signing into sandbox | ANA | research 22 (50215) | N1, N12 | ⚙️ Part A DONE 2026-09-18 (YubiKey hostdev live + guest FIDO hidraw grant for seat-less SSH; CTAP2 getInfo verified in-guest); Admin-UI sign sidecar deployed into guest k3s via the Helm chart and `/api/v1/auth/nonce` returns 200; operator button-touch sign test pending |",
    ),
    # 7. New SPR node row (N19) after the N18 row
    (
        "| 18 | N18 — Server-side push-time enforcement + hooks deployment (runs on EVERY deploy) | ANA | Research 19 (50080); OW_tools/hooks/ | N14 | ⏩ |",
        "| 18 | N18 — Server-side push-time enforcement + hooks deployment (runs on EVERY deploy) | ANA | Research 19 (50080); OW_tools/hooks/ | N14 | ⏩ |\n"
        "| 19 | N19 — SPR-1135: guest jcode deployment rework (N10/N11 host-SSD home removal) | SPR | SPR-1135 (50221) | N1 | ⚙️ SPR scaffolded 2026-09-18 (anchor 50221, V-1 gap vs TP-188); teardown + TP-188 coverage in progress |",
    ),
    # 8. Mermaid node + edge for the SPR node
    (
        '    N13["N13 [GATE] Host cutover — stop<br/>host k8s/docker ⚙️"]',
        '    N13["N13 [GATE] Host cutover — stop<br/>host k8s/docker ⚙️"]\n'
        '    N19["N19 [SPR] SPR-1135 jcode<br/>deployment rework ⚙️"]',
    ),
    (
        "    N1 --> N11\n",
        "    N1 --> N11\n    N1 --> N19\n",
    ),
    # 9. The N10 superseded narrative
    (
        "is withdrawn; that doc is retained for history with `status: SUPERSEDED`. N8's\n"
        "gate no longer depends on N10. (Host-side fstab/libvirt bind teardown is an\n"
        "operator residual, out of agent scope.)",
        "is withdrawn; that doc is retained for history with `status: SUPERSEDED`. N8's\n"
        "gate no longer depends on N10.\n"
        "\n"
        "**N10/N11 wiring REMOVED under SPR-1135 (2026-09-18).** The withdrawal above was a\n"
        "documentation and environment change only: the deployed mechanism survived it. Verified\n"
        "live 2026-09-18 — the `sandbox` domain still exported `vm_sandbox_jcode` **and** an unused\n"
        "`vm_sessions`; the guest still held an **ad-hoc** read-write mount at\n"
        "`/mnt/vm-sandbox-jcode` (not in fstab) with stale 15–16 Sep content; the host still held the\n"
        "binds and backing directories (`/data/vm-sandbox/jcode-home`, `/data/jcode-vm-sessions`,\n"
        "`/var/lib/libvirt/virtiofs/jcode_state`). The operator reports two days of confusion from the\n"
        "resulting two-plausible-homes state. This is now governed: **SPR-1135 (udrs 50221)** removes\n"
        "the wiring and adds the TP-188 step that keeps it removed; **research 23 (udrs 50216)**\n"
        "records the requirement and the findings. The host's **own** `~/.jcode` bind on the SSD is\n"
        "correct, working, and explicitly unchanged (RD-19).",
    ),
]


def main() -> None:
    # --- DB: the SPR's own graph + its execution node -------------------------
    for args in (
        ["upsert_mikado_graph", "--graph-ci-id", str(SPR_ANCHOR), "--parent-ci-id",
         str(SPR_ANCHOR), "--title", "SPR-1135: Mikado Dependency Graph", "--strategy",
         "new_skeleton", "--total-nodes", "2", "--status", "ACTIVE"],
        ["upsert_mikado_node", "--graph-ci-id", str(SPR_ANCHOR), "--node-id", "S1",
         "--node-type", "SPR", "--description", S1_DESC, "--status", "IN_PROGRESS",
         "--artifact-ci-id", str(SPR_ANCHOR), "--execution-order", "1"],
        ["upsert_mikado_node", "--graph-ci-id", str(SPR_ANCHOR), "--node-id", "S2",
         "--node-type", "SPR", "--description", S2_DESC, "--status", "NOT_STARTED",
         "--artifact-ci-id", str(SPR_ANCHOR), "--depends-on", "S1", "--execution-order", "2"],
        # --- DB: the SPR as a node of the DAR graph ---------------------------
        ["upsert_mikado_node", "--graph-ci-id", str(DAR_GRAPH_CI), "--node-id", "N19",
         "--node-type", "SPR", "--description",
         "SPR-1135 — guest jcode deployment rework: remove the withdrawn N10/N11 host-SSD home "
         "association (domain device, guest ad-hoc mount, host binds, backing dirs) and add the "
         "TP-188 step that keeps it removed.",
         "--status", "IN_PROGRESS", "--artifact-ci-id", str(SPR_ANCHOR),
         "--depends-on", "N1", "--execution-order", "19"],
    ):
        r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                           capture_output=True, text=True)
        ok = '"status": "success"' in r.stdout
        print(f"{args[0]} {args[3] if len(args) > 3 else ''}: {'OK' if ok else 'FAIL ' + (r.stdout + r.stderr)[-200:]}")

    # --- file: mark N10/N11 and add the SPR node -----------------------------
    text = GRAPH.read_text()
    applied, skipped = 0, 0
    for old, new in EDITS:
        if new.split("\n")[0] in text and old not in text:
            skipped += 1
            continue
        if old in text:
            text = text.replace(old, new, 1)
            applied += 1
        else:
            print(f"  MISS (not found): {old[:70]!r}")
    GRAPH.write_text(text)
    print(f"graph edits: applied={applied} skipped={skipped} total={len(EDITS)}")


if __name__ == "__main__":
    main()
