---
id: 50247
title: Migration lint gate and runtime sidecar use different squawk binaries — TP Change Report
status: ACTIVE
author: operator
authorized_by: 40175
change_class: 3
ci_impacted:
  - 40175
  - 39275
created: 2026-09-18
domain: INFRASTRUCTURE
parent: 50249
parent_ci: 50249
phase: DEVELOPMENT
scope:
- path: docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries/02_TP_Change_Report.md
  access: ro
severity: 1
type: SPR.TP_CHANGE
version: "2026_09_18_19_47"
---

# Migration lint gate and runtime sidecar use different squawk binaries — TP Change Report

> [!WARNING]
> **AGENT INSTRUCTION: This document is NOT a Test Procedure (TP).**
> It is a *Change Report* documenting how a separate regression TP was modified.
> Every code fix requires coverage in an executable TP (e.g., `docs/praca/TP/TP-NNN.md`).
> Do not attempt to write executable bash commands directly into this report.

## Affected TP

- **TP Reference**: **none at creation** (`tp_gap_category: no_tp`). No executable TP covers
  either artifact; a TP must be scaffolded to carry the steps below before the fix lands
  (doSPR2 Phase 1.5 requires the TP to exist and to FAIL pre-fix).
- **Parent Artifact**: `RFC-OW-271` Squawk Sidecar Lint Gate (UDRS 40175); the gate it must
  agree with came from `RFC-OW-256` (UDRS 39275).

## Gap Classification (V-1 through V-6)

| Violation | Applies | Evidence |
|:----------|:--------|:---------|
| V-1: Uncovered AC | n/a (no TP) | The proposition "the gate and the runtime lint with one squawk version" has no covering step anywhere. With no TP to hold it, this is recorded as the category below rather than as an uncovered AC in an existing TP. |
| V-2: Suppression | No | Nothing suppresses a failure; the mismatch is simply unobserved. |
| V-3: Prerequisite not enforced | No | No TP prerequisite is involved. |
| V-4: Temporal ordering | No | No TP ran out of order; none exists. |
| V-5: Degenerate pass criterion | **Yes (mechanism)** | The gate's observable "lint passed" cannot distinguish *which engine* produced the verdict, so it passes for both the correct and the drifted binary. The same shape of criterion let the vestigial native Postgres satisfy SC-10 in TP-188 (see DAR-OW-158 `04_Implementation/04`). |
| V-6: AC count mismatch | No | Not an arithmetic gap; the coverage is absent entirely. |

**Primary category**: `no_tp` — verified mechanically: no TP document references RFC-OW-256 or
RFC-OW-271, and `query_test_execs` returns zero rows for either pattern. V-5 is recorded as the
contributing mechanism.

## Steps Added / Modified

One step per VCL, mapped to the break it detects. All are binary assertions.

| # | Step | Covers | Expected Result | New/Modified |
|:--|:-----|:-------|:----------------|:-------------|
| 1 | From a clean checkout with no manual installs, run the A6 gate against a compliant staged migration. | V-2 (B-2) | PASS, and the gate reports the squawk path it used. **FAILS pre-fix**: a fresh venv has no squawk, so the gate raises `FileNotFoundError` and blocks. | New |
| 2 | Assert the gate's resolved squawk path is the repository-vendored artifact (no `sys.executable`-relative resolution anywhere in the gate). | V-1 (B-1) | Path equals `firecontrol/docker/squawk-linux-x86_64`. **FAILS pre-fix** (resolves to `.venv/bin/squawk`). | New |
| 3 | Compare the gate's squawk version to the version inside the running migration-sidecar image. | V-3 (B-1) | Identical strings. **FAILS pre-fix** (2.65.0 vs 2.59.0). | New |
| 4 | Assert the hand-placed `.venv/bin/squawk` is absent after provisioning from the repository, and that `setup_venv.sh` + `requirements*.txt` account for both gate engines. | V-1, V-2 (B-2) | No hand-placed binary; squawk and sqlfluff both provisioned and pinned. **FAILS pre-fix**. | New |
| 5 | Lint one deliberately non-compliant migration at both stages (A6 gate and sidecar entrypoint) and compare verdicts. | V-4 (B-1) | Same verdict from both stages. **FAILS pre-fix** whenever a rule differs between the two versions. | New |
| 6 | Assert the vendored binary is a registered CI and that its SHA-256 matches the pinned value. | V-5 (B-3) | Registered, hash matches. **FAILS pre-fix** (not registered). | New |

## Verification

Running these steps in the pre-fix state must **FAIL** — measured 2026-09-18: step 1 fails in 3
of the 6 guest clones today (Overwatch_1 has no venv; Overwatch_3 and Overwatch_5 have venvs
without squawk), step 2 resolves to the venv copy, step 3 reports 2.65.0 vs 2.59.0, and step 6
finds no registration. In the post-fix state all six must PASS. Steps 1 and 3 are the ones that
would have caught this defect the moment RFC-OW-271 landed.
