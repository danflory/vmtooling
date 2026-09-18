---
id: 50224
title: Guest JCode Deployment Rework Remove Host SSD Home Association
status: ACTIVE
author: operator
authorized_by: 49825
change_class: 3
ci_impacted:
  - 49825
created: 2026-09-18
domain: INFRASTRUCTURE
parent: 50221
parent_ci: 50221
phase: DEVELOPMENT
scope:
- path: docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/README.md
  access: ro
severity: 3
type: SPR.README
version: "2026_09_18_16_00"
---

# Guest JCode Deployment Rework Remove Host SSD Home Association

## Document Index

| Document | Type | Purpose |
|:---------|:-----|:--------|
| `SPR-1135.md` | Anchor | Problem statement, root cause, fix, scope, VCL |
| `01_Deficiency_Report.md` | Deficiency Report | Root design failure analysis and corrective design rules |
| `02_TP_Change_Report.md` | TP Change Report | TP-188 gap classification (V-1, V-5) and the steps added |

## What this SPR governs

The guest's jcode deployment must be a **standard, self-contained install** on the guest's
own `~/.jcode`, with no host association. The withdrawn N10/RES-14 host-SSD design left its
wiring in place after the revert — a libvirt filesystem device (`vm_sandbox_jcode`), an
unused `vm_sessions` device, an ad-hoc read-write mount in the guest, and host binds plus
backing directories. This SPR governs the teardown of that wiring, the verification step that
keeps it torn down, and the graph marking that makes the record match the topology.

## Status

- **Created**: 2026-09-18
- **Status**: ACTIVE (phase DEVELOPMENT)
- **Change class**: 3
- **Severity**: 3
- **TP gap**: V-1 (primary), V-5 (contributing) against `TP-188` (UDRS 49841)

## Related CIs

| CI | UDRS | Relation |
|:---|:-----|:---------|
| `DAR-OW-158` Disposable VM Sandbox Isolation | 49825 | parent / authorizing artifact |
| `TP-188` DAR-OW-158 Regression | 49841 | the closure gate this SPR changes |
| `02_Research/14_JCode_Home_On_Host_SSD.md` | 50034 | withdrawn design that introduced the defect |
| `02_Research/21_JCode_Config_State_Sync.md` | 50052 | superseding snapshot-sync mechanism |
| `02_Research/22_In-Guest_FIDO2_Signing_Enablement.md` | 50215 | same-class twin defect (native Postgres vestige) |
| `02_Research/23_Guest_JCode_Deployment_Standard_Install_No_Host_Association.md` | 50216 | research record for this rework |
| `03_Synthesis/01_Mikado_Graph.md` | 49871 | carries the N10/N11 markings |
