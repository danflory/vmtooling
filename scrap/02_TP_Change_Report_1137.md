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
severity: 3
type: SPR.TP_CHANGE
version: "2026_09_18_18_36"
---

# Migration lint gate and runtime sidecar use different squawk binaries — TP Change Report

> [!WARNING]
> **AGENT INSTRUCTION: This document is NOT a Test Procedure (TP).**
> It is a *Change Report* documenting how a separate regression TP was modified.
> Every code fix requires coverage in an executable TP (e.g., `docs/praca/TP/TP-NNN.md`).
> Do not attempt to write executable bash commands directly into this report.

## Affected TP

- **TP Reference**: **none** — no executable TP covers either artifact.
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

| # | Step | Expected Result | New/Modified |
|:--|:-----|:----------------|:-------------|
| 1 | On a clean clone, run the A6 gate against a compliant staged migration with no manual installs. | PASS, and `gate_sql_lint.py` reports the squawk path it used. FAILS pre-fix (no squawk in a fresh venv; hand-placed binary required). | New |
| 2 | Compare the gate's squawk version to the version inside the migration-sidecar image (`k3s kubectl exec … -c migration-sidecar -- squawk --version`). | Identical strings. FAILS pre-fix (2.65.0 vs 2.59.0). | New |
| 3 | Lint one deliberately non-compliant migration at both stages (gate and sidecar entrypoint) and compare the verdicts. | Same verdict, same rule. FAILS pre-fix whenever a rule differs between the two versions. | New |
| 4 | Assert the vendored `firecontrol/docker/squawk-linux-x86_64` SHA-256 equals the pinned value and that the path is a registered CI. | Match, and registered. | New |

## Verification

Running these steps in the pre-fix state must **FAIL** (step 1 has no binary in a fresh venv;
step 2 reports 2.65.0 vs 2.59.0; step 3 can diverge) and in the post-fix state must **PASS**.
Steps 1 and 2 are the ones that would have caught this defect at the moment RFC-OW-271 landed.
