# RiboRank

Two things live in this repository:

1. **`riborank/`** — an evaluation harness for *ranking* RNA 3D structure
   candidates. Given many predicted structures for one target, can a scoring
   function retrieve the best one?
2. **`discovery/`** — deterministic detectors and a staged funnel: sequence
   statistics, tandem repeat arrays, neighbourhood novelty, multiplicative
   scoring. See [docs/DISCOVERY.md](docs/DISCOVERY.md).
3. **`sde/`** — the Scientific Discovery Engine: a tool registry an agent may
   request from but cannot bypass, append-only candidate state, a dynamic
   investigation loop, adversarial review and an auditable report. RiboRank is
   one of its instruments. See [docs/ENGINE.md](docs/ENGINE.md).

The dependency runs one way: `sde` imports `riborank` and `discovery`; neither
imports `sde`.

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
*perfect* ranker fails to survive correction. `detectable_effect` puts it concretely: with 10 targets and the
20-comparison grid actually run, the smallest hit-rate gain this benchmark
could ever resolve is **+0.45**. `power_table` (written to every report) sizes
the alternative — detecting +0.15 under the same correction needs **90**
targets, not the 42 an uncorrected single test suggests.

So the next step is not another scoring function. It is more labelled targets.

This is an evaluation harness that measures honestly, plus a discovery
architecture. It is not a competitive structure-ranking method. See
[docs/CORRECTIONS.md](docs/CORRECTIONS.md) for six corrections to how results
were measured here; three of them corrected my own earlier fixes.

## Install

```bash
pip install -e ".[dev,ml]"
pytest                      # 288 tests
```

Requires Python 3.11+.

## The evaluation contract

Every benchmark emits `contract_candidates.csv` and `contract_summary.csv`,
validated before they are written: each row carries its `label_metric`, its
`tie_group_size` and its `benchmark_kind`, and the summary stores the random
reference beside the result. Adding a column ad hoc is rejected. See
[docs/CONTRACT.md](docs/CONTRACT.md).

`--benchmark-kind` is required and must be one of `prediction_pool`,
`experimental` or `controlled_decoy`. These are never averaged: on
`controlled_decoy` data `low_clash` beats random (0.618 vs 0.419), while on the
real CASP15 pool the same mode is indistinguishable from it.

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
    --native-map data/casp15_rna/native_map.csv \
    --benchmark-kind prediction_pool

python scripts/make_evaluation_digest.py \
    --eval-dir reports/evaluation/casp15 \
    --out reports/evaluation/casp15_expanded_digest.md
```

A smaller benchmark that needs no download:

```bash
python scripts/evaluate_structural_ensemble.py \
    --candidates-root data/real/candidates \
    --out-dir reports/evaluation/real --dataset-name real \
    --no-usalign --benchmark-kind controlled_decoy
```

## Run the demos

```bash
python -m discovery.demo   # the deterministic funnel
python -m sde.demo         # the full engine: loop, adversary, report
```

Both use synthetic data, so they demonstrate the mechanism rather than a result.
The engine demo ends by *refusing* to claim novelty, because the tool that would
settle it (`infernal_scan`) is not installed — which is the behaviour the design
exists to produce.

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
  ranking.py          regret, pairwise accuracy, ties, vs-random, power
  contract.py         the evaluation contract every benchmark must satisfy
  splits.py           target- and family-level folds, with leakage checks
  usalign.py          official US-align TM-score
  report.py           markdown rendering

discovery/          staged discovery funnel  (docs/DISCOVERY.md)
  schema.py           Candidate / Evidence / StageRecord / AgentVerdict
  stages.py           cost-ordered pipeline, enforced cheapest-first
  scoring.py          novelty * coherence * reproducibility
  features/           sequence stats, repeat arrays, gene neighbourhoods
  agents/             LLM protocol, four adversarial roles, review
  demo.py             end-to-end run on synthetic data

sde/                Scientific Discovery Engine  (docs/ENGINE.md)
  registry.py         tools an agent may request; whitelist, cost, inputs
  state.py            append-only candidate state and provenance log
  loop.py             observe -> hypothesise -> request -> execute -> stop
  adversary.py        four challenges that try to destroy the claim
  report.py           report generated from the event log alone
  tools/builtin.py    adapters over discovery/ and riborank/
  demo.py             end-to-end run on synthetic data

scripts/            CLI entry points
tests/              288 tests, mostly offline
reports/            generated evaluation artifacts
docs/               CONTRACT, METRICS, CORRECTIONS, DISCOVERY, ENGINE, VENDORED
```

## Known gaps

These are real and unhidden:

- **`data/real` cannot use the official metric.** It is entirely C4'-only, so
  US-align cannot parse it and it still reports `true_tm_like`. It is synthetic
  anyway and is a wiring check, not evidence.
- **Ten CASP15 targets, and that is the binding constraint.** At n=10 the
  smallest resolvable gain is +0.45, and a perfect ranker would not clear
  multiple-comparison correction on a 20-cell grid. No amount of modelling work
  can be validated here. More labelled targets are the prerequisite for
  everything else, and they must come as *three separate benchmarks* — real
  prediction pools, independent experimental structures, and controlled decoys
  — because averaging those kinds hides exactly the effect `data/real`
  demonstrates.
- **Sub-reports are stale.** Everything under
  `reports/evaluation/casp15/*/` was produced by scripts not yet ported onto
  `riborank.ranking`, so they still carry the pre-correction baseline. See the
  status table in [docs/CORRECTIONS.md](docs/CORRECTIONS.md). Those scripts also
  still use positional `sort_values(by, ascending)`, which breaks on pandas 3.
- **The group-calibration result was refuted by its own audit.** Masking the
  oracle group collapses it to zero and a shuffled-group control reaches 0.3 by
  chance. It was a group-ID shortcut, not structural signal. That audit is the
  best work in this repository and its conclusion stands.
- **The engine cannot find candidates, only investigate ones it is handed.**
  `hmmsearch` and `mmseqs_cluster` are declared but not installed, and they are
  the step that makes a billion-sequence space tractable. Neither `discovery/`
  nor `sde/` has touched real data.
- **No CI.** Tests run locally only.

## What was removed

`apps/web/` (3617 files of committed `node_modules` and build cache, zero source
files), the vendored `RhoFold/` checkout (39 MB, imported by nothing), and 674 MB
of regenerable CASP15 data were untracked. Details and the history-rewrite
recipe: [docs/VENDORED.md](docs/VENDORED.md).

## License

MIT.
