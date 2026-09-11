# vmtooling

Home for **deployment and backup tooling** for the DAR-OW-158 disposable VM
sandbox, plus supporting tools.

## Contents

| Path | Purpose |
|:-----|:--------|
| `docs/backup-design.md` | Research paper: measured compressibility + backup architecture for the disposable VM |
| `docs/vm-content-boundary.md` | Research paper: what must be inside the VM vs. read-only-referenced from host via virtiofs |
| `docs/vm-manager-selection.md` | Decision paper: VM manager choice (libvirt/KVM over Proxmox/VirtualBox/Xen) |
| `scrap/compress_measure.py` | Tool to measure how well a directory tree compresses (gzip/zstd by file class) |

## Measurement tool

```bash
# one-time setup
python3 -m venv .venv
.venv/bin/pip install zstandard

# measure compressibility of a tree
.venv/bin/python scrap/compress_measure.py /home/d/dev_env --sample-bytes 8388608
```

## Why this exists

All model-driven work (Gravitas, swarm, self-dev) will run inside a disposable,
daily-backed-up KVM/QEMU sandbox VM. This repo holds the tooling that deploys
and backs up that VM. See `docs/backup-design.md` for the design rationale.
