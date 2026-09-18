---
id: 50246
title: Migration lint gate and runtime sidecar use different squawk binaries — Deficiency Report
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
- path: docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries/01_Deficiency_Report.md
  access: ro
severity: 1
type: SPR.DEFICIENCY
version: "2026_09_18_19_45"
---

# Migration lint gate and runtime sidecar use different squawk binaries — Deficiency Report

## Root Design Failure

Two artifacts needed "a squawk", and each answered the question **locally and independently**.
RFC-OW-256's commit-time gate took the binary from the environment in which a commit hook
runs — the Python venv — because that is the path of least resistance there. RFC-OW-271's
container image could not use a venv and did the disciplined thing: vendor the binary in the
repository and pin its SHA-256. Both are locally reasonable; together they produce two
different linters, two versions, and no contract between them.

The root failure is a category error about **what a gate depends on**. A gate's verdict is a
function of its inputs: the file, the rule configuration, and the rule *engine*. Here the
engine was treated as environment plumbing ("the linter on PATH") rather than as a governed
artifact, so the verdict is not reproducible from the repository, and the two stages that
must agree were never compared.

## Break-by-break analysis

The anchor defects three breaks (B-1..B-3). Each is traced to the design decisions that
produced it.

| Break | Design decisions that produced it | Why it was not caught |
|:------|:----------------------------------|:----------------------|
| **B-1** rule divergence | The gate resolves the engine from `Path(sys.executable).parent` (venv-local); the image vendors its own copy; no artifact asserted they must match. | No TP and no check compared the two stages. The versions drifted upstream (2.59.0 → 2.65.0) without any repository change, so nothing was reviewable. |
| **B-2** not reproducible | `setup_venv.sh` installs `sqlfluff` but not `squawk`; neither is pinned in `requirements*.txt`; the gate's binary is hand-placed. | The gate fails closed, so the missing binary looks like a strict gate rather than a broken environment. Nothing asserted the gate can run from a clean checkout. |
| **B-3** ungoverned artifact | The binary was vendored for the *image* (RFC-OW-271) and registered its config (`.squawk.toml`, UDRS 42031) but not itself. | Registration focused on the text artifacts a gate consumes; a binary build input was treated as an asset rather than a CI. |

## What the Original Design Got Wrong

| Decision | What it got wrong |
|:---------|:------------------|
| Resolve the gate's squawk from `Path(sys.executable).parent` | Binds the gate's rule set to whatever is installed in a local venv. It is invisible to version control, unpinned, and drifts without any artifact changing. |
| Install `sqlfluff` in `setup_venv.sh` but not `squawk` | Half the tool pair is reproducible and half is tribal knowledge. The gate's two engines come from different trust models (pip-managed vs hand-placed). |
| Let RFC-OW-256 and RFC-OW-271 each choose a squawk independently | No shared artifact contract, so no one owned "these must be the same binary". The version delta (2.59.0 vs 2.65.0) was never a decision — it is an accident. |
| Verify only at the image boundary (SHA-256 at build) | Verifies the image against the repository, but never verifies the *gate* against the repository, which is the stage that decides whether a migration is committed at all. |
| Leave the vendored binary unregistered while registering its `.squawk.toml` | The rule configuration is governed; the rule engine is not. The more consequential artifact is the ungoverned one. |

## Impact Assessment

- **Verification integrity (B-1)**: the commit gate is a governance gate (A6). If it lints with
  a different engine than the runtime, then "lint passed" is not evidence about the cluster, and
  a migration can be admitted that the runtime lint will reject — or blocked for a rule the
  runtime does not enforce. The gate's verdict is not reproducible from the repository.
  *Measured 2026-09-18*: the two versions currently agree on all 251 corpus files (identical 42
  flagged), so this is a latent risk, not an active wrong verdict.
- **Work stoppage (B-2, active)**: on a fresh clone or rebuilt venv the gate has no binary. It
  raises `FileNotFoundError`, exits non-zero, and the dispatcher counts it as BLOCKED — so
  **every commit touching a migration fails until squawk is hand-installed.** Fail-closed, which
  is the correct direction for governance, but it is a hard stop with no actionable message and
  no repository path to recovery.
- **Governance gap (B-3)**: the binary the runtime trusts is not a registered CI, so it is
  invisible to the identity and write-path machinery that governs its own `.squawk.toml`.
- **Same class as two defects already recorded today**: a mechanism (here, the gate's engine)
  exists in two places with no single source of truth. That is the pattern of the withdrawn
  N10/N11 jcode share (two plausible homes) and the vestigial native Postgres (two plausible
  databases) — see `04_Implementation/03` and `04_Implementation/04` in DAR-OW-158.

## Corrective Design

**Rule: a gate's engine is a governed artifact.** Anything whose version changes a gate's
verdict must be vendored, hash-pinned, registered, and asserted against the environment where
the same check runs again. "Installed on the machine" is not a source of truth.

**Rule: one artifact, many consumers.** The commit gate, the image build, and any future
consumer reference the same vendored binary. Copies may exist at runtime (a container cannot
reach a venv); *sources and versions* may not.

**Rule: assert the agreement, do not assume it.** The stage that can silently disagree with the
runtime is exactly the stage that needs the assertion. A one-line version equality check
between the gate and the image is what turns this class of drift into a failure.

**Rule: a gate must be runnable from a clean checkout.** If provisioning the gate's own
dependencies is not in the repository's setup path, the gate is not reproducible and its
failures are indistinguishable from environment breakage.

## Convergence Pattern Check

Not applicable: the fix contains no iteration, retry or batch logic. It is a path change, an
install step, and one assertion.
