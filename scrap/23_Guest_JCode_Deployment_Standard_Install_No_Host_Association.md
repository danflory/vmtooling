---
id:
type: DAR.RESEARCH
parent: 49825
parent_ci: 49825
title: Guest JCode Deployment Standard Install No Host Association
status: ACTIVE
phase: DRAFT
version: "2026_09_18_15_45"
domain: INFRASTRUCTURE
created: 2026-09-18
author: operator
ci_impacted:
  - 49825
---

# Guest JCode Deployment Standard Install No Host Association

## 1. Problem

The sandbox must run jcode as a **standard, self-contained install**: its home is
the guest's own `~/.jcode` on the guest disk, and **nothing about it is associated
with the host** — no host-SSD home, no host-backed virtiofs share, no `JCODE_HOME`
redirection into a host directory.

Node **N11** violated that requirement. It provisioned a dedicated jcode sandbox
home on the host SSD and exposed it into the guest as a writable virtiofs share, so
that jcode state would outlive a disposable VM. The idea did not work out at all; it
was reverted on 2026-09-16/17, and the operator reports that it caused two days of
confusion. This research records the error fully, the requirement it violated, and
the residue that still contradicts the requirement.

The host's own jcode home on the host SSD is **not** in scope and is **not** a
defect: it is deliberate and working well. The error was extending a host-side
storage choice into the guest, where it does not apply.

## 2. Requirement (operator, 2026-09-18)

- jcode in the guest is a normal, self-contained install.
- Its home is the guest's own `~/.jcode`, on the guest disk.
- It is **not associated with the host in any way**.
- When state must move between host and guest, it moves by an explicit **snapshot
  sync** (see `21_JCode_Config_State_Sync.md`), never by a live shared mount.

## 3. Findings

| # | Finding | Evidence |
|:--|:--------|:---------|
| F1 | **The N11 design.** The sandbox domain was given a fourth virtiofs device, target `vm_sandbox_jcode` (read-write), backed by `/var/lib/libvirt/virtiofs/vm_sandbox_jcode`, itself a bind of `/data/vm-sandbox/jcode-home` on the SSD (`/dev/sdb1`). The guest saw it as `/mnt/vm-sandbox-jcode`. | `virsh dumpxml sandbox` filesystem device; host `findmnt` shows `/dev/sdb1[/vm-sandbox/jcode-home]`; staged device XML `~/n11_jcode_sandbox_device.xml` on the host |
| F2 | **The guest was pointed at it by environment.** `~/.profile` carried `JCODE_HOME=/mnt/vm-sandbox-jcode`; it now carries a revert note: "N10 REVERT 2026-09-16: normal self-contained install (no host-SSD home). Was: JCODE_HOME=/mnt/vm-sandbox-jcode". The revert also left `*.bak.20260916-n10-revert` artifacts behind. | `~/.profile` in the guest |
| F3 | **The requirement is already satisfied in practice, but the wiring was never removed.** The guest's live `~/.jcode` is a local directory on `/dev/vda2`, and the guest's running jcode processes use it. What still contradicts the requirement is the leftover host association: the domain still exports `vm_sandbox_jcode` **and** `vm_sessions`; the guest still has an **ad-hoc** read-write mount of `/mnt/vm-sandbox-jcode` (not in `/etc/fstab`, so it vanishes on reboot while the domain keeps exporting it) holding stale 15–16 Sep content (96 MB of backing); `vm_sessions` is exported by the domain but never mounted in the guest at all (732 KB of backing); `/var/lib/libvirt/virtiofs/jcode_state` exists on the host but is not a mountpoint and has no fstab bind. | Guest `mount`, `ls -la /mnt/vm-sandbox-jcode`, guest `/etc/fstab`, host `findmnt`, host `/etc/fstab` |
| F4 | **Failure mode.** For a period two plausible jcode homes existed simultaneously — the host-SSD share and the guest-local directory — with neither marked authoritative and no fstab entry to disambiguate. The operator reports two days lost to the resulting confusion. This is the same class of defect as the vestigial native Postgres removed earlier the same day: two plausible stores, one of them stale, and a reader with no way to tell which is real. | Operator statement; measured state above |
| F5 | **Reversal trail.** `14_JCode_Home_On_Host_SSD.md` is marked WITHDRAWN, N10 is SUPERSEDED, and `21_JCode_Config_State_Sync.md` records both the supersession and the snapshot-sync successor. The graph (`03_Synthesis/01_Mikado_Graph.md`) reflects the supersession. | Those documents |
| F6 | **The host half is correct.** The host's own `~/.jcode` is a bind of `/data/jcode-home` (1.4 GB on `/dev/sdb1`) and works well. It is the host's jcode, not the guest's, so it does not associate the guest with the host. No change is required or wanted there. | Host `findmnt`, host `/etc/fstab`, operator statement |

## 4. Actions

Unwire the guest's host association, and leave everything else alone:

| Action | Detail |
|:-------|:-------|
| Domain export | Detach the `vm_sandbox_jcode` filesystem device from the `sandbox` domain (persistent config; live where libvirt supports it). |
| Guest mount | Unmount `/mnt/vm-sandbox-jcode` in the guest. Nothing has it open, and the guest's jcode does not use it. |
| Host binds and fstab | Remove the `vm_sandbox_jcode` and `vm_sessions` bind entries and their `/etc/fstab` lines (operator sudo window). |
| Backing directories | Remove the now-unreferenced `/data/vm-sandbox/jcode-home`, `/data/jcode-vm-sessions` and `/var/lib/libvirt/virtiofs/jcode_state`. |
| Untouched | `host_dev_env` (read-only, RD-6) and `vm_backups` (read-write) are unrelated to jcode and stay. The host's own `~/.jcode` bind stays. |

## 5. Implications

1. **One jcode home in the guest, on the guest disk.** After unwiring, the guest's
   only jcode home is `/home/d/.jcode` on `/dev/vda2`, which is what the requirement
   asks for and what the guest already runs today.
2. **A withdrawn design must not be left half-wired.** The residue was worse than
   either extreme: the export and the ad-hoc mount survived the revert, so the
   abandoned mechanism stayed reachable and plausible while the documentation said
   it was abandoned.
3. **State movement is a sync, not a mount.** Any future need to align host and
   guest jcode state goes through the snapshot path in research 21 (one-way,
   host → guest, dry-run by default), which cannot create a second live home.
4. **Scope discipline.** The host's jcode storage is a deliberate, working choice;
   the guest's is not. The two must not be conflated again, which is precisely how
   this error arose.

## 6. Verification

```text
# guest: the home that is actually used
readlink -f /home/d/.jcode            -> /home/d/.jcode
df -h /home/d/.jcode | tail -1        -> /dev/vda2   158G  120G   32G  80% /
pgrep -a jcode                        -> jcode ... serve  (running from the local home)

# guest: the residue that must go
mount | grep virtiofs                 -> host_dev_env (ro), vm_backups (rw), vm_sandbox_jcode (rw, ad-hoc)
grep -n virtiofs /etc/fstab           -> host_dev_env, vm_backups only  (no jcode share)

# host: the export and its backing
virsh dumpxml sandbox | grep -c vm_sandbox_jcode   -> 1   (must become 0)
findmnt -no SOURCE /var/lib/libvirt/virtiofs/vm_sandbox_jcode -> /dev/sdb1[/vm-sandbox/jcode-home]
findmnt -no SOURCE /home/d/.jcode                  -> /dev/sdb1[/jcode-home]   (host home, unchanged, correct)
```

## 7. Research Phase Decisions

| # | Decision | Rationale | Impact | Date |
|:--|:---------|:----------|:-------|:-----|
| RD-17 | jcode in the sandbox is a **standard self-contained install** on the guest's own `~/.jcode` on the guest disk: no host-SSD home, no host-backed share, no `JCODE_HOME` redirection, no association with the host | The N11 host-SSD home produced two plausible jcode homes and two days of confusion (F4); the operator's requirement is a normal install | Guest jcode deployment is fully local; host/guest state alignment uses the snapshot sync only |
| RD-18 | The withdrawn N11 wiring is **removed**, not retained: domain export, guest mount, host binds, fstab lines and backing directories all go | A withdrawn design left half-wired keeps a stale mechanism reachable and plausible (F3, implication 2) | The guest ends with exactly one jcode home; the host's own home is untouched |
| RD-19 | The host's own `~/.jcode` on the host SSD **stays as it is** | It is deliberate and working; it does not associate the guest with the host (F6) | The fix is strictly guest-scoped; no host jcode migration |
