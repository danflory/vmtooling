---
id: 50248
title: Migration lint gate and runtime sidecar use different squawk binaries
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
- path: docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries/README.md
  access: ro
severity: 1
type: SPR.README
version: "2026_09_18_18_37"
---

# Migration lint gate and runtime sidecar use different squawk binaries

## Document Index

| Document | Type | Purpose |
|:---------|:-----|:--------|
| `SPR-1137.md` | Anchor | Problem statement, root cause, fix, scope, VCL |
| `01_Deficiency_Report.md` | Deficiency Report | Root design failure and corrective design rules |
| `02_TP_Change_Report.md` | TP Change Report | `no_tp` classification and the steps to add |

## What this SPR governs

Squawk is part of the DB migration pipeline at two stages — the commit-time A6 lint gate and
the migration sidecar's runtime lint. They currently run **different binaries** (2.65.0 from a
hand-placed venv copy vs 2.59.0 from the RFC-OW-271 vendored artifact baked into the image),
so the gate's verdict is not evidence about the cluster and version drift is silent.

This SPR governs: making the vendored `firecontrol/docker/squawk-linux-x86_64` the single
source of truth, pointing the gate at it, making the gate's binary reproducible from the
repository, asserting gate/runtime version equality, and registering the vendored binary as a
CI. It is recorded as an **implementation point in DAR-OW-158** because the guest's DB
deployment is what consumes this migration path.

## Status

- **Created**: 2026-09-18
- **Status**: ACTIVE (phase DEVELOPMENT)
- **Change class**: 3
- **Severity**: 3
- **TP gap**: `no_tp` (no executable TP for either RFC; V-5 as the contributing mechanism)

## Related CIs

| CI | UDRS | Relation |
|:---|:-----|:---------|
| `RFC-OW-271` Squawk Sidecar Lint Gate | 40175 | parent (vendors the binary; defines the runtime lint) |
| `RFC-OW-256` OPF-014 Flyway Lint Gate Porting | 39275 | introduced the commit-time gate and its venv-resolved binary |
| `firecontrol/gates/gate_sql_lint.py` | 42098 | the gate that resolves squawk from the venv |
| `firecontrol/.squawk.toml` | 42031 | rule configuration (already governed) |
| `DAR-OW-128` R04 Squawk Sidecar Installation | 40080 | original sidecar installation research |
| `DAR-OW-158` Disposable VM Sandbox Isolation | 49825 | implementation point (guest DB migration path) |
