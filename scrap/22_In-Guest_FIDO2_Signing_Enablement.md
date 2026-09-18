---
id:
type: DAR.RESEARCH
parent: 49825
parent_ci: 49825
title: In-Guest FIDO2 Signing Enablement
status: ACTIVE
phase: DRAFT
version: "2026_09_18_15_06"
domain: INFRASTRUCTURE
created: 2026-09-18
author: operator
ci_impacted:
  - 49825
---

# In-Guest FIDO2 Signing Enablement

## 1. Problem

Node **N17** of this DAR (`03_Synthesis/01_Mikado_Graph.md`) records a synthesized gap:
the operator must be able to perform **FIDO2 closures from the guest**, and an in-guest
`ow_sign` run had failed because the guest has no FIDO2 signing path. The governed signing
flow is `python3 OW_tools/cli/ow_sign.py --ci-id <ID> --phase <PHASE>` (see the
`operator-signatures` skill), and its security property is a **physical YubiKey button
touch**; no software can substitute for it. `ow_sign` reaches the authenticator through
`fido2.hid.CtapHidDevice`, which on Linux reads the **FIDO HID interface of the key via
`/dev/hidrawN`**, and it reaches the database through the Admin-UI sidecar on
`localhost:8000`.

This research establishes what was actually missing, what was done about it, and what
remains, so that working from the guest means being able to **sign and commit**.

## 2. Findings

### 2.1 The USB path

| # | Finding | Evidence |
|:--|:--------|:---------|
| F1 | The operator key is `1050:0407` "Yubikey 4/5 OTP+U2F+CCID" on host bus 5 port 2, with three interfaces: OTP HID (iface 0), FIDO HID (iface 1), CCID (iface 2). Only the FIDO interface matters to `ow_sign`; CCID would only matter for OpenPGP/PIV. | `lsusb -d 1050:0407 -v`; host sysfs `5-2`, `5-2:1.0..1.2` |
| F2 | The `sandbox` domain had a `qemu-xhci` controller but **no USB `hostdev`**, so the guest saw only root hubs. This is the primary gap recorded by N17. | `virsh dumpxml sandbox` (no `hostdev`); guest `lsusb` showed 2 root hubs only |
| F3 | **No host root is required** to attach: user `d` is in group `libvirt`, so `virsh attach-device` works unprivileged. This keeps DAR-158 constraint RD-3 intact (agent never holds host root outside an operator window). | `id` shows `130(libvirt)`; `virsh attach-device ... --live` succeeded without sudo |
| F4 | Attaching the hostdev alone was **not sufficient**. The guest's stock Ubuntu rule set grants `TAG+="uaccess"` on the FIDO hidraw node only; `uaccess` ACLs are applied to sessions that own a seat, so the **seat-less SSH session** that drives `ow_sign` received `EACCES`. This is the non-obvious half of the gap and would have presented as "no FIDO device found". | Before fix: `PermissionError: [Errno 13]` on `/dev/hidraw1` over ssh; after fix: `crw-rw---- root plugdev` |
| F5 | Passthrough is **exclusive**: while the key is attached, the host loses its FIDO hidraw node and host applications (browser WebAuthn, `ykman`) cannot use the key. `lsusb` still lists the device on the host because qemu holds it through usbfs, so `lsusb` alone is not a reliable "host can use it" signal. | Host `/dev/hidraw4,5` (with ACLs) disappeared on attach and returned on detach |
| F6 | A **persistent** USB hostdev makes `virsh start sandbox` fail whenever the key is absent from the host bus. Transient (live) attach is therefore the correct default for a long-lived VM. | libvirt resolves the hostdev at domain start; documented in the helper header |

### 2.2 The guest software path

| # | Finding | Evidence |
|:--|:--------|:---------|
| F7 | The guest already carries the signing runtime: `python-fido2` **2.2.1** (the version `ow_sign` requires) in `~/dev_env/clones/Overwatch/.venv`, and on Linux that library uses a raw **hidraw** backend, so the `hidapi` python module is *not* required. | `.venv/bin/pip list`; `fido2/hid/__init__.py` selects the linux backend |
| F8 | After the hostdev attach and the udev fix, a full **CTAP2 `getInfo` round trip** succeeds in the guest over the same seat-less SSH path that runs `ow_sign`. This proves discovery, permissions and the HID transport without consuming a touch. | `/dev/hidraw1`, aaguid `2fc0579f-8113-47ea-b116-bb5a8db9202a`, CTAP `U2F_V2 / FIDO_2_0 / FIDO_2_1_PRE` |
| F9 | The Admin-UI sign sidecar image (`overwatch-admin-sidecar:v2026.07.31.6-ubuntu-fips`) is **already present in guest containerd**, the FIDO2 RBAC grants are **already applied** in the guest database for both `overwatch_agent` and `ow_agent`, and the `firecontrol-db-credentials` secret exists. The missing piece is only the **Deployment/Service** itself (`k8s/admin-ui-sidecar.yaml`). | `k3s ctr images ls`; grant query over `information_schema`; `kubectl get secret` |
| F10 | The manifest DSN points at `host=pgbouncer port=51729`. **No pgbouncer exists in the guest**; the guest database is `firecontrol-db:5432`, exposed on the guest host as LoadBalancer port `51728`. The DSN must be adapted to the guest topology, or pgbouncer deployed. | `kubectl get all -n overwatch` (no pgbouncer pod); service ports; `ss -ltn` |
| F11 | **Credential separation is real**: `POSTGRES_USER` is `ow_db_superuser`, and that password is rejected for `overwatch_agent` and `ow_admin_ui`. The sidecar must connect as **`overwatch_agent`** with the agent credential already held on the guest (the one `db_write.py` uses), which preserves the RFC-OW-370 / D3 containment: `audit.ow_log_signature_change` must not be executable by the agent role. | `psql` auth failure for both roles with the superuser password; grants show the agent roles hold exactly the five required objects |
| F12 | The sidecar identity contract is the `X-Forwarded-User` header; `ow_sign` supplies it from `os.getlogin()`. No ingress is needed for a `localhost:8000` call, so the deployment does not have to widen the guest network surface. | `src/admin-ui-sidecar/main.py` `get_identity`; `ow_sign.py` `request_json` |
| F13 | The **A3 signature gate** builds its protected list from the DB `signoff_required` tag plus `signature_protected` in the gate config, and blocks a commit when no signature row exists for the resolved UDRS id. **No `docs/praca` path is currently protected** (zero matches), so document commits do not consume a signature; the FIDO2 path is what protected files and phase sign-offs require. | `query_ci_tags --tag signoff_required` (0 `docs/praca` rows); `OW_tools/hooks/pre-commit-signature-gate` |
| F14 | **FUSE is disabled** in this workspace. A stale `.fuse_scope` sentinel names DAR-OW-080, and `.fuse_scope.inactive` is present, so the `/doResearch2` scope gate is inert for this DAR. Recorded so the absent lock is not mistaken for a missing step. | `cat .fuse_scope`, `cat .fuse_scope.inactive` |

### 2.3 Clone currency ("guest clone at head, fully merged")

| # | Finding | Evidence |
|:--|:--------|:---------|
| F15 | The guest `clones/Overwatch` **main is the most advanced state in the estate**: `e09c6f8cd`, **192 commits ahead of `origin/main` (`d81b6d550`) and 0 behind**, so pushing it is a fast-forward. `origin/DAR-OW-158` is already an ancestor of that main (the branch merge is local, unpublished). | `git rev-list --left-right --count HEAD...origin/main` = `192 0` |
| F16 | Other clones are stale or divergent, and this is what "fully merged" has to reconcile: the guest `Overwatch_1/2/3/4` are behind `origin` (nothing to push); the guest `Overwatch_2` `DAR-OW-158` is **65 ahead of `origin/DAR-OW-158`**; the guest `Overwatch_5` is a **divergent clone** (remote named `Overwatch`, no tracking refs) whose `DAR-OW-158` tip `783c52ba9e` is **not in main history** and whose worktree holds 20 uncommitted paths. Unmerged `origin` branches: `DAR-OW-71` (3), `DAR-OW-151` (3), `DAR-OW-157_...` (5), `RFC-WF-026` (14), `RFC-WF-027` (2), `SPR-1117` (2). | per-branch `rev-list --count`, `git branch -r --contains`, `git status` per clone |

## 3. Actions taken

### 3.1 Host (workstation)

| Path | What it is |
|:-----|:-----------|
| `~/dev_env/vmtooling/yubikey_usb_hostdev.xml` | libvirt USB hostdev definition (matched by vendor/product, `managed='yes'`), the artifact the domain is attached from |
| `~/dev_env/vmtooling/docs/yubikey-fido-passthrough.md` | the operator-facing write-up of the same evaluation, evidence and trade-offs |
| `~/dev_env/vmtooling/.gitignore` | now ignores `backups/` (local domain-XML snapshots) |
| `~/dev_env/vmtooling/backups/sandbox_domain_20260918_pre_usb.xml` | pre-change `virsh dumpxml sandbox` snapshot; deliberately **not** committed |
| `~/.local/bin/sandbox-fido` | operator command: `status`, `check`, `on`, `off`, `persist`, `unpersist`; `status` reports host-side availability from the host FIDO hidraw node, not `lsusb` |
| `~/.bashrc` | comment block next to the `sandbox()` alias pointing at the command and the doc |

The host work was committed to the **`vmtooling`** repository as
`47aee40 Add YubiKey FIDO2 USB passthrough for the sandbox VM (DAR-OW-158/N17 Part A)`
(3 files, +151 lines). At the time of writing that commit is **1 commit ahead of
`origin/main` and not yet pushed**.

### 3.2 Guest

| Action | Detail |
|:-------|:-------|
| Live USB attach | `virsh attach-device sandbox .../yubikey_usb_hostdev.xml --live`; the domain now carries the hostdev and the guest enumerates the key |
| Guest udev rule | `/etc/udev/rules.d/70-yubikey-fido.rules` grants group `plugdev` read/write on the **FIDO** hidraw node only (`ENV{ID_FIDO_TOKEN}=="1"`), leaving the OTP/keyboard interface root-only. This is the fix for F4 and it is what makes the seat-less SSH path work. |
| Verification | `sandbox-fido status` (host/guest visibility) and `sandbox-fido check` (in-guest CTAP2 `getInfo`). The `off`/`on` round trip confirmed the key returns to the host when detached. |

## 4. Implications

1. **N17 Part A is complete and verified.** The USB half of the gap is closed: the key can
   be handed to the guest on demand, is readable by the session that runs `ow_sign`, and
   the guest can drive a full CTAP2 conversation with it.
2. **N17 Part B is the remaining blocker**, and it is smaller than recorded: the image,
   the RBAC grants and the secret already exist in the guest. What is needed is the
   Deployment/Service, with a DSN corrected for the guest topology (F10) and the agent
   credential (F11). Until it exists, `ow_sign` fails at `localhost:8000` **before** it can
   ask for a touch.
3. **"Sign and commit from the guest" therefore resolves to:** Part B deployment, then a
   real `ow_sign` run with one button touch. Committing a *protected* file additionally
   requires that recorded signature; committing ordinary documents does not (F13).
4. **The clone estate needs a deliberate consolidation**, because the guest main is ahead
   of origin while other clones diverge (F15, F16). The safe sequence is: push the
   fast-forward main, then reconcile the divergent clones branch by branch, escalating any
   conflict to the operator rather than resolving it silently.
5. **Passthrough is a custody transfer** (F5): the operator should read `sandbox-fido on`
   as "the workstation loses its key until I run `sandbox-fido off`".

## 5. Verification

```text
# host, before: no hostdev, guest saw root hubs only
virsh dumpxml sandbox | grep -c hostdev            -> 0
ssh d@192.168.122.55 lsusb                          -> root hubs only

# after: sandbox-fido status
key plugged into host   : yes
attached to sandbox     : yes (live)
  in persistent config  : no (VM boots without the key)
host apps can use key   : no (handed over to the guest)
guest sees the key      : yes
    crw------- 1 root root    240, 0   /dev/hidraw0   (OTP HID, not granted)
    crw-rw---- 1 root plugdev 240, 1   /dev/hidraw1   (FIDO HID)

# after: sandbox-fido check  (in-guest, over the seat-less ssh path)
FIDO transport OK: /dev/hidraw1 aaguid 2fc0579f-8113-47ea-b116-bb5a8db9202a
CTAP versions: [U2F_V2, FIDO_2_0, FIDO_2_1_PRE]

# after: detach returns the key to the host
sandbox-fido off  -> host FIDO hidraw present again, guest no longer sees the key

# remaining blocker, unchanged at time of writing
curl -s -o /dev/null -w %{http_code} -X POST http://localhost:8000/api/v1/auth/nonce  -> connection refused
```

## 6. Research Phase Decisions

| # | Decision | Rationale | Impact | Date |
|:--|:---------|:----------|:-------|:-----|
| RD-14 | YubiKey passthrough is **live/transient by default** (`sandbox-fido on`/`off`); persistent domain config only on explicit operator request | A persistent USB hostdev makes `virsh start sandbox` fail whenever the key is absent (F6), and a long-lived VM would otherwise hold the operator key permanently, breaking host-side WebAuthn (F5) | The domain stays bootable without the key; custody of the key is an explicit operator action |
| RD-15 | The in-guest sidecar must connect as **`overwatch_agent`** using the agent credential, never as the database superuser | The superuser password is rejected for the agent roles anyway (F11), and connecting as superuser would defeat the RFC-OW-370 / D3 containment that keeps signature logging out of agent reach | Sidecar deployment must carry the agent credential as a secret; the FIDO2 grant set already present is exactly what the flow needs |
| RD-16 | The sidecar DSN is corrected for the guest topology (**guest DB service, no pgbouncer**) instead of mirroring the host manifest verbatim | The guest runs no pgbouncer; the host-era DSN targets `pgbouncer:51729`, which cannot resolve in the guest (F10) | The deployment deviates from the committed manifest in exactly one field; recorded here so the deviation is intentional and auditable |
