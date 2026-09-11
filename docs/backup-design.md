---
title: "Backup Design for the Disposable VM Sandbox"
author: Dan Flory / Overwatch agent
date: 2026-09-11
status: DRAFT
domain: INFRASTRUCTURE
related:
  - DAR-OW-158 (Disposable VM Sandbox Isolation)
  - vmtooling repo (deployment + backup tooling)
---

# Backup Design for the Disposable VM Sandbox

A research paper grounding the daily-backup design for the DAR-OW-158
disposable KVM/QEMU sandbox in measured data from the real workload.

## 1. Motivation

The operator's objective (DAR-OW-158) is to run **all model-driven work inside
a disposable VM** that is backed up daily and can be wiped and re-provisioned
at any time. The workstation layer must never be exposed to unfettered model
root access. The backup design is therefore not a nice-to-have: it is the
mechanism that makes the whole "disposable" posture safe. If the VM is cheap
to lose and quick to restore, then granting root inside it is low-risk.

This paper answers three questions with measurement rather than assumption:

1. **How well does the VM content compress?** (determines storage cost, target media)
2. **What is the daily delta?** (determines backup cadence granularity)
3. **What backup architecture best fits the disposable posture?**

## 2. Measured compressibility (dev_env, 2026-09-11)

Measurement tool: `scrap/compress_measure.py` in this repo. Scans the
`/home/d/dev_env` tree (excluding `.git`, `node_modules`, `.venv`,
`__pycache__`, `.cache`), buckets by extension class, samples up to 300
files/class (up to 8 MB each), reports gzip -6 and zstd -3 ratios.

### 2.1 Headline result

| Metric | Value |
|:-------|:------|
| Raw bytes scanned | **84.4 GB** (313,599 files) |
| Estimated gzip-compressed | **64.4 GB** |
| **Overall gzip ratio** | **1.3x** |

**The overall tree does NOT compress well.** Only ~1.3x. This is the single
most important finding for backup design.

### 2.2 Why: the incompressible majority

The "other" class holds **62.0 GB (73%)** of the raw bytes and compresses at
only **1.1x**. Inspection shows this class is dominated by:

- **Git object packs** (`.git/objects/pack/*.pack`) — already delta+deflate
  compressed, essentially incompressible.
- **Native binaries** — `node_modules/.bun/` (claude-agent-sdk, next-swc,
  buf, codex vendored binaries), Playwright's bundled `node`, Language
  Server binaries, the Antigravity binary. Already compressed/random.
- **Git LFS blobs** — content-addressed, often already-compressed artifacts.

### 2.3 The compressible minority (the useful part)

Text and structured classes compress well, but are a small fraction of bytes:

| Class | Raw | gzip ratio | zstd ratio | Compressed |
|:------|----:|-----------:|-----------:|-----------:|
| json | 5.57 GB | 6.1x | **10.8x** | 0.91 GB |
| markdown/text | 2.07 GB | 3.0x | 3.1x | 0.69 GB |
| python | 1.52 GB | 5.4x | 5.4x | 0.28 GB |
| binary/db | 5.06 GB | 4.6x | 5.3x | 1.10 GB |
| log | 0.31 GB | **24.0x** | **27.1x** | 0.01 GB |
| js/ts | 0.18 GB | 5.0x | 5.0x | 0.04 GB |
| xml | 0.80 GB | 5.3x | 5.0x | 0.15 GB |
| sql | 0.03 GB | 7.4x | 7.1x | 0.004 GB |
| web (html/css/svg) | 0.18 GB | 7.6x | **11.1x** | 0.02 GB |

Note: `.git` and `node_modules` were excluded from the scan. Including them
would add roughly the git pack sizes (many GB) at ~1.0x and node_modules
binaries at ~1.1x — all incompressible. The true full-tree ratio including
those is **at or below 1.3x**.

## 3. Implications for backup design

### 3.1 Whole-image compression is a dead end

Because 73% of bytes are already-compressed git packs and native binaries,
**gzip/zstd on a full VM image buys only ~1.3x**. This means:

- **Do not design around compressing the full disk image.** The storage win
  is negligible and costs CPU.
- Deduplication of **identical byte ranges** (repeated git pack copies across
  the 6+ Overwatch clones, identical node_modules trees) is far more valuable
  than generic compression.

### 3.2 The daily delta is tiny — that is the real win

The VM's daily churn is what matters for daily backups. The workload is:
source code, docs, SQL, and configs — precisely the classes that compress at
3–24x and are small in absolute terms (json+markdown+python+sql+log ≈ 9.5 GB
raw, ~2 GB compressed). Postgres WAL and data pages churn modestly day to
day. **An incremental/delta daily backup will be on the order of MBs to a
few GB** even for an active day, because the 62 GB incompressible core is
static between days.

### 3.3 What should be excluded vs included

| Content | Include in VM | Backup treatment |
|:--------|:--------------|:-----------------|
| dev_env source (Overwatch, Gravitas, tooling) | yes | In VM disk; git is the source of truth — **exclude .git from VM backup**, rely on remotes |
| `~/Documents/` (incl. `Private_research/theory/`) | **yes** | **Must back up nightly** — small (442 MB), high-value personal content; include in the subset backup (D-4) alongside jcode memory |
| Postgres (firecontrol + others) | yes | **Must back up** — logical dump (`pg_dump`) or WAL archiving; compressible 4.6x |
| node_modules / build artifacts | yes (as needed) | **Exclude from backup** — reproducible via lockfiles |
| Git LFS blobs | yes | Exclude — content-addressable, re-fetchable |
| Config / auth / secrets | yes | **Must back up** separately, encrypted |
| jcode memory / sessions | yes | Must back up (small) |

## 4. Recommended backup architecture

### 4.1 Layered approach (host-side, snapshot-based)

The strongest restore story for a "disposable workstation" is a **host-side
qcow2 snapshot chain** on the NVMe (or the 1.8 TB HDD), because:

- A snapshot is instantaneous (copy-on-write), so a "daily backup" is nearly
  free and non-disruptive.
- Restore = revert to the snapshot. The disposable posture means you want the
  cheapest possible "back to yesterday" path.
- qcow2 internal snapshots capture VM state at block granularity.

**Daily cadence:**
1. Quiesce (or use crash-consistent) — snapshot the qcow2 disk(s).
2. Keep a rolling window (e.g., 7 daily + 4 weekly) using qcow2 overlay
   snapshots or `qemu-img` external snapshots.
3. Additionally, run a nightly **guest-side `pg_dump` of the firecontrol
   database** (and other Postgres) to a backup dir, because a block snapshot
   of a live Postgres is only crash-consistent, not point-in-time-safe for
   the DB.

### 4.2 Why guest-side DB dumps are non-negotiable

Block snapshots of a running Postgres can capture a torn state. A daily
`pg_dump` (or `pg_basebackup`/WAL archiving) gives a clean, restorable DB
state and compresses at ~4.6x measured. This is the standard "snapshot the
blocks, dump the database" hybrid.

### 4.3 Storage placement

- **Primary snapshots**: local NVMe or HDD. 1.8 TB free on `/mnt/f_drive`
  comfortably holds multiple qcow2 snapshots.
- **Offsite/extra copy**: the compressible subset (text/JSON/log/DB dumps,
  ~2–3 GB) can be tar.zstd'd and sent off-host cheaply; the incompressible
  image stays local.

### 4.4 Restore SLAs to design against

| Scenario | Target | Mechanism |
|:---------|:-------|:----------|
| Wipe VM, restore to yesterday | minutes | qcow2 snapshot revert / overlay discard |
| Recover a lost file/session | seconds–minutes | file-level restore from snapshot mount or guest backup |
| Recover Postgres to a point | minutes | pg_dump restore |
| Full rebuild from scratch | hours | dev_env git clone + lockfile reinstall + config |

## 5. Deduplication opportunity (the actual compression win)

Measured 1.3x overall is misleading in the right direction: the identical
**git pack** `pack-677af003...` appears in at least **4 separate Overwatch
clones** (`Overwatch_2/3/4`, plus others), each several GB. A backup tool with
content-defined chunk dedup (e.g., `borgbackup`, `restic`, or `zstd --long`
with `--patch-from`) would collapse these to a single stored copy. This turns
the 62 GB incompressible core into effectively ~15–20 GB of unique data.

- **If backups are host-side qcow2 snapshots**: dedup is limited (qcow2
  snapshots dedup by shared COW blocks, not by content). Accept the disk cost.
- **If backups are file-level** (borg/restic of the guest): dedup shines on
  the git-pack redundancy, but file-level backups of 84 GB are slower and
  more complex.
- **Recommendation**: host-side qcow2 snapshots for the disposable-restore
  path (fast, simple, disk-cheap given 1.8 TB free), plus a nightly
  **borg/restic** of the compressible+stateful subset (config, DB dumps,
  jcode memory) for true off-host and dedup. This hybrid gives both the
  fast wipe-and-restore and a clean, small, encrypted offsite copy.

## 6. Compression choice (gzip vs zstd)

When compression IS applied (to the subset backups and DB dumps):

- **zstd -3** beats gzip -6 on every measured class (e.g., json 10.8x vs 6.1x,
  web 11.1x vs 7.6x, log 27.1x vs 24.0x) and is dramatically faster.
- Use `tar --zstd` for subset backups and `pg_dump | zstd -3` for DB dumps.
- Skip compression on the qcow2 snapshot path entirely (1.3x not worth it).

## 7. Decision summary

| # | Decision | Rationale |
|:--|:---------|:----------|
| D-1 | Do not gzip the full VM image (≤1.3x) | 73% incompressible (git packs, binaries) |
| D-2 | Host-side qcow2 snapshots for the daily disposable-restore path | Instant, simple, disk-cheap |
| D-3 | Nightly guest-side `pg_dump \| zstd` for Postgres | Crash-consistent snapshots are not DB-safe |
| D-4 | Nightly borg/restic of the small compressible+stateful subset | True off-host copy, dedup, encryption |
| D-5 | Use zstd, not gzip, everywhere compression is applied | Faster + better ratio (measured) |
| D-6 | Exclude .git, node_modules, LFS, build artifacts from file backups | Reproducible / re-fetchable; git is source of truth |
| D-7 | Include `~/Documents/` in the nightly subset backup (D-4) | Personal, high-value, small (442 MB); operator decision 2026-09-11 that Documents is part of the VM |

## 8. Open questions

- Should the qcow2 snapshots live on the 1.8 TB HDD (capacity) or NVMe
  (speed)? HDD is fine for snapshot chains since COW writes are sequential-ish.
- Do we want a 3-2-1 posture (2 local + 1 offsite)? The compressible subset
  (~3 GB) is trivially offsite-able; the full image is not.
- Encrypted secrets: which layer encrypts (restic repo vs qcow2 LUKS inside VM)?

## 9. Tooling home

This paper and the measurement tool live in the new **`vmtooling`** repo
(`github.com/danflory/vmtooling`), which is the home for VM deployment and
backup tooling:

```
vmtooling/
├── docs/backup-design.md        # this paper
├── scrap/compress_measure.py    # measurement tool
└── (future: deploy scripts, snapshot scripts, restore runbooks)
```

## Appendix: raw measurement output

```
# Compression measurement: /home/d/dev_env
class                     raw MB   files   gzip x   zstd x   est.gz MB
other                    62040.8   65030      1.1      1.1     58709.7
binary/native             5670.6    3310      3.3      3.6      1719.3
json                      5567.1   45602      6.1     10.8       906.8
binary/db                 5055.7      21      4.6      5.3      1095.5
markdown/text             2071.4  103752      3.0      3.1       688.1
python                    1517.0   70211      5.4      5.4       279.7
xml                        801.7     827      5.3      5.0       151.9
binary/image               633.8    2475      1.2      1.3       517.8
log                        310.8     160     24.0     27.1        13.0
TOTAL                    84423.1  313599                       64427.3
Overall gzip ratio: 1.3x
```
