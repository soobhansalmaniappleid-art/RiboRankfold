#!/usr/bin/env python
from __future__ import annotations

import argparse
import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd


REPRESENTATIVE_ATOMS = ("C4'", "C4*", "P")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a distribution-shift evaluation harness for RNA 3D candidate ensembles. "
            "Targets are expected as CANDIDATES_ROOT/TARGET_ID/*.pdb. If native.pdb is "
            "present for a target, labels and ranking metrics are computed."
        )
    )
    parser.add_argument("--candidates-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--native-name", default="native.pdb")
    parser.add_argument(
        "--native-map",
        type=Path,
        default=None,
        help="Optional CSV with columns target_id,native_path for benchmarks whose natives are stored outside target folders.",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-native-candidate", action="store_true")
    args = parser.parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive")
    return args


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset_name = args.dataset_name or args.candidates_root.name

    native_map = read_native_map(args.native_map)
    manifest = build_manifest(
        args.candidates_root,
        native_name=args.native_name,
        include_native=args.include_native_candidate,
        native_map=native_map,
    )
    if manifest.empty:
        raise SystemExit(f"No candidate PDB files found under {args.candidates_root}")

    features = build_features(manifest)
    features = add_labels(features, native_name=args.native_name)
    features = add_scores(features)

    manifest.to_csv(args.out_dir / "manifest.csv", index=False)
    features.to_csv(args.out_dir / "features.csv", index=False)

    label_available = bool(features["has_native"].any())
    if label_available:
        per_target = evaluate_per_target(features, top_k=args.top_k)
        method_metrics = summarize_methods(per_target)
        pairwise = pairwise_ranking_accuracy(features)
        source_shift = source_shift_summary(features, top_k=args.top_k)
        per_target.to_csv(args.out_dir / "per_target_metrics.csv", index=False)
        method_metrics.to_csv(args.out_dir / "method_metrics.csv", index=False)
        pairwise.to_csv(args.out_dir / "pairwise_accuracy.csv", index=False)
        source_shift.to_csv(args.out_dir / "source_shift_summary.csv", index=False)
    else:
        per_target = pd.DataFrame()
        method_metrics = pd.DataFrame()
        pairwise = pd.DataFrame()
        source_shift = pd.DataFrame()

    report = render_report(
        dataset_name=dataset_name,
        candidates_root=args.candidates_root,
        features=features,
        per_target=per_target,
        method_metrics=method_metrics,
        pairwise=pairwise,
        source_shift=source_shift,
        top_k=args.top_k,
    )
    (args.out_dir / "summary.md").write_text(report, encoding="utf-8")
    print(f"Wrote ensemble evaluation artifacts to {args.out_dir}")


def read_native_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    frame = pd.read_csv(path)
    required = {"target_id", "native_path"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"native map missing columns: {sorted(missing)}")
    return {str(row.target_id): str(row.native_path) for row in frame.itertuples(index=False)}


def build_manifest(
    candidates_root: Path,
    native_name: str,
    include_native: bool,
    native_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    native_map = native_map or {}
    rows: list[dict[str, object]] = []
    for target_dir in sorted(path for path in candidates_root.iterdir() if path.is_dir()):
        mapped_native = Path(native_map[target_dir.name]) if target_dir.name in native_map else None
        native_path = mapped_native if mapped_native is not None else target_dir / native_name
        for candidate_path in sorted(target_dir.glob("*.pdb")):
            if candidate_path.name == native_name and not include_native:
                continue
            rows.append(
                {
                    "target_id": target_dir.name,
                    "candidate_id": candidate_path.stem,
                    "candidate_path": str(candidate_path),
                    "candidate_source": infer_candidate_source(candidate_path.stem),
                    "native_path": str(native_path) if native_path.exists() else "",
                    "has_native": native_path.exists(),
                }
            )
    return pd.DataFrame(rows)


def infer_candidate_source(candidate_id: str) -> str:
    lowered = candidate_id.lower()
    if lowered.startswith("casp"):
        return "casp"
    if lowered.startswith("rhofold"):
        return "rhofold"
    if lowered.startswith("drfold"):
        return "drfold"
    if lowered.startswith("farfar"):
        return "farfar2"
    if lowered.startswith("template"):
        return "template"
    if lowered.startswith("decoy"):
        return "synthetic_decoy"
    if lowered.startswith("native"):
        return "native"
    return "unknown"


def build_features(manifest: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for item in manifest.itertuples(index=False):
        coords = representative_coords(Path(item.candidate_path))
        row = item._asdict()
        row.update(geometry_features(coords))
        rows.append(row)
    return pd.DataFrame(rows)


def add_labels(features: pd.DataFrame, native_name: str) -> pd.DataFrame:
    rows = []
    native_cache: dict[str, np.ndarray] = {}
    for item in features.itertuples(index=False):
        row = item._asdict()
        if not bool(item.has_native):
            row.update(
                {
                    "true_rmsd": np.nan,
                    "true_tm_like": np.nan,
                    "contact_map_f1": np.nan,
                    "contact_map_precision": np.nan,
                    "contact_map_recall": np.nan,
                    "multi_metric_quality": np.nan,
                    "aligned_residue_count": 0,
                }
            )
            rows.append(row)
            continue
        native_path = Path(item.native_path)
        if str(native_path) not in native_cache:
            native_cache[str(native_path)] = representative_coords(native_path)
        native = native_cache[str(native_path)]
        candidate = representative_coords(Path(item.candidate_path))
        rmsd, aligned, contact_metrics = best_structure_match(Path(item.candidate_path), native_path)
        row["true_rmsd"] = rmsd
        row["true_tm_like"] = tm_like(rmsd, aligned) if aligned else np.nan
        row.update(contact_metrics)
        row["multi_metric_quality"] = multi_metric_quality(row["true_tm_like"], row["contact_map_f1"], row["clashes_per_residue"])
        row["aligned_residue_count"] = aligned
        rows.append(row)
    return pd.DataFrame(rows)


def add_scores(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    frame["score_contact"] = normalize(frame["contact_density"]) + 0.5 * normalize(frame["long_range_contact_density"])
    frame["score_low_clash"] = -normalize(frame["clashes_per_residue"]) - 0.5 * normalize(frame["backbone_break_fraction"])
    frame["score_compact"] = normalize(frame["compactness"]) - 0.25 * normalize(frame["radius_of_gyration"])
    frame["score_hybrid"] = (
        0.45 * normalize(frame["contact_density"])
        + 0.25 * normalize(frame["long_range_contact_density"])
        - 0.20 * normalize(frame["clashes_per_residue"])
        - 0.10 * normalize(frame["backbone_break_fraction"])
        + 0.10 * normalize(frame["compactness"])
    )
    return frame


def evaluate_per_target(features: pd.DataFrame, top_k: int) -> pd.DataFrame:
    score_columns = ["score_hybrid", "score_contact", "score_low_clash", "score_compact"]
    rows: list[dict[str, object]] = []
    labeled = features.dropna(subset=["true_tm_like", "true_rmsd", "multi_metric_quality"])
    for target_id, group in labeled.groupby("target_id"):
        oracles = {
            "tm_like": group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0],
            "multi_metric": group.sort_values(["multi_metric_quality", "true_tm_like"], ascending=[False, False]).iloc[0],
        }
        for score_column in score_columns:
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            selected_top1 = selected.iloc[0]
            for oracle_type, oracle in oracles.items():
                sort_columns = ["true_tm_like", "true_rmsd"] if oracle_type == "tm_like" else ["multi_metric_quality", "true_tm_like"]
                ascending = [False, True] if oracle_type == "tm_like" else [False, False]
                selected_best = selected.sort_values(sort_columns, ascending=ascending).iloc[0]
                rows.append(
                    {
                        "target_id": target_id,
                        "method": score_column.replace("score_", ""),
                        "oracle_type": oracle_type,
                        "num_candidates": int(len(group)),
                        "oracle_candidate": oracle.candidate_id,
                        "oracle_tm_like": float(oracle.true_tm_like),
                        "oracle_rmsd": float(oracle.true_rmsd),
                        "oracle_contact_f1": float(oracle.contact_map_f1),
                        "oracle_multi_metric_quality": float(oracle.multi_metric_quality),
                        "selected_top1_candidate": selected_top1.candidate_id,
                        "selected_top1_tm_like": float(selected_top1.true_tm_like),
                        "selected_top1_rmsd": float(selected_top1.true_rmsd),
                        "selected_top1_contact_f1": float(selected_top1.contact_map_f1),
                        "selected_top1_multi_metric_quality": float(selected_top1.multi_metric_quality),
                        f"selected_best_in_top{top_k}_candidate": selected_best.candidate_id,
                        f"best_of_{top_k}_tm_like": float(selected_best.true_tm_like),
                        f"best_of_{top_k}_rmsd": float(selected_best.true_rmsd),
                        f"best_of_{top_k}_contact_f1": float(selected_best.contact_map_f1),
                        f"best_of_{top_k}_multi_metric_quality": float(selected_best.multi_metric_quality),
                        "tm_like_regret": float(oracle.true_tm_like - selected_best.true_tm_like),
                        "rmsd_regret": float(selected_best.true_rmsd - oracle.true_rmsd),
                        "multi_metric_regret": float(oracle.multi_metric_quality - selected_best.multi_metric_quality),
                        f"oracle_in_top{top_k}": bool(oracle.candidate_id in set(selected["candidate_id"])),
                    }
                )
    return pd.DataFrame(rows)


def summarize_methods(per_target: pd.DataFrame) -> pd.DataFrame:
    if per_target.empty:
        return pd.DataFrame()
    topk_column = next(column for column in per_target.columns if column.startswith("best_of_") and column.endswith("_tm_like"))
    topk_multi_column = next(column for column in per_target.columns if column.startswith("best_of_") and column.endswith("_multi_metric_quality"))
    hit_column = next(column for column in per_target.columns if column.startswith("oracle_in_top"))
    return (
        per_target.groupby(["oracle_type", "method"])
        .agg(
            targets=("target_id", "nunique"),
            mean_best_of_k_tm_like=(topk_column, "mean"),
            mean_best_of_k_multi_metric=(topk_multi_column, "mean"),
            mean_tm_like_regret=("tm_like_regret", "mean"),
            mean_multi_metric_regret=("multi_metric_regret", "mean"),
            mean_rmsd_regret=("rmsd_regret", "mean"),
            oracle_hit_rate=(hit_column, "mean"),
        )
        .reset_index()
        .sort_values("mean_best_of_k_tm_like", ascending=False)
    )


def pairwise_ranking_accuracy(features: pd.DataFrame) -> pd.DataFrame:
    score_columns = ["score_hybrid", "score_contact", "score_low_clash", "score_compact"]
    rows = []
    labeled = features.dropna(subset=["true_tm_like"])
    for target_id, group in labeled.groupby("target_id"):
        pairs = list(itertools.combinations(group.index, 2))
        for score_column in score_columns:
            total = 0
            correct = 0
            for left_idx, right_idx in pairs:
                left = group.loc[left_idx]
                right = group.loc[right_idx]
                truth = math.copysign(1.0, left.true_tm_like - right.true_tm_like) if left.true_tm_like != right.true_tm_like else 0.0
                pred = math.copysign(1.0, left[score_column] - right[score_column]) if left[score_column] != right[score_column] else 0.0
                if truth == 0.0:
                    continue
                total += 1
                if pred == truth:
                    correct += 1
            rows.append(
                {
                    "target_id": target_id,
                    "method": score_column.replace("score_", ""),
                    "pairwise_comparisons": total,
                    "pairwise_accuracy": correct / total if total else np.nan,
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    summary = (
        frame.groupby("method")
        .agg(
            targets=("target_id", "nunique"),
            pairwise_comparisons=("pairwise_comparisons", "sum"),
            mean_pairwise_accuracy=("pairwise_accuracy", "mean"),
        )
        .reset_index()
        .sort_values("mean_pairwise_accuracy", ascending=False)
    )
    return summary


def source_shift_summary(features: pd.DataFrame, top_k: int) -> pd.DataFrame:
    """Report source composition and whether a scoring mode selects across sources.

    This is a scaffold for generator-aware evaluation. With true multi-generator
    inputs, it exposes whether a method generalizes beyond the dominant source.
    """
    labeled = features.dropna(subset=["true_tm_like"])
    if labeled.empty:
        return pd.DataFrame()
    rows = []
    for target_id, group in labeled.groupby("target_id"):
        oracle = group.sort_values(["true_tm_like", "true_rmsd"], ascending=[False, True]).iloc[0]
        source_counts = group["candidate_source"].value_counts().to_dict()
        for score_column in ["score_hybrid", "score_contact", "score_low_clash", "score_compact"]:
            selected = group.sort_values(score_column, ascending=False).head(top_k)
            rows.append(
                {
                    "target_id": target_id,
                    "method": score_column.replace("score_", ""),
                    "candidate_sources": ";".join(f"{key}:{value}" for key, value in sorted(source_counts.items())),
                    "oracle_source": oracle.candidate_source,
                    "selected_top1_source": selected.iloc[0].candidate_source,
                    f"selected_top{top_k}_source_count": int(selected["candidate_source"].nunique()),
                    "oracle_source_in_selected": bool(oracle.candidate_source in set(selected["candidate_source"])),
                }
            )
    return pd.DataFrame(rows)


def representative_coords(path: Path) -> np.ndarray:
    chains = representative_chains(path)
    if not chains:
        return np.asarray([], dtype=float)
    coords = []
    for chain_id in sorted(chains):
        coords.extend(chains[chain_id])
    return np.asarray(coords, dtype=float)


def representative_chains(path: Path) -> dict[str, np.ndarray]:
    residues: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith(("ATOM", "HETATM")) or len(line) < 54:
                continue
            atom = line[12:16].strip()
            if atom not in REPRESENTATIVE_ATOMS:
                continue
            chain = line[21].strip() or "_"
            resseq = line[22:26].strip()
            icode = line[26].strip()
            try:
                coord = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])], dtype=float)
            except ValueError:
                continue
            residues.setdefault((chain, resseq, icode), {})[atom] = coord
    chains: dict[str, list[np.ndarray]] = {}
    for key in sorted(residues, key=lambda item: (item[0], residue_number(item[1]), item[2])):
        atoms = residues[key]
        chosen = next((atoms[name] for name in REPRESENTATIVE_ATOMS if name in atoms), None)
        if chosen is not None:
            chains.setdefault(key[0], []).append(chosen)
    return {chain: np.asarray(coords, dtype=float) for chain, coords in chains.items()}


def residue_number(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def geometry_features(coords: np.ndarray) -> dict[str, float]:
    n = int(len(coords))
    if n == 0:
        return {
            "num_residues": 0,
            "radius_of_gyration": np.nan,
            "end_to_end_distance": np.nan,
            "contact_density": 0.0,
            "long_range_contact_density": 0.0,
            "clashes_per_residue": np.nan,
            "backbone_break_fraction": np.nan,
            "compactness": 0.0,
        }
    centered = coords - coords.mean(axis=0)
    radius = float(np.sqrt((centered**2).sum(axis=1).mean()))
    end_to_end = float(np.linalg.norm(coords[-1] - coords[0])) if n > 1 else 0.0
    distances = pairwise_distances(coords)
    upper = distances[np.triu_indices(n, k=1)]
    contact_count = int((upper < 12.0).sum()) if len(upper) else 0
    possible = n * (n - 1) / 2
    long_count = 0
    long_possible = 0
    for i in range(n):
        for j in range(i + 8, n):
            long_possible += 1
            if distances[i, j] < 18.0:
                long_count += 1
    steps = np.linalg.norm(np.diff(coords, axis=0), axis=1) if n > 1 else np.asarray([])
    breaks = int((steps > 12.0).sum()) if len(steps) else 0
    clashes = int(((upper < 2.5) & (upper > 0.0)).sum()) if len(upper) else 0
    return {
        "num_residues": n,
        "radius_of_gyration": radius,
        "end_to_end_distance": end_to_end,
        "contact_density": float(contact_count / possible) if possible else 0.0,
        "long_range_contact_density": float(long_count / long_possible) if long_possible else 0.0,
        "clashes_per_residue": float(clashes / n),
        "backbone_break_fraction": float(breaks / max(n - 1, 1)),
        "compactness": float(n / (radius + 1e-6)),
    }


def pairwise_distances(coords: np.ndarray) -> np.ndarray:
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff**2).sum(axis=2))


def best_structure_match(candidate_path: Path, native_path: Path) -> tuple[float, int, dict[str, float]]:
    """Find the best chain/window match before computing labels.

    CASP RNA natives may contain multiple RNA chains and non-RNA molecules. Candidate
    files are often single-chain C4' traces. A naive concatenated alignment can turn
    a valid candidate into a very high RMSD artifact, so labels are computed against
    the best chain/window pair.
    """
    candidate_chains = representative_chains(candidate_path)
    native_chains = representative_chains(native_path)
    best: tuple[float, int, dict[str, float]] | None = None
    for candidate in candidate_chains.values():
        for native in native_chains.values():
            for c_segment, n_segment in comparable_segments(candidate, native):
                rmsd, aligned = aligned_rmsd(c_segment, n_segment)
                if aligned == 0 or not np.isfinite(rmsd):
                    continue
                contact_metrics = contact_map_metrics(c_segment, n_segment)
                if best is None or rmsd < best[0]:
                    best = (rmsd, aligned, contact_metrics)
    if best is None:
        return np.nan, 0, {"contact_map_precision": np.nan, "contact_map_recall": np.nan, "contact_map_f1": np.nan}
    return best


def comparable_segments(candidate: np.ndarray, native: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    c_len = len(candidate)
    n_len = len(native)
    if c_len == 0 or n_len == 0:
        return []
    length = min(c_len, n_len)
    if length < 3:
        return []
    if c_len == n_len:
        return [(candidate, native)]
    if c_len < n_len:
        return [(candidate, native[start : start + c_len]) for start in range(n_len - c_len + 1)]
    return [(candidate[start : start + n_len], native) for start in range(c_len - n_len + 1)]


def contact_map_metrics(candidate: np.ndarray, native: np.ndarray, threshold: float = 18.0, min_separation: int = 8) -> dict[str, float]:
    n = min(len(candidate), len(native))
    if n <= min_separation:
        return {"contact_map_precision": np.nan, "contact_map_recall": np.nan, "contact_map_f1": np.nan}
    candidate_distances = pairwise_distances(candidate[:n])
    native_distances = pairwise_distances(native[:n])
    mask = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(i + min_separation, n):
            mask[i, j] = True
    candidate_contacts = (candidate_distances < threshold) & mask
    native_contacts = (native_distances < threshold) & mask
    tp = int((candidate_contacts & native_contacts).sum())
    pred = int(candidate_contacts.sum())
    truth = int(native_contacts.sum())
    precision = tp / pred if pred else 0.0
    recall = tp / truth if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "contact_map_precision": float(precision),
        "contact_map_recall": float(recall),
        "contact_map_f1": float(f1),
    }


def aligned_rmsd(candidate: np.ndarray, native: np.ndarray) -> tuple[float, int]:
    n = min(len(candidate), len(native))
    if n == 0:
        return np.nan, 0
    candidate = candidate[:n]
    native = native[:n]
    candidate_centered = candidate - candidate.mean(axis=0)
    native_centered = native - native.mean(axis=0)
    covariance = candidate_centered.T @ native_centered
    u, _, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    correction[2, 2] = np.sign(np.linalg.det(u @ vt))
    rotation = u @ correction @ vt
    aligned = candidate_centered @ rotation
    rmsd = np.sqrt(((aligned - native_centered) ** 2).sum() / n)
    return float(rmsd), int(n)


def tm_like(rmsd: float, aligned_count: int) -> float:
    if not np.isfinite(rmsd) or aligned_count <= 0:
        return np.nan
    d0 = max(1.0, 1.24 * ((max(aligned_count, 16) - 15) ** (1.0 / 3.0)) - 1.8)
    return float(1.0 / (1.0 + (rmsd / d0) ** 2))


def multi_metric_quality(tm_score: float, contact_f1: float, clashes_per_residue: float) -> float:
    if not np.isfinite(tm_score):
        return np.nan
    contact = 0.0 if not np.isfinite(contact_f1) else contact_f1
    clash_penalty = 0.0 if not np.isfinite(clashes_per_residue) else min(float(clashes_per_residue), 1.0)
    return float(0.65 * tm_score + 0.30 * contact - 0.05 * clash_penalty)


def normalize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    std = values.std(ddof=0)
    if std == 0 or not np.isfinite(std):
        return values * 0.0
    return (values - values.mean()) / std


def render_report(
    dataset_name: str,
    candidates_root: Path,
    features: pd.DataFrame,
    per_target: pd.DataFrame,
    method_metrics: pd.DataFrame,
    pairwise: pd.DataFrame,
    source_shift: pd.DataFrame,
    top_k: int,
) -> str:
    targets = features["target_id"].nunique()
    candidates = len(features)
    labeled_targets = features.loc[features["has_native"], "target_id"].nunique()
    source_counts = features["candidate_source"].value_counts().rename_axis("source").reset_index(name="count")
    lines = [
        f"# Ensemble Evaluation: {dataset_name}",
        "",
        "## Scope",
        "",
        f"- Candidates root: `{candidates_root}`",
        f"- Targets: `{targets}`",
        f"- Candidates: `{candidates}`",
        f"- Targets with native labels: `{labeled_targets}`",
        f"- Top-k: `{top_k}`",
        "",
        "## Candidate Sources",
        "",
        source_counts.to_markdown(index=False),
        "",
    ]
    if method_metrics.empty:
        lines.extend(
            [
                "## Evaluation Status",
                "",
                "No native structures were found inside the target folders, so this run only produced manifest/features/scores.",
                "To compute regret and oracle metrics, add `native.pdb` per target or extend the harness with a native mapping file.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"## Method Metrics",
                "",
                method_metrics.to_markdown(index=False),
                "",
                "## Pairwise Ranking Accuracy",
                "",
                pairwise.to_markdown(index=False),
                "",
                "## Generator / Source-Aware Summary",
                "",
                source_shift.to_markdown(index=False),
                "",
                "## Per-Target Metrics",
                "",
                per_target.to_markdown(index=False),
                "",
                "## Interpretation",
                "",
                "This is an evaluation harness, not a state-of-the-art model claim. "
                "It measures whether simple scoring modes can recover the oracle candidate under the available candidate distribution.",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
