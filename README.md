# RiboRank

Two things live in this repository:

1. **`riborank/`** — an evaluation harness for *ranking* RNA 3D structure
   candidates. Given many predicted structures for one target, can a scoring
   function retrieve the best one?
2. **`discovery/`** — a staged funnel for genomic discovery, where deterministic
   detectors run first and a language model runs last. See
   [docs/DISCOVERY.md](docs/DISCOVERY.md).

## Status, stated plainly

**No scoring mode here beats picking candidates at random.** Measured with
official US-align TM-score on CASP15 (10 targets, 1355 scored candidates),
tie-aware, against the exact random expectation of **0.422**
(95%: 0.354–0.490):

| mode | best-of-5 | vs random | top-1 pick percentile |
|---|---:|---|---:|
| `plausibility` | 0.394 | within random | 57.1 |
| `low_clash` | 0.430 | within random | 51.0 |
| `contact` | 0.317 | below random | 13.2 |
| `hybrid` | 0.312 | below random | 15.9 |
| `compact` | 0.275 | below random | 15.7 |

Random picks at percentile 50 by definition. Three modes land near **15**,
because they reward compactness without limit and their top pick is a collapsed
structure. `plausibility` fixes that and is the only mode above 50, with the
best pairwise ordering accuracy (0.625 against 0.5 for chance), but it still
does not retrieve the best candidate.

The candidate pool is far better than earlier reports claimed: best-of-pool is
0.45–0.79 real TM-score, not the ~0.3 the internal metric suggested. That
number was a metric artifact, now corrected.

### Is it a retrieval stage instead?

A mode could be useless at picking one candidate yet still useful at shrinking
139 candidates to 20 for an expensive downstream scorer. Tested directly
(`retrieval_curve.csv`): **no mode survives multiple-comparison correction at
any k**. `contact` at k=50 looks strong (hit 0.80 against 0.375 random,
p=0.014) but needs to clear a Holm threshold of 0.0025 across the 20-comparison
grid. At the useful k values (k<=25) every mode is within noise of random.

The more useful finding is that **the benchmark is underpowered**. A paired
sign-flip test on n targets cannot go below p = 2^-n, so at n=10 almost nothing
can reach significance. A test in this repo shows that on 5 targets even a
*perfect* ranker fails to survive correction. `targets_needed` estimates that
detecting a +0.15 hit-rate gain at k=25 requires **~42 targets**; CASP15 RNA
provides 10.

So the next step is not another scoring function. It is more labelled targets.

This is an evaluation harness that measures honestly, plus a discovery
architecture. It is not a competitive structure-ranking method. See
[docs/CORRECTIONS.md](docs/CORRECTIONS.md) for five corrections to how results
were measured here; three of them corrected my own earlier fixes.

## Install

```bash
pip install -e ".[dev,ml]"
pytest                      # 178 tests
```

Requires Python 3.11+.

## Reproduce the evaluation

```bash
# Fetch the benchmark data (~674 MB, not stored in git)
python scripts/download_casp15_predictions.py
python scripts/download_casp15_natives.py

# Run the harness
python scripts/evaluate_structural_ensemble.py \
    --candidates-root data/casp15_rna/candidates \
    --out-dir reports/evaluation/casp15 \
    --dataset-name casp15 \
    --native-map data/casp15_rna/native_map.csv

python scripts/make_evaluation_digest.py \
    --eval-dir reports/evaluation/casp15 \
    --out reports/evaluation/casp15_expanded_digest.md
```

A smaller benchmark that needs no download:

```bash
python scripts/evaluate_structural_ensemble.py \
    --candidates-root data/real/candidates \
    --out-dir reports/evaluation/real --dataset-name real
```

## Run the discovery demo

```bash
python -m discovery.demo
```

Synthetic data, so it demonstrates the mechanism rather than a result.

## How to read the reports

In this order:

1. **`pick_diagnostics.csv`** — every mode against random selection from the
   same pools, tie-aware. If a mode is not above random, nothing else in the
   report matters.
2. **`retrieval_curve.csv`** — whether a mode keeps the best candidate in its
   top k better than random, with multiple-comparison correction.
3. **`score_ties.csv`** — the fraction of candidates each mode assigns an
   identical score. A mode that ties on most of its input is not ranking it; its
   top-k is decided by the tie-break. On CASP15, `low_clash` ties on **95.8%**.
4. **`oracle_hit_rate`** in `method_metrics.csv` — the fraction of targets where
   the genuinely best candidate is retrieved. This isolates ranking skill.
5. **`mean_best_of_k_quality`** — measures the candidate pool as much as the
   method. A weak pool caps it no matter how good the ranker is.

`tm_like` is an internal statistic, **not** official US-align TM-score. Do not
compare these numbers to published CASP results. See
[docs/METRICS.md](docs/METRICS.md).

## Layout

```
riborank/           evaluation harness
  structure.py        PDB reading, representative-atom traces
  geometry.py         geometric features, RMSD, tm_like, contact maps
  pipeline.py         manifest -> features -> native-derived labels
  scoring.py          five baseline modes, incl. size-plausibility
  ranking.py          regret, pairwise accuracy, ties, tie-aware vs-random
  report.py           markdown rendering

discovery/          staged discovery funnel  (docs/DISCOVERY.md)
  schema.py           Candidate / Evidence / StageRecord / AgentVerdict
  stages.py           cost-ordered pipeline, enforced cheapest-first
  scoring.py          novelty * coherence * reproducibility
  features/           sequence stats, repeat arrays, gene neighbourhoods
  agents/             LLM protocol, four adversarial roles, review
  demo.py             end-to-end run on synthetic data

scripts/            CLI entry points
tests/              178 tests, mostly offline
reports/            generated evaluation artifacts
docs/               METRICS, CORRECTIONS, DISCOVERY, VENDORED
```

## Known gaps

These are real and unhidden:

- **`data/real` cannot use the official metric.** It is entirely C4'-only, so
  US-align cannot parse it and it still reports `true_tm_like`. It is synthetic
  anyway and is a wiring check, not evidence.
- **Ten CASP15 targets, and that is the binding constraint.** `targets_needed`
  puts the requirement at ~42 for the effect sizes in play. At n=10 a perfect
  ranker would not clear multiple-comparison correction on a 20-cell grid, so
  no amount of modelling work can be validated here. More labelled targets are
  the prerequisite for everything else.
- **Sub-reports are stale.** Everything under
  `reports/evaluation/casp15/*/` was produced by scripts not yet ported onto
  `riborank.ranking`, so they still carry the pre-correction baseline. See the
  status table in [docs/CORRECTIONS.md](docs/CORRECTIONS.md). Those scripts also
  still use positional `sort_values(by, ascending)`, which breaks on pandas 3.
- **The group-calibration result was refuted by its own audit.** Masking the
  oracle group collapses it to zero and a shuffled-group control reaches 0.3 by
  chance. It was a group-ID shortcut, not structural signal. That audit is the
  best work in this repository and its conclusion stands.
- **`discovery/` has never touched real data.** No ingestion, no MMseqs2/HMMER
  adapters, no real LLM client.
- **No CI.** Tests run locally only.

## What was removed

`apps/web/` (3617 files of committed `node_modules` and build cache, zero source
files), the vendored `RhoFold/` checkout (39 MB, imported by nothing), and 674 MB
of regenerable CASP15 data were untracked. Details and the history-rewrite
recipe: [docs/VENDORED.md](docs/VENDORED.md).

## License

MIT.
