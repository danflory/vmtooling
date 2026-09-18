#!/usr/bin/env python3
"""SPR-1137 fix (F-1..F-5) — prepared, NOT applied until the operator re-touches.

Design refinement forced by the evidence: the two gate engines need DIFFERENT provenance
rules, and that distinction is the real fix.

  * squawk is a vendored binary (not pip-installable) -> the REPOSITORY artifact is the
    source of truth, hash-pinned, shared with the image build.
  * sqlfluff is pip-installable -> the VENV is the source of truth, pinned in the install
    driver. It must be resolved explicitly rather than by bare `sqlfluff` on PATH, which
    today depends on whether the shell activated the venv.

Changes:
  F-1/F-2/F-4  firecontrol/gates/gate_sql_lint.py
  F-3          setup_venv.sh (pin sqlfluff, verify the vendored squawk)
  F-5          register firecontrol/docker/squawk-linux-x86_64 as a CI
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"
GATE = REPO / "firecontrol/gates/gate_sql_lint.py"
SETUP = REPO / "setup_venv.sh"
BINARY = "firecontrol/docker/squawk-linux-x86_64"
PINNED_SHA = "547623c6c4cd54035f8062e759c4b2d346bde55f84eb0c442bb706db6b24cafb"

OLD_RESOLUTION = """# Resolve squawk binary in the same venv as the Python interpreter
_VENV_BIN = Path(sys.executable).parent
_SQUAWK = str(_VENV_BIN / "squawk")"""

NEW_RESOLUTION = '''# ── Gate engine provenance (SPR-1137) ─────────────────────────────
# A gate's verdict is a function of its inputs, so its ENGINE is a governed artifact.
# Two engines, two provenance rules:
#
#   * squawk  — a vendored binary, not pip-installable. The REPOSITORY artifact is the
#               single source of truth; the migration-sidecar image bakes this same file,
#               so one version serves both lint stages. Verified by pinned SHA-256.
#   * sqlfluff — pip-installable. The VENV is the source of truth (pinned in setup_venv.sh)
#               and is resolved explicitly, never via bare PATH lookup.
_VENV_BIN = Path(sys.executable).parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SQUAWK = str(_REPO_ROOT / "firecontrol" / "docker" / "squawk-linux-x86_64")
_SQUAWK_SHA256 = "547623c6c4cd54035f8062e759c4b2d346bde55f84eb0c442bb706db6b24cafb"
_SQLFLUFF = str(_VENV_BIN / "sqlfluff")


def _engine_error(msg: str) -> None:
    print(f"  ❌ SQL lint engine: {msg}", file=sys.stderr)
    print("     The gate cannot render a verdict without its rule engine.", file=sys.stderr)
    sys.exit(1)


def _assert_engines() -> None:
    """Assert both engines are present and that squawk is the pinned repository artifact.

    Fails closed with an actionable message instead of a FileNotFoundError traceback, and
    fails if the vendored binary is not the version the image bakes (drift guard).
    """
    squawk = Path(_SQUAWK)
    if not squawk.is_file():
        _engine_error(
            f"squawk not found at {_SQUAWK} (expected the repository-vendored artifact)")
    digest = hashlib.sha256(squawk.read_bytes()).hexdigest()
    if digest != _SQUAWK_SHA256:
        _engine_error(
            f"squawk at {_SQUAWK} has sha256 {digest[:16]}… but the pinned artifact is "
            f"{_SQUAWK_SHA256[:16]}… — the gate would lint with a different engine than the "
            "migration sidecar bakes")
    if not Path(_SQLFLUFF).is_file():
        _engine_error(f"sqlfluff not found at {_SQLFLUFF} (run setup_venv.sh)")'''

SETUP_ADDITION = '''
# ── SQL lint gate engines (SPR-1137) ──────────────────────────────
# squawk is a vendored binary shared with the migration-sidecar image: the REPOSITORY
# artifact is the source of truth, so there is nothing to install — only to verify.
# sqlfluff is pip-installed above and pinned here so the gate's rule set is reproducible.
SQUAWK_BIN="$REPO_ROOT/firecontrol/docker/squawk-linux-x86_64"
if [ ! -x "$SQUAWK_BIN" ]; then
    echo "ERROR: vendored squawk missing or not executable: $SQUAWK_BIN" >&2
    exit 1
fi
echo "==> SQL lint engines"
echo -n "    squawk (vendored): "; "$SQUAWK_BIN" --version
'''


def db(*args: str) -> bool:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", *args],
                       capture_output=True, text=True, cwd=REPO)
    ok = '"status": "success"' in r.stdout + r.stderr
    print(f"    {'OK' if ok else 'FAIL'}: {' '.join(args[:2])}")
    return ok


def main() -> int:
    # ---- F-2 / F-1 / F-4: the gate ------------------------------------------
    src = GATE.read_text()
    if "_SQUAWK_SHA256" in src:
        print("gate already patched")
    else:
        if OLD_RESOLUTION not in src:
            print("ERROR: gate resolution block not found verbatim; refusing to guess",
                  file=sys.stderr)
            return 1
        src = src.replace(OLD_RESOLUTION, NEW_RESOLUTION, 1)
        # call the assertion at the top of main()
        m = re.search(r"^def main\(.*?\) -> int:\n", src, re.M)
        if not m:
            print("ERROR: main() not found", file=sys.stderr)
            return 1
        src = src[:m.end()] + "    _assert_engines()\n\n" + src[m.end():]
        # import hashlib
        src = src.replace("import re\nimport subprocess", "import hashlib\nimport re\nimport subprocess", 1)
        # F-1 declaration in the docstring
        src = src.replace(
            "Authority: RFC-OW-283 (DAR-OW-124 P12), OPF-014 §6",
            "Authority: RFC-OW-283 (DAR-OW-124 P12), OPF-014 §6\n"
            "Engine provenance (SPR-1137): squawk is the repository-vendored artifact\n"
            "`firecontrol/docker/squawk-linux-x86_64` (hash-pinned, shared with the migration\n"
            "sidecar image); sqlfluff is the pinned venv install. One engine, one source.",
            1)
        GATE.write_text(src)
        print("gate patched (F-1, F-2, F-4)")

    # ---- F-3: setup_venv.sh --------------------------------------------------
    s = SETUP.read_text()
    if "sqlfluff==" not in s:
        s = s.replace("  sqlfluff \\\n", "  sqlfluff==4.3.0 \\\n", 1)
    if "SQUAWK_BIN" not in s:
        anchor = 'echo "==> Versions"'
        if anchor in s:
            s = s.replace(anchor, SETUP_ADDITION.lstrip("\n") + "\n" + anchor, 1)
        else:
            s += SETUP_ADDITION
    SETUP.write_text(s)
    print("setup_venv.sh patched (F-3: sqlfluff pinned, vendored squawk verified)")

    # ---- F-5: register the vendored binary ----------------------------------
    print("registering the vendored binary:")
    db("ow_write_ci", "--path", BINARY, "--field", "doc_type=CODE")

    # ---- verify --------------------------------------------------------------
    rc = subprocess.run([".venv/bin/python", "-c", "import ast,pathlib;"
                         "ast.parse(pathlib.Path('firecontrol/gates/gate_sql_lint.py').read_text())"],
                        capture_output=True, text=True, cwd=REPO)
    print("gate syntax:", "OK" if rc.returncode == 0 else rc.stderr[-200:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
