#!/usr/bin/env python3
"""Log the two remaining swarm findings that are not covered by the SPR-1137 closure.

1. The HOST clone estate is unenforced (lizard's real finding, once its misdirected verdict is
   corrected: it verified the host, not the guest).
2. The squawk pin is duplicated and only half-verified (jaguar's extras).
"""
from __future__ import annotations

import pathlib
import subprocess

REPO = pathlib.Path.home() / "dev_env/clones/Overwatch"


def log(*args: str) -> None:
    r = subprocess.run([".venv/bin/python", "OW_tools/db_write.py", "log_lesson", *args],
                       capture_output=True, text=True, cwd=REPO)
    ok = '"status": "success"' in (r.stdout + r.stderr)
    print(f"  {'OK' if ok else 'FAIL'}: {args[3] if len(args) > 3 else ''}")
    if not ok:
        print("   ", (r.stdout + r.stderr)[-250:])


def main() -> int:
    log("--source-ci-id", "50249", "--key", "host-estate-hooks-unenforced",
        "--title", "The HOST clone estate is unenforced too - verify which machine a hook claim is about",
        "--finding",
        "After wiring the enforcement hooks into all six GUEST clones (N20), an adversarial verifier "
        "reported 'N20 falsified: only Overwatch has hooks, and its install is stale'. The verdict "
        "was about the wrong machine: the HOST clones live at /home/d/dev_env/Overwatch{,_1..5} and "
        "the GUEST clones at ~/dev_env/clones/Overwatch{,_1..5} (reachable as d@192.168.122.55), and "
        "the verifier checked the host. Re-checked: the guest estate is uniform (all six: pre-commit "
        "present, 18 gate scripts, 13 enabled), while the host estate really is unenforced - host "
        "Overwatch carries a stale install (17 gates, 12 enabled, no A24, files not chattr +i) and "
        "host Overwatch_1.._5 have none. The stale-install half of the finding is real and new.",
        "--reuse",
        "Two rules. (1) A hook/enforcement claim is per-machine: state the machine and the clone "
        "root path explicitly, and when a verification contradicts your own observation, first "
        "confirm which estate was inspected before accepting or rejecting it. (2) Wire hooks on "
        "every estate you work in - the host clones are still live until N13's host cutover removes "
        "them, so a stale or absent install there silently admits unregistered paths.",
        "--node-type", "WORKFLOW", "--topic", "gate_enforcement", "--grade", "ADVISORY")

    log("--source-ci-id", "50249", "--key", "pinned-artifact-half-verified",
        "--title", "A pinned artifact is only pinned if every copy is checked - duplicated pins drift",
        "--finding",
        "The squawk SHA-256 is duplicated: gate_sql_lint.py asserts it at run time and "
        "Dockerfile.migration-sidecar verifies it at image build. The Dockerfile also declares "
        "ARG SQUAWK_VERSION=2.59.0 which is never used (a dead pin next to a live SHA), and "
        "setup_venv.sh only prints and executes the vendored binary without verifying its hash. So "
        "the pin is enforced in two places, asserted in one, and decorative in a third.",
        "--reuse",
        "Keep one authoritative pin per artifact and derive every consumer from it (a single "
        "manifest the gate, the image build and the setup path all read). A declared-but-unused "
        "version ARG next to a live hash is a drift trap: it invites someone to bump the ARG and "
        "believe the artifact moved.",
        "--node-type", "CODE", "--topic", "artifact_pinning", "--grade", "ADVISORY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
