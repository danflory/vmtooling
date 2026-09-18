---
id: 50223
title: Guest JCode Deployment Rework Remove Host SSD Home Association — TP Change Report
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
- path: docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/02_TP_Change_Report.md
  access: ro
severity: 3
type: SPR.TP_CHANGE
version: "2026_09_18_16_00"
---

# Guest JCode Deployment Rework Remove Host SSD Home Association — TP Change Report

> [!WARNING]
> **AGENT INSTRUCTION: This document is NOT a Test Procedure (TP).**
> It is a *Change Report* documenting how a separate regression TP was modified.
> Every code fix requires coverage in an executable TP (e.g., `docs/praca/TP/TP-NNN.md`).
> Do not attempt to write executable bash commands directly into this report.

## Affected TP

- **TP Reference**: `TP-188` — DAR-OW-158 Regression (UDRS 49841), the DAR closure gate.
- **Parent Artifact**: `DAR-OW-158` Disposable VM Sandbox Isolation (UDRS 49825).

## Gap Classification (V-1 through V-6)

| Violation | Applies | Evidence |
|:----------|:--------|:---------|
| V-1: Uncovered AC | **Yes** | No step in TP-188 covers the requirement "the guest's jcode deployment is a standard self-contained install with no host association". Step 2 (SC-2) requires only that "jcode state [is] present" in the guest, which a host-backed share satisfies just as well as a guest-local home. The withdrawal of N10/RES-14 therefore has no covering step, so the residue survived the revert. |
| V-2: Suppression | No | No exception or warning path is involved; nothing suppresses a failure signal here. |
| V-3: Prerequisite not enforced | No | The affected step has no prerequisite that went unenforced. |
| V-4: Temporal ordering | No | The TP did not run before its implementation; it simply never covered this property. |
| V-5: Degenerate pass criterion | **Yes** | Step 2's pass criterion ("all of the above present and writable in the guest") cannot distinguish the target state (guest-local `~/.jcode`) from the background condition (a mounted host-backed jcode share). Both states pass, so the criterion cannot fail on the defect. The same weakness let the vestigial native Postgres survive SC-10, which asked whether the native `firecontrol` **database** was deleted (it was) rather than whether the native **instance** was (it was not). |
| V-6: AC count mismatch | No | The step/AC counts are consistent; the missing coverage is substantive, not arithmetic. |

**Primary category**: V-1 (with V-5 as the contributing mechanism).

## Steps Added / Modified

| # | Step | Expected Result | New/Modified |
|:--|:-----|:----------------|:-------------|
| 2a | In the guest: assert the jcode home is guest-local — `readlink -f ~/.jcode` resolves to the guest's own filesystem, `findmnt -no SOURCE ~/.jcode` is not a virtiofs share, and `mount \| grep virtiofs` lists only `host_dev_env` (ro) and `vm_backups` (rw). | PASS only when no jcode-targeted share is mounted and the home is local. FAILS against the pre-fix topology (the ad-hoc `vm_sandbox_jcode` mount is present). | New |
| 2b | On the host: assert the domain exports no jcode/session device — `virsh dumpxml sandbox` contains no `vm_sandbox_jcode` and no unused `vm_sessions` filesystem target — and that the corresponding host binds, `/etc/fstab` lines and backing directories are absent, while the host's own `~/.jcode` bind is untouched. | PASS only when the withdrawn mechanism is fully torn down. | New |

Both steps are added to TP-188's SC-2 (guest Tier 1 content) and SC-7 (virtiofs boundary)
neighbourhood, so the DAR closure gate covers the property that the withdrawal actually
happened.

## Verification

Running the updated TP in the pre-fix state must **FAIL** (step 2a fails on the ad-hoc
`vm_sandbox_jcode` mount; step 2b fails on the domain export and the host backing) and in the
post-fix state must **PASS**. This pre-fix FAIL is the evidence that the new coverage is real
rather than declarative, and it is what the original TP lacked.
