#!/usr/bin/env python3
"""SPR-1137: satisfy the A9 (pyright) and A16 (ruff format) gates on the patched gate.

OPF-042 §7: use explicit `+` concatenation for multi-line string literals, because pyright's
reportImplicitStringConcatenation flags the parenthesised adjacent-literal idiom.
Then run ruff format.
"""
from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"
GATE = REPO / "firecontrol/gates/gate_sql_lint.py"

OLD = '''        _engine_error(
            f"squawk at {_SQUAWK} has sha256 {digest[:16]}… but the pinned artifact is "
            f"{_SQUAWK_SHA256[:16]}… — the gate would lint with a different engine than the "
            "migration sidecar bakes")'''

NEW = '''        _engine_error(
            f"squawk at {_SQUAWK} has sha256 {digest[:16]}... but the pinned artifact is "
            + f"{_SQUAWK_SHA256[:16]}... - the gate would lint with a different engine than "
            + "the migration sidecar bakes"
        )'''

OLD2 = '''    if not squawk.is_file():
        _engine_error(
            f"squawk not found at {_SQUAWK} (expected the repository-vendored artifact)")'''

NEW2 = '''    if not squawk.is_file():
        _engine_error(
            f"squawk not found at {_SQUAWK} (expected the repository-vendored artifact)"
        )'''


def main() -> int:
    t = GATE.read_text()
    for old, new in ((OLD, NEW), (OLD2, NEW2)):
        if old in t:
            t = t.replace(old, new, 1)
            print("patched a concatenation block")
        elif new.split("\n")[0] in t:
            print("already patched")
        else:
            print("MISS:", old.split("\n")[0][:60])
    GATE.write_text(t)

    for cmd in ((".venv/bin/ruff", "format", str(GATE.relative_to(REPO))),
                (".venv/bin/pyright", str(GATE.relative_to(REPO)))):
        r = subprocess.run(list(cmd), capture_output=True, text=True, cwd=REPO)
        tail = (r.stdout + r.stderr).strip().splitlines()
        print(f"{cmd[0].split('/')[-1]}: exit={r.returncode} | {tail[-1][:110] if tail else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
