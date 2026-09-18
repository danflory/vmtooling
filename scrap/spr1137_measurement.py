#!/usr/bin/env python3
"""SPR-1137: record the measured impact (does the bug actually produce errors today?).

Measurement 2026-09-18: both binaries run over the full migration corpus
(firecontrol/sql/[VR]*.sql, 251 files, excluding V1__Baseline.sql) flag the IDENTICAL 42
files — zero verdict divergence. Both stages also effectively run squawk's default rule set:
the repository config `firecontrol/.squawk.toml` declares `excluded_rules = []` (identical to
the default), and neither stage runs with that file in its search path (the A6 hook runs from
the repo root; the sidecar's CWD is `/` while the config sits at `/app/.squawk.toml`).

So the version drift is currently LATENT. The one present-tense error is the fresh-clone case:
nothing installs squawk, so the gate raises FileNotFoundError and blocks every migration
commit. Recording this keeps the SPR's impact claim measured rather than assumed.
"""
from __future__ import annotations

import pathlib

FOLDER = pathlib.Path(
    "docs/praca/SPR/SPR-1137_Migration_lint_gate_and_runtime_sidecar_use_different_squawk_binaries"
)

MEASUREMENT = """
## Measured impact (2026-09-18) — does it produce errors today?

Measured rather than assumed, because the answer is narrower than the risk:

| question | measurement |
|:---------|:------------|
| Do the two versions disagree on the current corpus? | **No.** Both binaries run over all 251 files of `firecontrol/sql/[VR]*.sql` (excluding `V1__Baseline.sql`) flag the **identical 42 files** — zero divergence. |
| Do the two stages even read the same rule configuration? | **Effectively yes, by accident.** `firecontrol/.squawk.toml` declares `excluded_rules = []`, which is squawk's default, so it is inert. And neither stage has it in its search path anyway: the A6 hook runs from the repo root (no `.squawk.toml` there or above), and the sidecar's CWD is `/` while the config is at `/app/.squawk.toml`. Both therefore run default rules. |
| Is there any present-tense error? | **Yes, one.** On a fresh clone or rebuilt venv nothing installs squawk (`setup_venv.sh` installs `sqlfluff` only, and `requirements*.txt` pin neither), so `gate_sql_lint.py` raises `FileNotFoundError`, exits non-zero, and A6 blocks **every** commit touching a migration — with a traceback rather than a message. Fail-closed, so governance holds. |

**Conclusion**: today the defect is *latent*, not active. The gate's verdict happens to agree
with the runtime's, because both use default rules and the two versions agree on this corpus.
What is real today is the reproducibility failure (a fresh clone cannot run the gate at all)
and the drift risk: the moment either version's rule set changes upstream, the gate's verdict
stops being evidence about the cluster, and nothing would report it. That is why the fix is
still worth making — but the SPR should not claim present-tense wrong verdicts, and it no
longer does.
"""


def main() -> int:
    anchor = FOLDER / "SPR-1137.md"
    t = anchor.read_text()
    if "Measured impact (2026-09-18)" in t:
        print("already recorded")
        return 0
    marker = "## Root Cause"
    t = t.replace(marker, MEASUREMENT.strip() + "\n\n" + marker, 1)

    # soften the present-tense claim in the problem statement
    t = t.replace(
        "So a migration can **pass the commit gate and fail at startup lint, or the\nreverse** — the two stages are not enforcing the same rule set, and the mismatch is silent.",
        "So a migration **can** pass the commit gate and fail at startup lint, or the reverse: the two\n"
        "stages are not guaranteed to enforce the same rule set, and a mismatch would be silent.\n"
        "(Measured 2026-09-18: on the current corpus they do not yet disagree — see *Measured impact*\n"
        "below — so the defect is latent rather than active.)",
    )
    anchor.write_text(t)
    print("anchor updated with the measurement")

    defi = FOLDER / "01_Deficiency_Report.md"
    d = defi.read_text()
    line = ("- **Verification integrity**: the commit gate is a governance gate (A6). If it lints with a\n"
            "  different engine than the runtime, then \"lint passed\" is not evidence about the cluster, and\n"
            "  a migration can be admitted that the runtime lint will reject — or blocked for a rule the\n"
            "  runtime does not enforce. The gate's verdict is not reproducible from the repository.")
    new = ("- **Verification integrity**: the commit gate is a governance gate (A6). If it lints with a\n"
           "  different engine than the runtime, then \"lint passed\" is not evidence about the cluster, and\n"
           "  a migration can be admitted that the runtime lint will reject — or blocked for a rule the\n"
           "  runtime does not enforce. The gate's verdict is not reproducible from the repository.\n"
           "  *Measured 2026-09-18*: the two versions currently agree on all 251 corpus files (identical\n"
           "  42 flagged), so this is a latent risk, not an active wrong verdict. The active error is the\n"
           "  fresh-clone `FileNotFoundError` described below.")
    if line in d:
        d = d.replace(line, new, 1)
        defi.write_text(d)
        print("deficiency report updated")
    else:
        print("deficiency line not found (already updated?)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
