#!/usr/bin/env python
from __future__ import annotations

import argparse
import tarfile
from pathlib import Path
from urllib.request import urlretrieve


DEFAULT_TARGETS = [
    "R1107",
    "R1108",
    "R1116",
    "R1117",
    "R1126",
    "R1128",
    "R1136",
    "R1138",
    "R1149",
    "R1156",
]

BASE_URL = "https://predictioncenter.org/download_area/CASP15/predictions/RNA"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and extract CASP15 RNA prediction tarballs.")
    parser.add_argument("--targets", nargs="*", default=DEFAULT_TARGETS)
    parser.add_argument("--out-root", type=Path, default=Path("data/casp15_rna/candidates"))
    parser.add_argument("--archive-dir", type=Path, default=Path("data/casp15_rna/downloads"))
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-extract", action="store_true")
    args = parser.parse_args()

    args.out_root.mkdir(parents=True, exist_ok=True)
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    for target_id in args.targets:
        archive = args.archive_dir / f"{target_id}.tar.gz"
        if args.force_download or not archive.exists():
            url = f"{BASE_URL}/{target_id}.tar.gz"
            print(f"Downloading {url}")
            urlretrieve(url, archive)
        count = extract_predictions(archive, args.out_root / target_id, force=args.force_extract)
        print(f"{target_id}: extracted {count} PDB-like models to {args.out_root / target_id}")


def extract_predictions(archive: Path, target_dir: Path, force: bool) -> int:
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            raw_name = Path(member.name).name
            if not raw_name or raw_name.startswith("."):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            content = handle.read()
            if b"ATOM" not in content and b"HETATM" not in content:
                continue
            candidate_id = Path(raw_name).stem
            out_path = target_dir / f"casp15_{candidate_id}.pdb"
            if out_path.exists() and not force:
                continue
            out_path.write_bytes(content)
            count += 1
    return count


if __name__ == "__main__":
    main()
