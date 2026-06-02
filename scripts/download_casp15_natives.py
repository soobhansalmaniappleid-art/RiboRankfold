#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd


CASP15_RNA_NATIVE_PDB_IDS = {
    # Official CASP15 RNA target list:
    # https://predictioncenter.org/casp15/targetlist.cgi?view=rna
    "R1107": "7QR4",
    "R1108": "7QR3",
    "R1116": "8S95",
    "R1117": "8FZA",
    "R1126": "8TVZ",
    "R1128": "8BTZ",
    "R1136": "7ZJ4",
    # R1138 has two listed reference structures; use the first as the default anchor.
    "R1138": "7PTK",
    "R1149": "8UYS",
    # R1156 has three listed reference structures; use the first as the default anchor.
    "R1156": "8UYE",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download available CASP15 RNA native PDB structures from RCSB.")
    parser.add_argument("--out-dir", type=Path, default=Path("data/casp15_rna/natives"))
    parser.add_argument("--native-map", type=Path, default=Path("data/casp15_rna/native_map.csv"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for target_id, pdb_id in CASP15_RNA_NATIVE_PDB_IDS.items():
        out_path = args.out_dir / f"{target_id}_{pdb_id}.pdb"
        if args.force or not out_path.exists():
            url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            urlretrieve(url, out_path)
        rows.append({"target_id": target_id, "pdb_id": pdb_id, "native_path": str(out_path)})

    args.native_map.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.native_map, index=False)
    print(f"Wrote native structures to {args.out_dir}")
    print(f"Wrote native map to {args.native_map}")


if __name__ == "__main__":
    main()
