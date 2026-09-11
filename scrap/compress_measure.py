#!/usr/bin/env python3
"""compress_measure.py — measure backup compressibility of a directory tree.

Walks a directory, buckets files by extension, and reports how each class
compresses (gzip and zstd) so we can reason about daily VM backup size.

Usage:
    python3 compress_measure.py [path] [--limit N] [--max-samples 500] [--sample-bytes 20MB]

Example:
    python3 compress_measure.py /home/d/dev_env --sample-bytes 20971520

Output: per-extension table with raw bytes, compressed bytes, ratio, and
estimated compressed size extrapolated to the full tree.
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import sys
import zlib
from collections import defaultdict
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover - optional
    zstd = None


EXT_GROUP = {
    ".md": "markdown/text",
    ".markdown": "markdown/text",
    ".txt": "markdown/text",
    ".rst": "markdown/text",
    ".py": "python",
    ".pyi": "python",
    ".sh": "shell",
    ".bash": "shell",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "config",
    ".cfg": "config",
    ".conf": "config",
    ".log": "log",
    ".out": "log",
    ".csv": "data",
    ".tsv": "data",
    ".js": "js/ts",
    ".ts": "js/ts",
    ".tsx": "js/ts",
    ".jsx": "js/ts",
    ".tsbuildinfo": "js/ts",
    ".map": "js/ts",
    ".html": "web",
    ".css": "web",
    ".svg": "web",
    ".xml": "xml",
    ".ipynb": "notebook",
    ".lock": "lockfile",
    ".png": "binary/image",
    ".jpg": "binary/image",
    ".jpeg": "binary/image",
    ".gif": "binary/image",
    ".webp": "binary/image",
    ".ico": "binary/image",
    ".pdf": "binary/image",
    ".gz": "binary/compressed",
    ".zip": "binary/compressed",
    ".tar": "binary/archive",
    ".tgz": "binary/compressed",
    ".xz": "binary/compressed",
    ".zst": "binary/compressed",
    ".whl": "binary/compressed",
    ".so": "binary/native",
    ".dll": "binary/native",
    ".bin": "binary/native",
    ".pyc": "binary/native",
    ".whl": "binary/compressed",
    ".sqlite": "binary/db",
    ".db": "binary/db",
    ".node": "binary/native",
    ".ttf": "binary/image",
    ".otf": "binary/image",
    ".woff": "binary/compressed",
    ".woff2": "binary/compressed",
    ".parquet": "binary/parquet",
    ".npz": "binary/compressed",
    ".npy": "binary/native",
    ".pt": "binary/native",
    ".pkl": "binary/native",
    ".joblib": "binary/native",
    ".ckpt": "binary/native",
    ".safetensors": "binary/native",
    ".onnx": "binary/native",
    ".model": "binary/native",
}


def gzip_ratio(data: bytes) -> float:
    return len(data) / len(gzip.compress(data, compresslevel=6))


def zstd_ratio(data: bytes, level: int = 3) -> float:
    if zstd is None:
        return 0.0
    cctx = zstd.ZstdCompressor(level=level)
    return len(data) / len(cctx.compress(data))


def classify(name: str) -> str:
    ext = Path(name).suffix.lower()
    return EXT_GROUP.get(ext, "other")


def walk(root: Path, limit: int, max_samples: int, sample_bytes: int):
    """Collect total bytes + measured samples per class."""
    totals: dict[str, int] = defaultdict(int)
    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[bytes]] = defaultdict(list)
    sample_counts: dict[str, int] = defaultdict(int)

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip heavy/uninteresting dirs by default
        dirnames[:] = [
            d
            for d in dirnames
            if d not in (".git", "node_modules", ".venv", "__pycache__", ".cache")
        ]
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            cls = classify(fn)
            totals[cls] += size
            counts[cls] += 1
            # Sample up to max_samples files per class
            if sample_counts[cls] < max_samples and size > 0:
                try:
                    with open(fp, "rb") as fh:
                        data = fh.read(sample_bytes)
                    samples[cls].append(data)
                    sample_counts[cls] += 1
                except OSError:
                    continue
            if limit and sum(counts.values()) >= limit:
                return totals, counts, samples
    return totals, counts, samples


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=".", help="directory to scan")
    ap.add_argument("--limit", type=int, default=0, help="stop after N files")
    ap.add_argument("--max-samples", type=int, default=300)
    ap.add_argument("--sample-bytes", type=int, default=5_000_000)
    ap.add_argument("--min-total-bytes", type=int, default=1_000_000)
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    totals, counts, samples = walk(
        root, args.limit, args.max_samples, args.sample_bytes
    )

    print(f"# Compression measurement: {root}")
    print(f"(sampled up to {args.max_samples} files/class, "
          f"{args.sample_bytes} bytes/file; gzip -6, zstd -3)\n")

    rows = []
    for cls, total in totals.items():
        if total < args.min_total_bytes:
            continue
        s = samples.get(cls, [])
        if not s:
            rows.append((cls, total, counts[cls], 0.0, 0.0, None))
            continue
        # Aggregate ratio over sampled bytes
        raw = b"".join(s)
        gz = gzip_ratio(raw)
        zs = zstd_ratio(raw) if zstd else 0.0
        rows.append((cls, total, counts[cls], gz, zs, len(raw)))

    rows.sort(key=lambda r: -r[1])
    total_raw = sum(r[1] for r in rows)
    est_gz = sum(r[1] / r[3] for r in rows if r[3] > 0)

    print(f"{'class':<22}{'raw MB':>10}{'files':>8}{'gzip x':>9}"
          f"{'zstd x':>9}{'est.gz MB':>12}")
    print("-" * 70)
    for cls, total, cnt, gz, zs, _ in rows:
        gz_s = f"{gz:.1f}" if gz else "-"
        zs_s = f"{zs:.1f}" if zs else "-"
        est = total / gz if gz else 0
        print(f"{cls:<22}{total/1e6:>10.1f}{cnt:>8}{gz_s:>9}{zs_s:>9}"
              f"{est/1e6:>12.1f}")

    print("-" * 70)
    print(f"{'TOTAL':<22}{total_raw/1e6:>10.1f}"
          f"{sum(r[2] for r in rows):>8}"
          f"{'':>9}{'':>9}{est_gz/1e6:>12.1f}")
    if total_raw:
        print(f"\nOverall gzip ratio: {total_raw/est_gz:.1f}x "
              f"(sampled classes, ≥{args.min_total_bytes/1e6:.0f} MB)")

    if zstd is None:
        print("\nnote: zstandard not installed; install with "
              "`pip install zstandard` for zstd numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
