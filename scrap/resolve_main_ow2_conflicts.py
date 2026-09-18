#!/usr/bin/env python3
"""Resolve the main + ow2/DAR-OW-158 merge conflicts (4 files).

Decisions (all evidence-based, operator-approved):
 1. `_connections/__init__.py`  -> UNION: the auto-merged `_dsn.py` now defines BOTH
    `parse_conninfo` and `resolve_endpoint`, so export both.
 2. `_testing.py`               -> THEIRS (`_2`): main's only change to this file was the
    same pg_prove endpoint fix, done with the older `resolve_endpoint()`; `_2`'s version
    uses `parse_conninfo(resolve_dsn())` with a missing-host/port guard and matches the
    surrounding env loop and `OW_tools/tests/conftest.py`. Nothing else is lost.
 3. `docs/praca/TP/TP-198.md`   -> THEIRS (`_2`): the DB registers CI 49983 at that path as
    "RFC-WF-033 VV — /commit per-commit closure-micro absorption", which is `_2`'s content.
    main's body there was the RFC-OW-419 cutover verification (recoverable at main's
    commit 9e6690f79) — a document-identity collision, reported to the operator.
 4. `test_ow_query_efsm_transitions.sql` -> UNION: keep main's checks (round-trip +
    companion e2e reference) and append `_2`'s unique return-column projection check.
"""
from __future__ import annotations

import pathlib
import sys

CONN = pathlib.Path("OW_tools/db_write_commands/_connections/__init__.py")
TESTING = pathlib.Path("OW_tools/db_write_commands/_testing.py")
SQL = pathlib.Path("firecontrol/tests/sproc_regression/auth/test_ow_query_efsm_transitions.sql")

EXTRA_SQL_CHECK = """-- 8. Return columns are the documented EFSM tuple projection
SELECT is(
    (SELECT proargnames[array_position(proargmodes, 't'):]
       FROM pg_proc
      WHERE proname = 'ow_query_efsm_transitions'
        AND pronamespace = 'auth'::regnamespace),
    ARRAY['from_phase', 'from_status', 'event', 'to_phase', 'to_status'],
    'Return columns match spec: from_phase, from_status, event, to_phase, to_status'
);
"""


def resolve(path: pathlib.Path, choices: list[str]) -> int:
    """Replace each conflict block with the chosen side ('ours' | 'theirs')."""
    lines = path.read_text().splitlines()
    out: list[str] = []
    idx = 0
    i = 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            if idx >= len(choices):
                raise SystemExit(f"{path}: more conflicts than choices")
            choice = choices[idx]
            idx += 1
            ours: list[str] = []
            theirs: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("======="):
                ours.append(lines[i])
                i += 1
            i += 1  # skip =======
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i])
                i += 1
            i += 1  # skip >>>>>>>
            out.extend(ours if choice == "ours" else theirs)
        else:
            out.append(lines[i])
            i += 1
    path.write_text("\n".join(out) + "\n")
    print(f"  {path}: {idx} conflict(s) resolved ({choices})")
    return idx


def main() -> int:
    # 1. __init__.py: union — both names, in both the import list and __all__
    t = CONN.read_text()
    t = t.replace("<<<<<<< HEAD\n    \"resolve_endpoint\",\n=======\n    \"parse_conninfo\",\n>>>>>>> refs/remotes/ow2/DAR-OW-158",
                  "    \"resolve_endpoint\",\n    \"parse_conninfo\",")
    # the import-list conflict (if any) is handled by the same union idea
    lines = t.splitlines()
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            ours, theirs = [], []
            i += 1
            while not lines[i].startswith("======="):
                ours.append(lines[i]); i += 1
            i += 1
            while not lines[i].startswith(">>>>>>>"):
                theirs.append(lines[i]); i += 1
            i += 1
            union = [x for x in ours]
            for x in theirs:
                if x not in union:
                    union.append(x)
            out.extend(union)
        else:
            out.append(lines[i]); i += 1
    CONN.write_text("\n".join(out) + "\n")
    print(f"  {CONN}: union applied (resolve_endpoint + parse_conninfo)")

    # 2. _testing.py: theirs for both hunks
    resolve(TESTING, ["theirs", "theirs"])

    # 3. sql: ours for all four hunks, then append _2's unique check
    resolve(SQL, ["ours", "ours", "ours", "ours"])
    s = SQL.read_text()
    marker = "SELECT * FROM finish();"
    if EXTRA_SQL_CHECK.strip() not in s and marker in s:
        s = s.replace(marker, EXTRA_SQL_CHECK + "\n" + marker, 1)
        SQL.write_text(s)
        print(f"  {SQL}: appended the return-column projection check from _2")

    # 4. TP-198.md is resolved separately via `git checkout --theirs`
    leftovers = []
    for p in (CONN, TESTING, SQL):
        txt = p.read_text()
        if "<<<<<<<" in txt or ">>>>>>>" in txt:
            leftovers.append(str(p))
    if leftovers:
        print("UNRESOLVED MARKERS REMAIN:", leftovers, file=sys.stderr)
        return 1
    print("no conflict markers remain in the three text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
