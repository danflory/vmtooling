---
title: "VM Manager Selection for the Disposable Sandbox"
author: Dan Flory / Overwatch agent
date: 2026-09-11
status: DRAFT
domain: INFRASTRUCTURE
related:
  - DAR-OW-158 (Disposable VM Sandbox Isolation)
  - vmtooling/docs/backup-design.md
  - vmtooling/docs/vm-content-boundary.md
---

# VM Manager Selection for the Disposable Sandbox

Which hypervisor / VM manager do we build the DAR-OW-158 disposable sandbox on?
This paper enumerates the viable free options for Ubuntu and recommends one,
against the operator's explicit requirements.

## 1. Requirements (from the operator)

| # | Requirement | Meaning |
|:--|:------------|:--------|
| R-1 | Docker-capable | The VM must run Docker workloads |
| R-2 | Heavy k3s, many pods | Must comfortably host k3s Kubernetes with many pods (the host already runs k3s with dozens of pod sandboxes) |
| R-3 | VERY stable — no shaky/new foundation | Battle-tested, mature, boring tech. No bleeding-edge or young projects |
| R-4 | Free | No license cost (base product) |
| R-5 | Ubuntu-friendly | First-class support on Ubuntu (host is Ubuntu) |

## 2. The candidate set: how many choices?

For **free, Ubuntu-friendly, stable** hypervisors, there are exactly **four**
real candidates. Everything else is disqualified outright:

| # | Candidate | Type | Disqualifier or status |
|:--|:----------|:-----|:------------------------|
| 1 | **KVM/QEMU + libvirt** (virt-manager / virsh) | Type-1 hypervisor, OS-native | ✔ In contention |
| 2 | **Proxmox VE** | Debian-based hypervisor distro | In contention, but replaces the host OS (not Ubuntu) |
| 3 | **VirtualBox** | Type-2 hypervisor (Oracle) | In contention, but weak for heavy k3s/GPU passthrough |
| 4 | **Xen / XCP-ng** | Type-1 hypervisor | Ubuntu host support is poor; heavyweight, niche |

**Disqualified without further thought:**
- **VMware (ESXi/Workstation)** — not free (Broadcom licensing); not Ubuntu-native.
- **Hyper-V** — Windows-only.
- **GNOME Boxes** — a front-end to libvirt, not a separate choice.
- **LXD/Incus** — container-first; system containers, not a KVM-style VM manager;
  not the right fit for "VM with GPU passthrough + daily qcow2 snapshots."
- **Bare qemu command line** — not a "manager"; no management layer.

So the honest answer to "how many choices?" is **four contenders, two of which
are genuinely serious for this use case** (libvirt/KVM and Proxmox), with
VirtualBox a distant third and Xen out.

## 3. Requirements scoring

| Requirement | libvirt/KVM | Proxmox VE | VirtualBox | Xen/XCP-ng |
|:------------|:-----------:|:----------:|:----------:|:----------:|
| R-1 Docker | ✅ native | ✅ native (LXC+VMs) | ⚠️ works but heavy | ✅ |
| R-2 heavy k3s, many pods | ✅ excellent (this host already runs k3s under it) | ✅ excellent | ❌ poor for many-pod k8s | ✅ good |
| R-3 very stable / mature | ✅ 20+ yr production lineage (Linux kernel module) | ✅ mature, Debian-based | ⚠️ mature but type-2 overhead | ✅ mature |
| R-4 free | ✅ (GPL) | ✅ (AGPL, no support fee required) | ✅ base pack GPL v2 | ✅ (XCP-ng free) |
| R-5 Ubuntu-friendly | ✅ first-class (kernel-included) | ❌ replaces Ubuntu host (its own distro) | ✅ cross-platform | ⚠️ host support poor |
| GPU passthrough (RD-1) | ✅ VFIO, standard | ✅ VFIO | ❌ not officially supported | ✅ VFIO |
| virtiofs (RD-6) | ✅ native | ✅ native | ❌ no | ⚠️ limited |
| qcow2 snapshots for daily backup | ✅ native | ✅ native (with own backup) | ❌ own format | ⚠️ LVM/zvol |
| **TOTAL fit** | **Best** | **Good (but changes host OS)** | **Poor for this use** | **Poor for this host** |

## 4. Recommendation: KVM/QEMU + libvirt (virt-manager + virsh)

**Winner: libvirt on top of KVM/QEMU**, driven by the GUI (virt-manager) for
interactive work and the CLI (`virsh`) plus our `vmtooling` scripts for
automation.

Why it wins on every requirement:

1. **R-3 stability**: KVM has been in the Linux kernel since 2007 and is the
   production hypervisor underlying most public cloud (OpenStack, AWS
   Nitro-adjacent, Google's compute). It is the definition of "boring,
   battle-tested, not new." The host already runs k3s with dozens of pods
   directly on this kernel; KVM is the same kernel module.
2. **R-2 heavy k3s**: libvirt/KVM is precisely what runs k3s clusters in
   production. The VM will host k3s + many pods with full resource
   partitioning. Nested virtualization (KVM-in-KVM) works if ever needed.
3. **R-1 Docker**: any modern Linux VM runs Docker natively; libvirt imposes
   no container restrictions. k3s inside the VM uses its bundled containerd
   exactly as the host does today.
4. **R-5 Ubuntu**: KVM is kernel-included on Ubuntu, install is
   `apt install qemu-kvm libvirt-daemon-system virt-manager`, and it is the
   default assumed by Ubuntu's own virtualization docs.
5. **R-4 free**: GPL, no cost, no license server.
6. **Feature fit with the existing plan**: native virtiofs (RD-6 read-only
   host `dev_env/`), native VFIO GPU passthrough (RD-1 TITAN to VM), native
   qcow2 snapshot chains (daily backup design), NAT networking (outbound
   works, zero config).

### Why not Proxmox (the closest runner-up)

Proxmox is genuinely excellent and would handle all requirements, but it is a
**full Debian-based hypervisor OS** — choosing it means replacing the Ubuntu
workstation host, not running a manager *on* it. That conflicts with:
- keeping the current Ubuntu host's GUI/4-monitor workstation role,
- the operator's "new workstation mounted into the hardware" framing where
  the VM is a guest of this host,
- not wanting to migrate the entire host OS as part of standing up the sandbox.

If we were building a dedicated, headless server room box, Proxmox would be
the strong pick. For a workstation that runs a disposable VM, libvirt/KVM is
the right fit.

### Why not VirtualBox

Type-2 overhead, weak for many-pod k3s, no official GPU passthrough (breaks
RD-1), no virtiofs (breaks RD-6), and its own snapshot format (breaks the
qcow2 backup design). Fine for casual desktop VMs; wrong tool here.

## 5. The stack (final)

```
┌─ GUI for the operator ──> virt-manager
├─ CLI/automation ────────> virsh + vmtooling scripts (snapshot, deploy)
├─ management layer ──────> libvirt (daemon, domain XML, storage/net pools)
├─ hypervisor ────────────> QEMU/KVM (kernel module + qemu-system-x86_64)
└─ hardware ──────────────> this workstation (12 cores, 45 GB RAM, NVMe/SSD/HDD)
```

## 6. Decisions recorded

| # | Decision | Rationale |
|:--|:---------|:----------|
| D-1 | Use **libvirt + virt-manager/virsh** on KVM/QEMU | Wins every requirement (stable, free, Ubuntu-native, docker/k3s-ready, virtiofs+VFIO+qcow2 fit) |
| D-2 | Do not use Proxmox | Would replace the Ubuntu host OS; conflicts with workstation framing |
| D-3 | Do not use VirtualBox / Xen | VirtualBox lacks passthrough+virtiofs+qcow2; Xen poor on Ubuntu |
| D-4 | Package set: `qemu-kvm libvirt-daemon-system virt-manager` (plus `bridge-utils` if bridge mode needed) | Standard Ubuntu KVM stack |

## 7. Open items

- Confirm exact Ubuntu release before install (affects package versions).
- Decide NAT vs bridge for VM networking at build time (outbound works either
  way; bridge only if the VM must be reachable from the LAN).
- `grant sudo` window needed for the host package install (root-required).

## 8. How many choices — the short answer

**Four free/Ubuntu-plausible candidates; one clear winner** (libvirt/KVM).
The other three are disqualified for concrete reasons above. The decision is
not a hard one, which is a good sign — it means the mature, boring, correct
choice is obvious.
