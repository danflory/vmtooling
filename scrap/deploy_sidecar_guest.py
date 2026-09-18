#!/usr/bin/env python3
"""Deploy the Admin-UI sign sidecar into the guest k3s `overwatch` namespace.

DAR-OW-158 / N17 Part B. Deviations from the committed host manifest
(`k8s/admin-ui-sidecar.yaml`), both recorded as RD-15/RD-16 in research 22:

  1. DSN targets the guest database service directly (no pgbouncer in the guest),
     instead of the host-era `host=pgbouncer port=51729`.
  2. The connection uses the `overwatch_agent` credential (from the guest's
     ~/.pgpass) rather than the database superuser, preserving the RFC-OW-370 /
     D3 containment.

The password never touches argv or stdout: it is read from ~/.pgpass, embedded in
the Secret manifest, and piped to kubectl on stdin.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

NAMESPACE = "overwatch"
SECRET_NAME = "admin-ui-sidecar-dsn"
PGPASS = pathlib.Path.home() / ".pgpass"

SECRET_YAML = """apiVersion: v1
kind: Secret
metadata:
  name: {name}
  namespace: {ns}
type: Opaque
stringData:
  FIRECONTROL_DSN: "{dsn}"
"""

DEPLOY_YAML = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: admin-ui-sidecar
  namespace: {ns}
  labels:
    app: admin-ui-sidecar
  annotations:
    compliance.overwatch.io/fips-boundary: "container"
    compliance.overwatch.io/fips-cmvp: "4282"
    compliance.overwatch.io/justification: "DAR-OW-117 Host Kernel Gap"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: admin-ui-sidecar
  template:
    metadata:
      labels:
        app: admin-ui-sidecar
      annotations:
        compliance.overwatch.io/fips-boundary: "container"
        compliance.overwatch.io/fips-cmvp: "4282"
        compliance.overwatch.io/justification: "DAR-OW-117 Host Kernel Gap"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
      containers:
        - name: admin-ui-sidecar
          image: overwatch-admin-sidecar:v2026.07.31.6-ubuntu-fips
          imagePullPolicy: IfNotPresent
          env:
            - name: FIRECONTROL_DSN
              valueFrom:
                secretKeyRef:
                  name: {secret}
                  key: FIRECONTROL_DSN
          ports:
            - containerPort: 8000
              hostPort: 8000
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
          volumeMounts:
            - name: tmp-volume
              mountPath: /tmp
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 6
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: tmp-volume
          emptyDir: {{}}
---
apiVersion: v1
kind: Service
metadata:
  name: admin-ui-sidecar
  namespace: {ns}
spec:
  selector:
    app: admin-ui-sidecar
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
"""


def agent_password() -> str:
    """Read the overwatch_agent password from ~/.pgpass (never printed)."""
    for line in PGPASS.read_text().splitlines():
        parts = line.strip().split(":")
        if len(parts) >= 5 and parts[3] == "overwatch_agent":
            return parts[4]
    raise SystemExit("ERROR: no overwatch_agent entry in ~/.pgpass")


def main() -> int:
    pw = agent_password()
    dsn = (
        "dbname=firecontrol user=overwatch_agent "
        f"host=firecontrol-db port=5432 password={pw}"
    )
    manifest = SECRET_YAML.format(name=SECRET_NAME, ns=NAMESPACE, dsn=dsn) + "---\n" + DEPLOY_YAML.format(
        ns=NAMESPACE, secret=SECRET_NAME
    )
    proc = subprocess.run(
        ["sudo", "-n", "k3s", "kubectl", "apply", "-f", "-"],
        input=manifest.encode(),
        capture_output=True,
    )
    sys.stdout.write(proc.stdout.decode())
    sys.stderr.write(proc.stderr.decode())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
