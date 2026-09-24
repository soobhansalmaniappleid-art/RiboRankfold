# Metrics: what they are, and what they are not

## `tm_like` is not TM-score

`riborank.geometry.tm_like` applies the TM-score functional form

```
d0    = max(1.0, 1.24 * (L - 15)^(1/3) - 1.8)
score = 1 / (1 + (RMSD / d0)^2)
```

to a **single global RMSD** produced by Kabsch superposition of the best
chain/window pair. Real TM-score (US-align, TM-align) optimises an alignment and
sums a per-residue term:

```
TM = (1/L) * max over alignments of  sum_i 1 / (1 + (d_i / d0)^2)
```

The two are not the same statistic and do not agree numerically. In particular
`tm_like` is dominated by the worst-fitting residues, because a single large
deviation inflates the global RMSD, whereas TM-score down-weights them.

**Consequence:** every `tm_like` number in `reports/` is internally comparable
across candidates and methods in this repository, and is *not* comparable to any
published CASP TM-score. Do not put these numbers in a table next to CASP
results.

Replacing `tm_like` with official US-align output is the single highest-value
change available to this project. It is not done yet.

## `multi_metric_quality`

A hand-weighted blend, not a learned or validated objective:

```
0.65 * tm_like + 0.30 * contact_map_f1 - 0.05 * min(clashes_per_residue, 1.0)
```

The weights were chosen by hand. They have not been fit or ablated. Treat it as
a second oracle definition used to check that conclusions are not an artifact of
`tm_like` alone, not as a quality measure in its own right.

## Tie-breaking

`score_low_clash` is built from `clashes_per_residue` and
`backbone_break_fraction`. On the benchmarks in this repository, a majority of
candidates have **exactly zero** clashes and zero backbone breaks, so they
receive an identical score:

| benchmark | method    | candidates | distinct scores | tied fraction |
|-----------|-----------|-----------:|----------------:|--------------:|
| real      | low_clash |       1367 |             489 |         0.642 |
| real      | contact   |       1367 |            1263 |         0.076 |
| real      | hybrid    |       1367 |            1367 |         0.000 |

This matters because `low_clash` is the **best-scoring baseline in every report
in this repository**. Its top-5 was previously selected by `sort_values` without
a tie-break, so which of the ~64% tied candidates landed in the top 5 was decided
by the sort implementation. Re-running the identical code under a different
pandas version moved the `real` benchmark's `low_clash` oracle hit rate from
0.675 to 0.725 with no change in logic.

Every ordering in `riborank.ranking` now uses a stable sort with a tie key.
The key has to satisfy two conditions, and the first attempt only met one:

1. **Deterministic**, so results do not depend on the pandas version.
2. **Uninformative**, so the tie-break cannot carry signal.

The first fix used `candidate_id` itself, which is deterministic but not
uninformative. Filenames encode how candidates were made: in the synthetic
`real` benchmark, `decoy_001_small_noise` sorts before every other decoy, so a
mode that tied on everything "found" the least-perturbed decoy. `low_clash`
reached hit@1 = 0.625 that way. Reversing the alphabetical order dropped it
to **0.000**, with the score unchanged.

The tie key is now a SHA-256 hash of `candidate_id`: reproducible, and
unrelated to how anyone names files.
`tests/test_random_baseline.py::test_tie_break_does_not_follow_candidate_names`
builds 40 targets whose names sort in quality order and checks that a fully tied
mode does not inherit that order.

The underlying point stands and is reported alongside the metrics:

> **A scoring mode that ties on most of its input is not ranking. Read
> `score_ties.csv` before reading `method_metrics.csv`.**

`low_clash` should be understood as "reject structures with visible geometric
defects, then pick arbitrarily", which is a useful filter and not a ranker.

## Compare against random selection first

`pick_diagnostics.csv` puts every mode next to picking candidates at random
from the same pools. It is the first section of every generated report.

| column | meaning | random expectation |
|---|---|---|
| `mean_percentile_of_pick` | where the top-1 pick sits in its pool; 100 is the best candidate | 50 (exact) |
| `hit@k` | share of targets whose best candidate is in the top k | `k / pool size` (exact) |
| `best_of_k` | mean quality of the best candidate in the top k | exact, from the order statistics |
| `verdict` | `best_of_k` against the 95% interval of random selection | — |

The expected best of `k` random draws is computed exactly. With the pool sorted
ascending, the i-th value is the maximum of a random k-subset with probability
`C(i-1, k-1) / C(n, k)`. A test checks this against brute-force enumeration of
every subset. The interval comes from seeded resampling and is used only for the
verdict.

Until this table existed, no report here said what random selection would
score. On CASP15 most modes are below it.

## `oracle_hit_rate` is the headline

`mean_best_of_k_tm_like` measures the pool as much as the method. A weak pool
caps it regardless of how good the ranker is. `oracle_hit_rate` — the fraction of
targets where the genuinely best available candidate is retrieved into the top-k
— is the number that isolates ranking skill. Report both; lead with the hit rate.
