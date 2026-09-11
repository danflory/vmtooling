---
title: "VM Content Boundary: What Must Be Inside vs. Read-Only-Referenced"
author: Dan Flory / Overwatch agent
date: 2026-09-11
status: DRAFT
domain: INFRASTRUCTURE
related:
  - DAR-OW-158 (Disposable VM Sandbox Isolation)
  - vmtooling/docs/backup-design.md
---

# VM Content Boundary: What Must Be Inside vs. Read-Only-Referenced

A decision-support paper for DAR-OW-158: which content physically lives inside
the disposable VM, and which stays on the host and is referenced read-only
through the host/VM filesystem bridge.

## 1. The enabling question

The operator asked: *"Will I have access from the VM to host files for
read-only work? I don't need any of these non-personal development clones in
it if I can reference them."*

**Answer: Yes.** KVM/QEMU exposes host directories into the guest via
**virtiofs**, the modern shared-filesystem. A host directory can be mounted
in the VM **read-only** (`-o ro`), giving the guest full read access to the
host tree at near-native speed with no write path and no extra daemons.
Alternatives (9p, Samba/NFS, sshfs) are slower or heavier; virtiofs is the
recommended default.

This directly enables the content-boundary model below: personal content and
active work live in the VM; the large set of non-personal dev clones stays on
the host, visible to the VM read-only.

## 2. Why this matters (measured)

The VM does not need to *contain* everything it can *reach*. Host `dev_env`
is **84.4 GB** (measured), of which **73% is incompressible** git packs and
native binaries, and much of it is **duplicated** (the same git pack
`pack-677af003...` exists in 4+ Overwatch clones). Copying all of that into
the VM:

- triples-or-worse the VM disk, and
- drags nightly backups (see backup-design.md: whole-image compression is
  ~1.3x anyway), and
- bloats snapshots and restore times.

If the VM can read host clones in place, most of that 84 GB never enters the
VM disk or the backup set.

## 3. The boundary model

Three tiers:

### Tier 1 — MUST be inside the VM (authoritative, writable)

The VM is the new workstation for these; the host keeps no authoritative copy:

| Content | Why |
|:--------|:----|
| `~/Documents/` (incl. `Private_research/theory/`) | Operator decision 2026-09-11 (DAR-OW-158 RD-5); personal, high-value |
| Active Overwatch clone(s) being worked (e.g. Overwatch_5 / DAR branches) | Writable working tree; git remote is the sync channel |
| Postgres (firecontrol + others) | Stateful; VM root manages it |
| jcode config / memory / sessions | The agent's own state |
| Gravitas + its data | The brutal GPU workload being contained |
| The VM itself (OS, hypervisor tooling, backup scripts) | — |

### Tier 2 — Host-resident, read-only-referenced (do NOT copy into VM)

Non-personal development clones and bulk code that the VM can reach via
virtiofs read-only. Operator's question targets exactly this tier:

| Host path | Notes |
|:----------|:------|
| `dev_env/Overwatch`, `Overwatch_1..4` | Clone duplicates; active one (Overwatch_5) is Tier 1; the rest are reference/backups |
| `dev_env/Cline` (5 GB) | Non-personal upstream-tracking clone |
| `dev_env/anki`, `txtai`, `unstructured`, `crawlee-python`, `foam`, etc. | Reference/experiment repos |
| `dev_env/private_projects_SECRET_LOCAL` (8.1 GB) | Sensitive; keep host-side, do not ship into VM |
| `dev_env/*/node_modules`, `.git` objects | Bulk/incompressible; never copied |
| `Gravitas`'s repo history, `GSBE`, other governed projects | Read-only reference unless actively worked |

### Tier 3 — NEVER inside the VM (host-only secrets/authority)

| Content | Why |
|:--------|:----|
| Host SSH keys / `~/.ssh` | VM should not hold host identity |
| Host `sudo` escrow (`/etc/sudoers.d/d-admin`) | VM root is separate; host elevation is operator-only |
| Host GPG/cloud tokens used for host operations | Least privilege; grant only what VM work needs |
| k3s / kubeconfig host control (`/etc/rancher/k3s/k3s.yaml`) | Host cluster is not the VM's to manage |

## 4. Migration implication

With virtiofs, "migration" is not "copy everything":

1. **Copy Tier 1** into the VM (Documents 442 MB, active clone, DB dumps, config).
2. **Do not copy Tier 2.** Mount `dev_env` (or per-repo subtrees) read-only
   into the VM at e.g. `/mnt/host/dev_env`.
3. **Verify** the VM can run Overwatch tooling against the read-only mount
   where reads are all that's needed; any clone the operator actively works
   moves up to Tier 1 (writable in-VM copy) at that point.
4. **Secrets stay put** (Tier 3) on the host; the VM gets only what its work
   requires.

This shrinks the VM disk from "84 GB dev_env" to roughly Tier 1 only
(Documents 442 MB + active clone + OS + DB), making daily backups tiny and
restores fast — reinforcing the disposable posture.

## 5. Open questions / decisions

- **Which exact subtrees** get read-only-mounted: the whole `dev_env`, or
  per-repo? (Recommend per-repo or a single read-only `dev_env` mount;
  finer control later.)
- **Sync direction**: when a Tier 2 repo is promoted to Tier 1 (operator
  starts actively working it), what is the copy-in and reverse-sync policy?
- **Read-only enforcement**: virtiofs `-o ro` is the guard; also confirm the
  guest mount is set noexec/noauto where relevant.
- **Host visibility into the VM**: symmetric question — does the host need to
  read VM files (e.g., for backups)? (Yes for snapshots; the host-side
  snapshot mechanism covers that without a filesystem bridge.)

## 6. Relation to DAR-OW-158

- Updates DAR-OW-158 research with RD-6 (proposed): *Tier 2 non-personal
  clones stay host-resident and are read-only-referenced via virtiofs.*
- Adds a gap closure to DAR-OW-158 G-x: *how to expose host clones to the VM*
  (answer: virtiofs read-only mount).
- Shapes Action Plan A7 (migration) to "copy Tier 1, mount Tier 2, leave
  Tier 3."
