#!/usr/bin/env python3
"""Corrections forced by the swarm's adversarial verification.

1. praca.success_criteria SC 3 for CI 50221 (SPR-1135) is falsely checked=true: gorilla
   verified V-3 is still OPEN (/data/jcode-vm-sessions and the three virtiofs dirs remain).
2. TP-206 (CI 50250) steps 1, 2, 4 and 5 as written were falsified by jaguar:
   - step 1: the V999 fixture trips the N10 pairing check so the gate exits 1, and the output
     never names the squawk binary -> use a repeatable (R__) fixture and an honest criterion.
   - step 2: "no Path(sys.executable).parent-relative resolution remains" is literally false;
     the venv path legitimately stays for sqlfluff. Criterion narrowed to squawk.
   - step 4: the pin lives in setup_venv.sh, not requirements*.txt.
   - step 5: `squawk -` does not work in the image ("Failed to find files for provided
     patterns"), making the step a vacuous both-exit-1 pass. Write the file inside the
     container instead.
3. DAR-OW-158 graph node N21 (SPR-1137) -> CLOSED.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"
TP206 = REPO / "docs/praca/TP/TP-206.md"
GRAPH = REPO / ("docs/praca/DAR/DAR-OW-158_Disposable_VM_Sandbox_Isolation/03_Synthesis/"
                "01_Mikado_Graph.md")


def db(*args: str) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True, cwd=REPO)
    ok = '"status": "success"' in (r.stdout + r.stderr)
    print(f"  {'OK' if ok else 'FAIL'}: {' '.join(args[:2])}")
    if not ok:
        print("   ", (r.stdout + r.stderr)[-200:])
    return ok


def patch(path: pathlib.Path, pairs: list[tuple[str, str]]) -> None:
    t = path.read_text()
    for old, new in pairs:
        if new in t:
            print(f"  {path.name}: already correct")
        elif old in t:
            t = t.replace(old, new, 1)
            print(f"  {path.name}: patched")
        else:
            print(f"  {path.name}: MISS {old[:60]!r}")
    path.write_text(t)


def main() -> int:
    print("=== 1. SC 3 honesty correction ===")
    db("upsert_sc", "--ci-id", "50221", "--sc-num", "3", "--checked", "false",
       "--desc", "The host holds no guest jcode/session backing: binds and /etc/fstab lines for "
                 "vm_sandbox_jcode and vm_sessions gone; /data/vm-sandbox/jcode-home, "
                 "/data/jcode-vm-sessions and /var/lib/libvirt/virtiofs/jcode_state removed; the "
                 "host's own ~/.jcode bind unchanged. OPEN 2026-09-18: jcode-home is gone and the "
                 "binds/fstab lines are gone, but /data/jcode-vm-sessions and the three virtiofs "
                 "dirs still exist (operator action outstanding).")

    print("=== 2. TP-206 step corrections ===")
    patch(TP206, [
        # Step 1: fixture + honest criterion
        ("""```bash
printf -- '-- fixture\\nSELECT 1;\\n' > firecontrol/sql/V999__tp206_fixture.sql
git add firecontrol/sql/V999__tp206_fixture.sql
.git/hooks/gates/A6_migration_lint.sh; echo "exit=$?"
git reset -q firecontrol/sql/V999__tp206_fixture.sql && rm -f firecontrol/sql/V999__tp206_fixture.sql
```

**Pass**: the gate exits 0 (or blocks only for the unregistered fixture, not for a missing
binary) **and** the output names the squawk binary it used, resolved from the repository.""",
         """```bash
printf -- '-- fixture\\nSELECT 1;\\n' > firecontrol/sql/R__tp206_fixture.sql
git add firecontrol/sql/R__tp206_fixture.sql
.git/hooks/gates/A6_migration_lint.sh; echo "exit=$?"
git reset -q firecontrol/sql/R__tp206_fixture.sql && rm -f firecontrol/sql/R__tp206_fixture.sql
```

A **repeatable** (`R__`) fixture is used deliberately: a `V__` fixture without a paired
`_smoke.sql`/`_e2e.sql` trips the N10 pairing check and makes the gate exit 1 for a reason
unrelated to engine availability (verified 2026-09-18). The criterion tested here is that the
gate **executes and renders a verdict** rather than dying on a missing engine.

**Pass**: the gate finds its engine and renders a verdict — exit 0 with a compliant repeatable
fixture, and no `FileNotFoundError`. The engine's *provenance* is asserted by steps 2 and 3."""),
        # Step 2: narrow the criterion to squawk
        ("**Pass**: the gate resolves squawk from the repository path\n(`firecontrol/docker/squawk-linux-x86_64`, or a path the repository installs) and no\n`Path(sys.executable).parent`-relative resolution remains.",
         "**Pass**: the gate resolves **squawk** from the repository path\n(`firecontrol/docker/squawk-linux-x86_64`). A `Path(sys.executable).parent`-relative resolution\n**legitimately remains for sqlfluff** (pip-installed, pinned in `setup_venv.sh`) — the criterion\nis that squawk specifically does not come from the venv. Verified 2026-09-18: a naive\n\"no venv-relative resolution anywhere\" check is wrong for this gate."),
        # Step 4: the pin lives in setup_venv.sh
        ("""grep -n 'squawk' setup_venv.sh || echo "setup_venv.sh does NOT provision squawk"
grep -rn -i 'squawk\\|sqlfluff' requirements*.txt || echo "neither engine pinned in requirements\"""",
         """grep -n 'squawk\\|sqlfluff==' setup_venv.sh || echo "setup_venv.sh does not account for the engines\""""),
        ("**Pass**: no hand-placed binary, and `setup_venv.sh` plus `requirements*.txt` account for both\ngate engines (squawk and sqlfluff).",
         "**Pass**: no hand-placed binary, and `setup_venv.sh` accounts for both gate engines — it\npins `sqlfluff==4.3.0` and verifies the vendored squawk. (The pin lives in the install driver;\nthere is no `requirements*.txt` for the main venv.)"),
        # Step 5: a working in-container lint invocation
        ("""sudo k3s kubectl exec -i -n overwatch firecontrol-db-0 -c migration-sidecar -- squawk - < /tmp/tp206_bad.sql; echo "runtime-side exit=$?\"""",
         """sudo k3s kubectl exec -i -n overwatch firecontrol-db-0 -c migration-sidecar -- \\
  sh -c 'cat > /tmp/tp206_bad.sql; squawk /tmp/tp206_bad.sql; rc=$?; rm -f /tmp/tp206_bad.sql; exit $rc' \\
  < /tmp/tp206_bad.sql; echo "runtime-side exit=$?\""""),
        ("**Pass**: both stages return the same verdict (both flag, or both accept) for the same file.",
         "**Pass**: both stages return the same verdict **and the same finding count** for the same\nfile. (Verified 2026-09-18: piping to `squawk -` does not work in this image — it exits 1 with\n\"Failed to find files for provided patterns\" without linting, which would make the step a\nvacuous both-exit-1 pass. The file must exist inside the container.)"),
    ])

    print("=== 3. N21 -> CLOSED in the DAR graph ===")
    db("upsert_mikado_node", "--graph-ci-id", "49871", "--node-id", "N21", "--node-type", "SPR",
       "--description",
       "SPR-1137 - one squawk, one version, one source. CLOSED 2026-09-18: the migration lint gate "
       "resolves its squawk engine from the repository-vendored artifact (pinned SHA-256, shared "
       "with the migration-sidecar image) instead of a hand-placed venv copy, so a fresh clone can "
       "run the gate; sqlfluff is pinned in setup_venv.sh and resolved explicitly; the vendored "
       "binary is registered as CI 50251. Evidence: TP-206 (50250) pre-fix FAIL -> post-fix PASS; "
       "CR 50253 (review_scope python); FIDO-sealed closure via ow_close_ci.",
       "--status", "CLOSED", "--artifact-ci-id", "50249", "--depends-on", "N1,N12",
       "--execution-order", "21")

    t = GRAPH.read_text()
    applied = 0
    lines = t.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| 21 | N21 — SPR-1137: one squawk, one version, one source"):
            lines[i] = (line.split("|")[0] + "| 21 | N21 — SPR-1137: one squawk, one version, one "
                        "source (migration lint gate vs runtime sidecar) | SPR | SPR-1137 "
                        "(50249, CLOSED) | N1, N12 | ✅ DONE 2026-09-18: the gate resolves squawk "
                        "from the repository-vendored artifact (pinned SHA-256, shared with the "
                        "sidecar image) instead of a hand-placed venv copy, so a fresh clone runs "
                        "the gate; sqlfluff pinned and resolved explicitly; the vendored binary "
                        "registered as CI 50251; TP-206 pre-fix FAIL → post-fix PASS; CR 50253; "
                        "FIDO-sealed closure |")
            applied += 1
            break
    t = "\n".join(lines) + "\n"
    if 'N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ⚙️"]' in t:
        t = t.replace('N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ⚙️"]',
                      'N21["N21 [SPR] SPR-1137 one<br/>squawk, one version ✅"]', 1)
        applied += 1
    GRAPH.write_text(t)
    print(f"  graph edits applied: {applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
