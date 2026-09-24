# RiboRank

Two things live in this repository:

1. **`riborank/`** — an evaluation harness for *ranking* RNA 3D structure
   candidates. Given many predicted structures for one target, can a scoring
   function retrieve the best one?
2. **`discovery/`** — a staged funnel for genomic discovery, where deterministic
   detectors run first and a language model runs last. See
   [docs/DISCOVERY.md](docs/DISCOVERY.md).

## Status, stated plainly

**No scoring mode here beats picking candidates at random on real predictions.**

On CASP15 (10 targets, ~139 candidates each), measured tie-aware against the
exact random expectation:

| mode | best-of-5 | vs random (0.139; 95%: 0.083–0.204) | top-1 pick percentile |
|---|---:|---|---:|
| `plausibility` | 0.097 | within | **56.9** |
| `low_clash` | 0.147 | within (it is random: 96% of scores tie) | 49.8 |
| `contact` | 0.062 | **below** | 40.2 |
| `compact` | 0.060 | **below** | 41.0 |
| `hybrid` | 0.059 | **below** | 43.5 |

No mode ever ranks the best candidate first. The features carry real but
weak signal: pairwise ordering accuracy is 0.61–0.66, against 0.5 for chance.
But the original modes reward compactness without limit, so their top pick
is a collapsed structure. `plausibility` removes that failure. It gives the
best typical pick of any mode but does not find the best candidate.

This is an evaluation harness that measures honestly, plus a discovery
architecture. It is not a competitive structure-ranking method. See
[docs/CORRECTIONS.md](docs/CORRECTIONS.md) for three successive corrections
to how results were measured here; the second and third correct the earlier fixes.

## Install

```bash
pip install -e ".[dev,ml]"
pytest                      # 143 tests
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
2. **`score_ties.csv`** — the fraction of candidates each mode assigns an
   identical score. A mode that ties on most of its input is not ranking it; its
   top-k is decided by the tie-break. On CASP15, `low_clash` ties on **95.8%**.
3. **`oracle_hit_rate`** in `method_metrics.csv` — the fraction of targets where
   the genuinely best candidate is retrieved. This isolates ranking skill.
4. **`mean_best_of_k_tm_like`** — measures the candidate pool as much as the
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
tests/              143 tests, no network required
reports/            generated evaluation artifacts
docs/               METRICS, CORRECTIONS, DISCOVERY, VENDORED
```

## Known gaps

These are real and unhidden:

- **`tm_like` is not TM-score.** Replacing it with official US-align output is
  the highest-value change available. Not done.
- **Ten CASP15 targets.** Every conclusion rests on 10 labelled targets. That is
  too few to support a strong claim about anything.
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
