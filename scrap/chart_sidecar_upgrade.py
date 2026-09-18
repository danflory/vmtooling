#!/usr/bin/env python3
"""Add the Admin-UI sign sidecar to the Overwatch Helm chart and upgrade the
guest release (DAR-OW-158 / N17 Part B).

Why the chart: the sidecar needs the database endpoint, and OPF-010 states
"Literal ports are a violation" — the port lives in exactly one governed place
(`chart/values.yaml: database.port`, RFC-OW-103 "sole source, do not copy
elsewhere"). Templating the sidecar into the chart lets the DSN be assembled
from that single source instead of copying the number into another artifact.

Run from the workspace root on the guest. Idempotent.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
TEMPLATES = ROOT / "chart" / "templates"
VALUES = ROOT / "chart" / "values.yaml"
VALUES_GUEST = ROOT / "chart" / "values-guest.yaml"
PGPASS = pathlib.Path.home() / ".pgpass"
KUBECONFIG = "/etc/rancher/k3s/k3s.yaml"
RELEASE = "overwatch"
NAMESPACE = "overwatch"

VALUES_BLOCK = """
# -- Admin UI sign sidecar (RFC-OW-355 CLI / RFC-OW-370 FIDO2 WebAuthn).
# Serves the nonce + assertion endpoints ow_sign calls on localhost:8000.
adminUiSidecar:
  enabled: true
  replicas: 1
  image:
    repository: overwatch-admin-sidecar
    tag: "v2026.07.31.6-ubuntu-fips"
    pullPolicy: IfNotPresent
  port: 8000
  # The agent role, not the superuser: keeps signature logging out of agent reach
  # (RFC-OW-370 / D3 containment).
  dbUser: overwatch_agent
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 128Mi
"""

GUEST_BLOCK = """
# -- Admin UI sign sidecar (N17 Part B). Tag is the host-imported release tag.
adminUiSidecar:
  enabled: true
  image:
    repository: overwatch-admin-sidecar
    tag: "v2026.07.31.6-ubuntu-fips"
"""


def patch_values(path: pathlib.Path, block: str) -> str:
    text = path.read_text()
    if "adminUiSidecar:" in text:
        return f"SKIP {path.name}: adminUiSidecar present"
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block)
    return f"PATCHED {path.name}: added adminUiSidecar"


def install_templates() -> list[str]:
    out = []
    for name in (
        "admin-ui-sidecar-deployment.yaml",
        "admin-ui-sidecar-service.yaml",
        "admin-ui-sidecar-secret.yaml",
    ):
        src = pathlib.Path("/tmp") / name
        dst = TEMPLATES / name
        dst.write_text(src.read_text())
        out.append(f"WROTE {dst.relative_to(ROOT)}")
    return out


def agent_password() -> str:
    for line in PGPASS.read_text().splitlines():
        parts = line.strip().split(":")
        if len(parts) >= 5 and parts[3] == "overwatch_agent":
            return parts[4]
    raise SystemExit("ERROR: no overwatch_agent entry in ~/.pgpass")


def kube(args: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["sudo", "-n", "k3s", "kubectl", *args], capture_output=True, **kw  # type: ignore[arg-type]
    )


def helm(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["sudo", "-n", "/usr/local/bin/helm", "--kubeconfig", KUBECONFIG, *args],
        capture_output=True,
    )


def main() -> int:
    print(patch_values(VALUES, VALUES_BLOCK))
    print(patch_values(VALUES_GUEST, GUEST_BLOCK))
    for line in install_templates():
        print(line)

    # The sidecar objects were created by kubectl apply earlier; Helm cannot adopt
    # them, so remove them and let the release own them from here on.
    for kind, name in (
        ("deployment", "admin-ui-sidecar"),
        ("service", "admin-ui-sidecar"),
        ("secret", "admin-ui-sidecar-dsn"),
    ):
        proc = kube(["delete", kind, name, "-n", NAMESPACE, "--ignore-not-found"])
        print(f"DELETE {kind}/{name}: {proc.stdout.decode().strip() or proc.stderr.decode().strip()}")

    values_file = pathlib.Path("/tmp/.ow_guest_values.yaml")
    try:
        # --reuse-values does not re-merge the chart's values.yaml defaults for new
        # keys, so the new adminUiSidecar block would be nil. Instead: take the
        # release's live values, add the new component to them, and upgrade from
        # that file. This preserves the installed configuration exactly.
        got = helm(["get", "values", RELEASE, "-n", NAMESPACE, "-o", "json"])
        if got.returncode != 0:
            sys.stderr.write(got.stderr.decode())
            return got.returncode
        live = json.loads(got.stdout.decode() or "{}")
        live.setdefault("adminUiSidecar", {}).update(
            {
                "enabled": True,
                "replicas": 1,
                "port": 8000,
                "dbUser": "overwatch_agent",
                "image": {
                    "repository": "overwatch-admin-sidecar",
                    "tag": "v2026.07.31.6-ubuntu-fips",
                    "pullPolicy": "IfNotPresent",
                },
            }
        )
        live.setdefault("database", {}).setdefault("agentConnection", {})["password"] = agent_password()
        values_file.write_text(json.dumps(live, indent=2))
        values_file.chmod(0o600)
        proc = helm(
            [
                "upgrade",
                RELEASE,
                "./chart",
                "-n",
                NAMESPACE,
                "-f",
                str(values_file),
                "--wait",
                "--timeout",
                "180s",
            ]
        )
    finally:
        values_file.unlink(missing_ok=True)
    sys.stdout.write(proc.stdout.decode()[-1500:])
    sys.stderr.write(proc.stderr.decode()[-1500:])
    if proc.returncode != 0:
        return proc.returncode
    proc = kube(["get", "pods", "-n", NAMESPACE, "-l", "component=admin-ui-sidecar", "-o", "wide"])
    sys.stdout.write(proc.stdout.decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
