#!/usr/bin/env python3
"""TP-206 runner (post-fix) for SPR-1137.

Executes the six TP-206 steps against the PRE-FIX tree and records the result as a
pre_fix test execution (the TDD evidence G-TDD-2 requires).

Step 1 is demonstrated in Overwatch_5, a clone whose venv has no squawk, because that is
where B-2 manifests; the other steps run in the authoritative clone. Cleanup is always
performed (fixture removed, index reset, .git_hold cleared).
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

MAIN = pathlib.Path.home() / "dev_env/clones/Overwatch"
OW5 = pathlib.Path.home() / "dev_env/clones/Overwatch_5"
TP = "TP-206"
SPR_CI = 50249
TP_CI = 50250


def run(cwd: pathlib.Path, *args: str, stdin: str | None = None) -> tuple[int, str]:
    r = subprocess.run(list(args), capture_output=True, text=True, cwd=cwd, input=stdin)
    return r.returncode, (r.stdout + r.stderr).strip()


def db(*args: str) -> bool:
    rc, out = run(MAIN, ".venv/bin/python", "OW_tools/db_write.py", *args)
    return '"status": "success"' in out


results: list[tuple[int, str, str, str]] = []


def record(num: int, covers: str, verdict: str, evidence: str) -> None:
    results.append((num, covers, verdict, evidence))
    print(f"  Step {num} [{covers}]: {verdict} — {evidence[:110]}")


def main() -> int:
    # Step 1 — gate runs from a clean checkout (demonstrated in Overwatch_5, no squawk)
    fixture = OW5 / "firecontrol/sql/R__tp206_fixture.sql"
    fixture.write_text("-- fixture\nSELECT 1;\n")
    run(OW5, "git", "add", str(fixture.relative_to(OW5)))
    rc, out = run(OW5, ".git/hooks/gates/A6_migration_lint.sh")
    run(OW5, "git", "reset", "-q", str(fixture.relative_to(OW5)))
    fixture.unlink(missing_ok=True)
    subprocess.run(["sudo", "-n", "rm", "-f", str(OW5 / ".git_hold")], capture_output=True)
    missing = "FileNotFoundError" in out or "squawk" in out and rc != 0
    record(1, "V-2/B-2", "FAIL" if missing else "PASS",
           f"gate exit={rc} in a venv without squawk: {out.splitlines()[-1][:80] if out else 'no output'}")

    # Step 2 — gate resolves the repository artifact?
    gate = MAIN / "firecontrol/gates/gate_sql_lint.py"
    src = gate.read_text()
    squawk_from_repo = '_SQUAWK = str(_REPO_ROOT' in src
    squawk_from_venv = 'Path(sys.executable).parent / "squawk"' in src
    record(2, "V-1/B-1", "PASS" if (squawk_from_repo and not squawk_from_venv) else "FAIL",
           f"squawk_from_repo={squawk_from_repo} squawk_from_venv={squawk_from_venv} "
           "(sqlfluff legitimately stays venv-resolved)")

    # Step 3 — gate version == image version?
    rc_g, gate_ver = run(MAIN, "firecontrol/docker/squawk-linux-x86_64", "--version")
    rc_i, img_ver = run(MAIN, "sudo", "-n", "k3s", "kubectl", "exec", "-n", "overwatch",
                        "firecontrol-db-0", "-c", "migration-sidecar", "--", "squawk", "--version")
    same = gate_ver.strip() == img_ver.strip()
    record(3, "V-3/B-1", "PASS" if same else "FAIL",
           f"gate-resolved={gate_ver.strip()} image={img_ver.strip()}")

    # Step 4 — no hand-placed binary; both engines provisioned?
    hand_placed = (MAIN / ".venv/bin/squawk").exists()
    setup = (MAIN / "setup_venv.sh").read_text() if (MAIN / "setup_venv.sh").exists() else ""
    setup_has_squawk = "squawk" in setup
    pinned = "sqlfluff==" in setup
    ok4 = (not hand_placed) and setup_has_squawk and pinned
    record(4, "V-1,V-2/B-2", "PASS" if ok4 else "FAIL",
           f"hand_placed={hand_placed} setup_venv_provisions_squawk={setup_has_squawk} pinned={pinned}")

    # Step 5 — one non-compliant migration, same verdict at both stages?
    bad = pathlib.Path("/tmp/tp206_bad.sql")
    bad.write_text("-- fixture: non-compliant\nALTER TABLE auth.udrs ADD COLUMN tp206_probe int NOT NULL;\n")
    rc_v, out_v = run(MAIN, "firecontrol/docker/squawk-linux-x86_64", str(bad))
    rc_c, out_c = run(MAIN, "sudo", "-n", "k3s", "kubectl", "exec", "-i", "-n", "overwatch",
                      "firecontrol-db-0", "-c", "migration-sidecar", "--", "sh", "-c",
                      "cat > /tmp/tp206_bad.sql; squawk /tmp/tp206_bad.sql; rc=$?; "
                      "rm -f /tmp/tp206_bad.sql; exit $rc",
                      stdin=bad.read_text())
    findings_match = out_v.count("issue") == out_c.count("issue")
    bad.unlink(missing_ok=True)
    verdicts_match = (rc_v != 0) == (rc_c != 0)
    record(5, "V-4/B-1", "PASS" if verdicts_match else "FAIL",
           f"vendored exit={rc_v} in-image exit={rc_c} (same verdict: {verdicts_match}, same finding count: {findings_match})")

    # Step 6 — vendored binary is a governed CI?
    rc_s, sha = run(MAIN, "sha256sum", "firecontrol/docker/squawk-linux-x86_64")
    rc_q, q = run(MAIN, ".venv/bin/python", "OW_tools/db_write.py", "query_ci_by_path",
                  "--path", "firecontrol/docker/squawk-linux-x86_64")
    registered = '"id":' in q and "squawk-linux-x86_64" in q
    record(6, "V-5/B-3", "PASS" if registered else "FAIL",
           f"sha256={sha.split()[0][:16]}… registered={registered}")

    fails = [r for r in results if r[2] == "FAIL"]
    passes = [r for r in results if r[2] == "PASS"]
    verdict = "FAIL" if fails else "PASS"
    print(f"\nTP-206 pre-fix verdict: {verdict} ({len(passes)} PASS, {len(fails)} FAIL)")

    notes = (f"post_fix: SPR-1137 post-fix state, TP-206 run 2026-09-18 after F-1..F-5. "
             f"{len(fails)} FAIL / {len(passes)} PASS — "
             + "; ".join(f"step {n} FAIL: {e[:60]}" for n, _, v, e in results if v == "FAIL")[:600])
    ok = db("insert_test_exec", "--tp-id", TP, "--verdict", verdict, "--executor", "agent",
            "--workflow-name", "doSPR2", "--notes", notes, "--ci-id", str(SPR_CI),
            "--session-id", "2071")
    print("recorded test_exec:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
