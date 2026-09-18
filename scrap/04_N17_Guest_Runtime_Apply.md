---
id:
title: DAR-OW-158 N17 — Guest Runtime and FIDO2 Enablement Implementation Note
status: ACTIVE
created: 2026-09-18
domain: INFRASTRUCTURE
parent: 49825
parent_ci: 49825
phase: DEVELOPMENT
type: DAR.RESEARCH.IMPLEMENTATION
version: "2026_09_18_16_32"
---

# DAR-OW-158 N17 — Guest Runtime and FIDO2 Enablement Implementation Note

Applied 2026-09-18 on the `sandbox` guest (Ubuntu 24.04.5, kernel 6.8.0-139-generic)
and on the host during an operator `grant sudo` window. Every row below was observed
live; nothing is recorded as PASS without its evidence. Findings and decisions live in
research 22 (udrs 50215), SPR-1135 (udrs 50221) and the N10/N11 rework apply note
(udrs 50216, `04_Implementation/03`); this note records the **executed changes**.

## Per-item result

| # | Item | Result | Observed value |
|:--|:-----|:-------|:---------------|
| 1 | YubiKey USB hostdev attached to the `sandbox` domain (N17 Part A) | **DONE** (live; not persisted) | `1050:0407` matched by vendor/product; guest `lsusb` shows the key; in-guest CTAP2 `getInfo` returns aaguid `2fc0579f-8113-47ea-b116-bb5a8db9202a`, CTAP `U2F_V2/FIDO_2_0/FIDO_2_1_PRE`. Artifacts: `~/dev_env/vmtooling/yubikey_usb_hostdev.xml` and `~/.local/bin/sandbox-fido` (host) |
| 2 | Guest udev rule granting FIDO hidraw to the seat-less SSH session | **DONE** | `/etc/udev/rules.d/70-yubikey-fido.rules` → `SUBSYSTEM=="hidraw", ENV{ID_FIDO_TOKEN}=="1", MODE="0660", GROUP="plugdev"`; `/dev/hidraw1` is `crw-rw---- root plugdev`. Without it the SSH path got `EACCES`: stock Ubuntu grants `uaccess` only, which needs a seat |
| 3 | Admin-UI sign sidecar deployed into guest k3s (N17 Part B) | **DONE** | Helm release `overwatch` REVISION 2; `admin-ui-sidecar` pod 1/1 Running; `GET /health` → 200; `POST /api/v1/auth/nonce` with `X-Forwarded-User: d` returns a nonce. Chart templates `chart/templates/admin-ui-sidecar-*.yaml` (CIs 50225–50227) |
| 4 | `git-lfs` installed in the guest | **DONE** | `git-lfs/3.4.1`. **Why it matters**: the repo's `.git/hooks/pre-push` exits 2 when `git-lfs` is absent, so **no push was possible from the guest** until this was installed. The fix was to install the dependency, not to bypass the hook |
| 5 | Guest native Postgres purged (the vestigial instance) | **DONE** | `postgresql*` packages purged, cluster `main` dropped, `postgresql.service` / `postgresql@16-main` gone, port 5432 free, `/var/lib/postgresql`, `/etc/postgresql*`, `/var/log/postgresql` removed. It held no application data (only the default `postgres` DB, 7.5 MB); the in-cluster pod holds the real `firecontrol` (508 MB). Operator-authorized, no dump (backups exist) |
| 6 | Withdrawn N10/N11 jcode/session share torn down | **DONE** for domain + guest + host binds; backing directories **outstanding** | Full record in `04_Implementation/03_N10_N11_JCode_Home_Rework_Apply.md` (udrs 50216). Summary: both virtiofs devices detached live and persistently; the guest share unmounted and its mountpoint removed; the host binds unmounted and their `/etc/fstab` lines deleted. Outstanding: `rm -rf` of `/data/vm-sandbox/jcode-home` and `/data/jcode-vm-sessions` plus `rmdir` of the three virtiofs dirs (operator-executed; the agent's destructive-path gate refuses) |
| 7 | Host root window used | **DONE** (operator-sequenced) | `grant sudo` consumed for: `/etc/fstab` safety copy (`/etc/fstab.bak.20260918-1214`), `umount` of the two binds, two `sed -i` fstab deletions. Nothing else ran as root; the host's own `~/.jcode` → `/dev/sdb1[/jcode-home]` bind was left untouched |
| 8 | Guest clone pushed to origin (the 198-commit divergence resolved) | **DONE** | `git push origin main` → `d81b6d550..65c3b70a4`; after fetch, ahead/behind is `0 0`. `origin/main` is now the guest clone's head. The `vmtooling` repo was pushed too (`c545631..47aee40`) |

## Security inconsistency (logged, not remediated — operator direction)

The sidecar must receive the `overwatch_agent` credential to build its DSN, and the Helm
mechanism for that stores it in the release values (hence in the Helm release Secret). The
operator has stated that less-than-secure credential handling is currently accepted and
directed that this be **recorded rather than fixed**. Recorded here as directed. The
containment property that *was* preserved: the sidecar connects as `overwatch_agent`, not
as the database superuser, so `audit.ow_log_signature_change` stays out of agent reach
(RFC-OW-370 / D3).

## Repo staging corrections recorded

- The committed host manifest `k8s/admin-ui-sidecar.yaml` carries the host-era DSN
  (`host=pgbouncer port=51729`). The guest runs no pgbouncer, so the sidecar is templated
  into the chart instead and composes its endpoint from `database.agentConnection.host` +
  `database.port` (RFC-OW-103 sole source), avoiding a copied port literal (OPF-010).
- The scaffolded SPR frontmatter emitted the invalid EFSM pair `(DEVELOPMENT, DRAFT)` and
  `sync_ci` rejected it. Corrected to `status: ACTIVE` (valid pairs: `(DRAFT, ACTIVE)`
  initial, `(DEVELOPMENT, ACTIVE)` activated).
- `prune_mikado_nodes` is not available to the agent role (permission denied) — correct
  containment. Nodes are retired by soft-marking (`status: SUPERSEDED` sets `retired_at`,
  SPR-1100), which is how the redundant SPR-owned graph nodes were retired.
- `sync_ci` repoints a moved CI's `storage_path` but does **not** update `doc_type`; the
  reclassification needed `ow_write_ci --field doc_type=...` as well.

## Outstanding / next

1. **Backing directories** (SPR-1135 V-3): operator runs the `rm -rf` / `rmdir` block.
2. **TP-188 coverage** (SPR-1135 V-4): add the step asserting a guest-local jcode home and
   the absence of any host-backed jcode share; it must FAIL pre-fix and PASS post-fix.
3. **FIDO2 button-touch end-to-end test**: run the real in-guest `ow_sign` with an operator
   touch. Open observation to settle then: a `sign/begin` probe returned 200 with an
   empty-looking payload (`rpId` null, zero-length challenge), which may be a probe artifact.
4. **Loose tails pending decision**: the now-void inbound `tcp/5432` allow from virbr0 in
   `/etc/nftables.conf` (its stated justification was the deleted native Postgres), and the
   inert N9 memory drop-in
   `/etc/systemd/system/postgresql@16-main.service.d/10-memory-limit.conf` (its target unit
   no longer exists).
5. **Branch consolidation**: `Overwatch_2`'s `DAR-OW-158` is 65 commits ahead of
   `origin/DAR-OW-158` and clean to push; `Overwatch_5` is a divergent clone (same GitHub URL
   under a remote named `Overwatch`) whose `DAR-OW-158` is not in main's history and whose
   worktree holds 20 uncommitted paths. Both await operator direction.
6. **SCRIPTS**: the executed tooling (sidecar deploy, chart upgrade, teardown, record
   updates) currently sits uncommitted in the host's `~/dev_env/vmtooling/scrap/`.
