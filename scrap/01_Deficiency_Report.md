---
id: 50222
title: Guest JCode Deployment Rework Remove Host SSD Home Association — Deficiency Report
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
- path: docs/praca/SPR/SPR-1135_Guest_JCode_Deployment_Rework_Remove_Host_SSD_Home_Association/01_Deficiency_Report.md
  access: ro
severity: 3
type: SPR.DEFICIENCY
version: "2026_09_18_15_59"
---

# Guest JCode Deployment Rework Remove Host SSD Home Association — Deficiency Report

## Root Design Failure

The N10/RES-14 design (UDRS 50034) placed the **guest's** jcode home on the **host's** SSD
and exposed it into the guest as a writable virtiofs share. That inverts the DAR's own
boundary doctrine: RD-6 keeps non-personal clones host-resident and **read-only**, RD-7 moves
governed projects **into** the VM. A live writable share satisfies neither rule and creates a
third state — a directory that is simultaneously guest-visible and host-owned — for which no
rule, no owner and no authoritative location was ever defined. The failure was not the
storage medium; it was inventing an unowned third location.

The second, compounding design failure is in the **revert**: withdrawal was recorded in
documentation and executed as an environment change (unset `JCODE_HOME`, comment an fstab
line) while the topology that implemented the idea (libvirt device, ad-hoc mount, host binds,
backing directories) was left running. No artifact in the DAR defined what "withdrawn" means
for a mechanism that is already deployed.

## What the Original Design Got Wrong

| Decision | What it got wrong |
|:---------|:------------------|
| Put the guest's jcode home on the host SSD for durability | Durability was bought by making the guest's state depend on the host. It created a second jcode home that was live and writable, so both homes looked real and neither was authoritative. |
| Expose it as a read-write virtiofs share | Read-write exposure means the guest and host can diverge silently; nothing arbitrates. The same mechanism is fine for `vm_backups` (write-only destination) and for `host_dev_env` (read-only reference) precisely because those directions are unambiguous. |
| Withdraw by documentation plus environment edits | The papers said "abandoned" while the domain, the guest and the host still implemented it. A withdrawn mechanism left reachable is worse than either keeping it or removing it: the record and reality point opposite ways. |
| Verify by "is jcode state present in the guest" | The criterion tests for the presence of a named object, not the absence of a mechanism, so any residue satisfies it. |

## Impact Assessment

- **Operator time**: two days of confusion, by the operator's own account, in distinguishing
  which jcode home was real.
- **Same-class defect found the same day**: the guest also ran a vestigial native Postgres on
  5432 holding no application data while the in-cluster pod held the real 508 MB. It caused a
  wrong-endpoint DSN and a silent 15-second hang during sidecar deployment, and it survived
  the DAR's own SC-10 check, which asked whether the native `firecontrol` **database** was
  deleted — it was — rather than whether the **instance** was. Recorded in
  `02_Research/22_In-Guest_FIDO2_Signing_Enablement.md` (UDRS 50215).
- **Verification blind spot**: TP-188 is the DAR closure gate and cannot currently see either
  residue, so both could have been present at closure while every step passed.
- **Future agents**: any reader of the guest topology sees a mounted jcode share named
  `vm-sandbox-jcode` with real-looking content, and has no in-band signal that it is
  abandoned. This is exactly how the error would propagate into new work.

## Corrective Design

**Rule: a withdrawal is a topology change, not a documentation change.** When a mechanism is
withdrawn, the same change set must (a) remove every deployed element of it — device, mount,
bind, backing store — and (b) update the verification artifact so the *absence* is tested.
Documentation-only withdrawal is not withdrawal.

**Rule: no third location.** Guest state lives in the guest; host state lives on the host;
the only cross-boundary shares are directionally unambiguous (`host_dev_env` read-only,
`vm_backups` write-only). Any proposal for a writable share of live application state must
name the authority for that state or it is rejected.

**Rule: verify the absence of the mechanism, not the absence of the name.** Where a check
exists to prove something was removed, it must assert on the mechanism (no jcode-targeted
filesystem device; no jcode virtiofs mount; no backing directory) rather than on the named
object that used to sit on top of it.

## Convergence Pattern Check

Not applicable: the fix contains no iteration, retry or batch logic. It is a finite teardown
plus one added test step.
