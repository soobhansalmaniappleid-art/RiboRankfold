"""Markdown report rendering."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

USALIGN_NOTE = (
    "official US-align TM-score, normalised by the native. Comparable with "
    "published CASP RNA results."
)

METRIC_CAVEAT = (
    "`tm_like` is an internal TM-score-shaped statistic computed from chain/window "
    "aligned RMSD, not official US-align TM-score. Values are internally comparable "
    "but must not be compared against published CASP TM-scores."
)


def render_ensemble_report(
    dataset_name: str,
    candidates_root: Path,
    features: pd.DataFrame,
    per_target: pd.DataFrame,
    method_metrics: pd.DataFrame,
    pairwise: pd.DataFrame,
    source_shift: pd.DataFrame,
    top_k: int,
    label_metric: str = "true_tm_like",
    coverage: pd.DataFrame | None = None,
    ties: pd.DataFrame | None = None,
    versus_random: pd.DataFrame | None = None,
    curve: pd.DataFrame | None = None,
    power: pd.DataFrame | None = None,
) -> str:
    source_counts = (
        features["candidate_source"].value_counts().rename_axis("source").reset_index(name="count")
    )
    lines = [
        f"# Ensemble Evaluation: {dataset_name}",
        "",
        "## Scope",
        "",
        f"- Candidates root: `{candidates_root}`",
        f"- Targets: `{features['target_id'].nunique()}`",
        f"- Candidates: `{len(features)}`",
        f"- Targets with native labels: "
        f"`{features.loc[features['has_native'], 'target_id'].nunique()}`",
        f"- Top-k: `{top_k}`",
        f"- Ground-truth metric: `{label_metric}`",
        f"- Metric caveat: {METRIC_CAVEAT if label_metric != 'usalign_tm' else USALIGN_NOTE}",
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
                "No native structures were found inside the target folders, so this run "
                "only produced manifest/features/scores.",
                "To compute regret and oracle metrics, add `native.pdb` per target or pass "
                "`--native-map`.",
                "",
            ]
        )
        return "\n".join(lines)

    if coverage is not None and not coverage.empty and int(coverage["unlabelled"].sum()):
        lines.extend(
            [
                "## Label Coverage",
                "",
                f"`{int(coverage['unlabelled'].sum())}` candidates could not be scored with "
                f"`{label_metric}` and are excluded from every metric below. US-align "
                "represents an RNA residue by C3', so candidates deposited as C4'-only "
                "backbone traces cannot be scored without changing the representative "
                "atom, which would break comparability with published CASP numbers.",
                "",
                coverage.to_markdown(index=False),
                "",
            ]
        )

    if versus_random is not None and not versus_random.empty:
        lines.extend(
            [
                "## Versus Random Selection",
                "",
                "Read this first. Each mode is compared with picking candidates at "
                "random from the same pools. `random` holds the exact expectation; "
                "`verdict` places each mode's best-of-k against the 95% interval of "
                "random selection. A mode below random is worse than no model.",
                "",
                versus_random.to_markdown(index=False),
                "",
            ]
        )

    if curve is not None and not curve.empty:
        survivors = curve[curve["survives_holm"]]
        lines.extend(
            [
                "## Retrieval Curve",
                "",
                "Separate question from ranking: does a mode keep the best candidate "
                "inside its top k more often than random selection does? That is what "
                "matters if this is used to shrink a pool for an expensive downstream "
                "scorer. `p_value` is a paired sign-flip permutation test and "
                "`survives_holm` corrects across the whole grid, because sweeping "
                "modes against k values produces dozens of comparisons.",
                "",
                curve.round(4).to_markdown(index=False),
                "",
                (
                    "No (mode, k) survives correction: this benchmark does not show "
                    "retrieval above random."
                    if survivors.empty
                    else "Surviving: "
                    + ", ".join(f"`{r.method}`@{r.k}" for r in survivors.itertuples())
                ),
                "",
            ]
        )

    if power is not None and not power.empty:
        available = int(power["n_targets_available"].iloc[0])
        lines.extend(
            [
                "## Statistical Power",
                "",
                f"This benchmark has **{available}** labelled targets. The table below "
                "says how many would be needed to detect a given improvement in "
                "hit-rate, at the stated power, with the alpha split across the "
                "comparisons actually run. No single row is *the* requirement: the "
                "answer moves by an order of magnitude across plausible effect sizes, "
                "so it is reported whole.",
                "",
                power.to_markdown(index=False),
                "",
            ]
        )

    lines.extend(
        [
            "## Method Metrics",
            "",
            method_metrics.to_markdown(index=False),
            "",
            "## Score Ties",
            "",
            "A high `tied_fraction` means the mode's top-k is mostly decided by "
            "tie-breaking rather than by the score, so its metrics below are not "
            "evidence of ranking skill.",
            "",
            ties.to_markdown(index=False) if ties is not None else "_not computed_",
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
            "This is an evaluation harness, not a state-of-the-art model claim. It measures "
            "whether simple scoring modes can recover the oracle candidate under the "
            "available candidate distribution. The number that matters is "
            "`oracle_hit_rate`; a high `mean_best_of_k_tm_like` with a zero hit rate means "
            "the pool is weak, not that the ranker works.",
            "",
        ]
    )
    return "\n".join(lines)
