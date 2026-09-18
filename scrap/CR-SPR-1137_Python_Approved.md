---
id:
title: SPR-1137 Python Implementation Review (Approved)
status: ACTIVE
author: agent
ci_impacted:
  - 42098
  - 50245
  - 50251
created: 2026-09-18
domain: GOVERNANCE
findings_count: 0
mechanical_pass: true
parent: 50249
parent_ci: 50249
phase: RELEASED
review_scope: python
review_verdict: APPROVED
type: CR
version: "2026_09_18_20_16"
---

# CR: SPR-1137 Python Implementation Review (Approved)

Formal `/checkImplementation` peer review of the SPR-1137 change-set: the migration lint gate
now resolves its squawk engine from the repository-vendored artifact (hash-pinned) instead of
the Python venv, resolves sqlfluff explicitly rather than by PATH, and fails with an actionable
engine error instead of a traceback.

Change-set under review (excluding PRACA docs):

| file | kind |
|:-----|:-----|
| `firecontrol/gates/gate_sql_lint.py` | Python (in scope for this CR) |
| `setup_venv.sh` | shell (syntax-checked; not Python scope) |
| `firecontrol/docker/squawk-linux-x86_64` | binary build input (registered as a CI) |

## Review Verdict

**APPROVED** — 0 blocking findings.

## Mechanical Checks

| Check | Status | Note |
|:------|:-------|:-----|
| Ruff lint | PASS | `ruff check firecontrol/gates/gate_sql_lint.py` → "All checks passed!" |
| Ruff format | PASS | `ruff format --check` → "1 file already formatted" (an earlier implicit-concatenation block was reformatted in the same commit) |
| Strict pyright (depth INF) | PASS | `0 errors, 0 warnings, 0 informations` |
| Third-party stub enforcement | N/A | No new external imports; the change adds only stdlib `hashlib` |
| Shell syntax (out of Python scope) | PASS | `bash -n setup_venv.sh` → OK |

## Semantic & Architectural Checks

| Check | Status | Note |
|:------|:-------|:-----|
| Scope containment | PASS | Every change is inside SPR-1137's declared scope (gate, vendored artifact, `setup_venv.sh`, pins, verification). No collateral edits, no refactoring beyond the fix. |
| Fail-closed preserved | PASS | `_assert_engines()` runs at the top of `main()`, before any file is linted, and exits 1 on a missing or drifted engine. The gate was fail-closed before (a `FileNotFoundError` also exited non-zero); it remains so, with an actionable message. |
| Real invocation path exercised | PASS | The A6 gate ran on this very changeset (13 gates checked on each commit) and the gate returns exit 0 on a real migration (`R__decisions__ow_manage_gap.sql`). |
| Drift guard is mechanical | PASS | The pinned SHA-256 is asserted on every run, so a swapped binary fails the gate rather than silently changing the rule set — the property that was missing (RFC-OW-271 verified only at image build). |
| Provenance distinction is correct | PASS | squawk (vendored, not pip-installable) resolves from the repository; sqlfluff (pip-installable) resolves from the venv. The venv path is retained for sqlfluff only, which is why a naive "no venv references" check would be wrong. |
| No second source introduced | PASS | `setup_venv.sh` *verifies* the vendored binary rather than copying it, so the fix does not recreate the two-sources defect it removes. |

## Non-blocking advisories (recorded, not blocking)

1. **Hash cost**: `_assert_engines()` hashes the 21 MB binary on every gate run. Measured cost is
   tens of milliseconds per run; acceptable for a commit-time gate, but if the gate is ever put
   on a hot path the digest should be cached by mtime+size.
2. **Repo-root assumption**: `_REPO_ROOT = Path(__file__).resolve().parents[2]` assumes the gate
   lives at `<root>/firecontrol/gates/`. If the file is ever relocated the assertion fails loudly
   and names the expected path, so the failure mode is self-diagnosing rather than silent.

## Evidence

- `TP-206` post-fix execution: **PASS 6/6**, recorded as a `post_fix` test execution.
- Pre-fix execution (recorded before the fix): **FAIL 5/6**.
- Fix commit: `14ee0b92a` (gate fixups for A9/A16 in the same commit).
