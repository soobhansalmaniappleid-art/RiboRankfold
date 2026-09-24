# Corrections

## 2026-09-24 — the `low_clash` baseline was a tie-breaking artifact

> **Partly superseded.** The diagnosis below (95.8% of scores tied, so the
> reported number came from the sort order) is correct. The claim that
> `low_clash` "falls from best to worst" is **not**: 0.039 was a second
> tie-break artifact. See the third entry, which computes the tie-aware value
> (0.147, the same as random selection).

### What was claimed

Every evaluation report in this repository reported `low_clash` as the strongest
baseline scoring mode. From `reports/evaluation/casp15_expanded_digest.md`:

> Best top-5 TM-like mode is `low_clash` with mean best-of-5 TM-like `0.116176`.

The same 0.116176 figure was carried into
`reports/evaluation/casp15/unseen_group_validation/`,
`reports/evaluation/casp15/source_invariant_*/` and
`reports/evaluation/casp15/group_calibration_audit/`, where it served as the
baseline that learned rerankers had to beat.

### What is actually true

`score_low_clash` is built only from `clashes_per_residue` and
`backbone_break_fraction`. On CASP15, most candidates have exactly zero of both,
so they receive an identical score:

| method    | candidates | distinct scores | tied fraction |
|-----------|-----------:|----------------:|--------------:|
| low_clash |       1392 |          **58** |     **0.958** |
| contact   |       1392 |            1174 |         0.157 |
| hybrid    |       1392 |            1185 |         0.149 |
| compact   |       1392 |            1185 |         0.149 |

1392 candidates collapse onto 58 distinct scores. The top-5 for `low_clash` was
therefore chosen almost entirely by `sort_values`' internal ordering among tied
rows, which is neither stable nor specified.

This was caught while porting the harness to a newer pandas: re-running the
*identical logic* on the `real` benchmark moved the `low_clash` oracle hit rate
from 0.675 to 0.725. Nothing in the method had changed.

After making every ordering deterministic (stable sort, `candidate_id` as the
final tie-break), the CASP15 ranking inverts:

| method    | mean best-of-5 tm_like — as reported | deterministic |
|-----------|-------------------------------------:|--------------:|
| low_clash |                           **0.116176** | **0.039429** |
| contact   |                             0.061739 |      0.061739 |
| compact   |                             0.059528 |      0.059528 |
| hybrid    |                             0.058878 |      0.058878 |

`low_clash` goes from best to **worst**. The other three modes are unaffected to
within floating-point noise, because they barely tie.

Pairwise accuracy already told this story and was overlooked: `low_clash` scores
**0.084**, far below chance, while the other modes sit at 0.63–0.66. A mode
cannot be simultaneously the best top-5 retriever and a below-chance pairwise
ranker. The contradiction was the tie artifact showing through.

### What this changes

- `low_clash` is a **filter**, not a ranker: "reject structures with visible
  geometric defects, then pick arbitrarily". It is still useful in that role.
- The comparisons in the sub-reports that used `low_clash = 0.116` as the bar to
  clear were measuring against an inflated baseline. Rerankers reported as
  roughly matching or slightly beating it (e.g. `invariant_rf` at 0.106,
  `invariant_ensemble` at 0.108) in fact beat the corrected baseline of 0.039 by
  a wide margin. **This correction is favourable to those results**, but they
  must be regenerated before the new numbers are quoted.
  *Superseded:* the right yardstick is random selection (0.139 best-of-5,
  95% interval 0.083–0.204). Against that, 0.106 and 0.108 are within random,
  not above it.
- It does **not** rescue the headline conclusion. `oracle_hit_rate` remains 0.0
  for all four baselines on CASP15. The rankers still do not work.

### Status of affected reports

| path | status |
|---|---|
| `reports/evaluation/casp15/{summary,method_metrics,per_target_metrics,features,score_ties}` | regenerated, correct |
| `reports/evaluation/casp15_expanded_digest.md` | regenerated, correct |
| `reports/evaluation/real/*` | regenerated, correct |
| `reports/evaluation/casp15/contact_topology_model_selection*/` | **stale** |
| `reports/evaluation/casp15/group_calibrated/` | **stale** |
| `reports/evaluation/casp15/group_calibration_audit/` | **stale** |
| `reports/evaluation/casp15/group_diagnostics/` | **stale** |
| `reports/evaluation/casp15/source_invariant_*/` | **stale** |
| `reports/evaluation/casp15/topology_signal_audit*/` | **stale** |
| `reports/evaluation/casp15/unseen_group_validation/` | **stale** |

The stale reports come from scripts that have not yet been ported onto
`riborank.ranking` and still do their own sorting. They carry the old baseline.
Porting them is tracked in the README's "Known gaps".

### Guard against recurrence

- `riborank.ranking.rank_by_score` and `_sort_by_oracle` use `kind="stable"` with
  a hash of `candidate_id` as the last key. The first version of this guard
  used `candidate_id` directly, which caused the second correction below.
- `riborank.ranking.tie_diagnostics` computes the tied fraction per mode, and it
  is written to `score_ties.csv` and printed in every generated report *above*
  the metrics table.
- `tests/test_ranking.py::test_selection_is_deterministic_under_massive_ties`
  shuffles the input rows and asserts the output is unchanged.

### The general lesson

The audits already in this repository (`group_calibration_audit`,
`topology_signal_audit`) were built to catch a model exploiting a shortcut, and
they worked — the shuffled-group control correctly demolished the group
calibration result. But no audit was pointed at the **baselines**. A control that
only interrogates the thing you hope is working will not catch a broken number in
the thing you assume is trivial.

## 2026-09-24 — the first tie-break fix leaked labels through filenames

### What happened

The fix above made every ordering deterministic by using `candidate_id` as the
final sort key. That is deterministic, but it isn't neutral. Filenames record
how candidates were generated, and alphabetical order follows those names.

In the synthetic `real` benchmark, each target's decoys are named
`decoy_001_small_noise`, `decoy_002_medium_noise`, and so on. The least
perturbed decoy sorts first. `low_clash` ties across a median of 8 candidates
at its top score, so an alphabetical tie-break handed it `decoy_001_small_noise`
on 27 of 40 targets.

| tie-break | `low_clash` hit@1 on `real` |
|---|---:|
| `candidate_id`, A→Z | 0.625 |
| `candidate_id`, Z→A | **0.000** |
| SHA-256 of `candidate_id` | **0.000** |

The score was identical in all three rows. The whole 0.625 came from the
filenames.

### Fix

The tie key is now the SHA-256 hash of `candidate_id`
(`riborank.ranking.tie_key`). It is reproducible, and it has no relationship to
how files are named. `tests/test_random_baseline.py::
test_tie_break_does_not_follow_candidate_names` builds 40 targets whose names
sort in quality order and asserts that a fully tied mode does not recover that
order. Under the alphabetical key the test would score 1.0; under the hash it
must stay near chance (0.1).

### Lesson

A tie-break is part of the model whenever ties are common. It has to be chosen
to carry no information, and "deterministic" doesn't guarantee that.

## 2026-09-24 — any single tie-break is arbitrary; metrics are now tie-aware

### What was wrong with the first two fixes

Both earlier fixes chose *one* ordering for tied candidates. When 96% of scores
tie, that choice decides the result. The same `low_clash` score on CASP15 has
been reported as:

| tie-break | best-of-5 |
|---|---:|
| unspecified pandas order (original reports) | 0.116 |
| `candidate_id` A→Z (first fix) | 0.039 |
| SHA-256 of `candidate_id` (second fix) | 0.201 |

None of these values says anything about the score. It only fixes an order
between *distinct* values, and every order within a tied group is equally
justified.

### Fix

`riborank.ranking.tie_aware_pick` computes each pick statistic as its
expectation over every ordering of tied candidates, exactly:

- **best-of-k:** the groups wholly inside the top k contribute their maximum.
  The group that straddles the cut contributes the exact expected maximum of a
  random m-subset of it.
- **hit@k:** 1 if the best candidate is in a group wholly inside the top k,
  `m / group size` if it is in the straddling group, otherwise 0.
- **percentile of pick:** the mean over the top-scoring group.

Random selection is the special case where every candidate ties, so it goes
through the same code. Tests check that:

- results match brute-force enumeration of every valid ordering,
- a fully tied mode scores exactly the same as random,
- renaming every candidate leaves every statistic unchanged.

`pick_diagnostics.csv`, the first table in each report, uses this. The
older `oracle_hit_rate` in `method_metrics.csv` still uses the single hash
ordering; read it together with `score_ties.csv`.

### What is now true on CASP15

| mode | best-of-5 | verdict | pick percentile | hit@25 |
|---|---:|---|---:|---:|
| random (exact) | 0.139 | reference (95%: 0.083–0.204) | 49.8 | 0.181 |
| `low_clash` | 0.147 | within random | 49.8 | 0.203 |
| `plausibility` | 0.097 | within random | **56.9** | **0.000** |
| `contact` | 0.062 | **below random** | 40.2 | 0.500 |
| `compact` | 0.060 | **below random** | 41.0 | 0.300 |
| `hybrid` | 0.059 | **below random** | 43.5 | 0.500 |

- `low_clash` does not rank on CASP15. It is indistinguishable from random.
- `hybrid`, `contact` and `compact` are genuinely worse than random at the
  top. They barely tie, so no tie-break changed them. Their pick is a collapsed
  structure (on R1138, 720 nt with Rg 14.3 Å against a pool median of 62.6 Å).
- `plausibility` fixes the collapse. Its top pick is the best of any mode, but
  it never puts the best candidate in the top 25, while random does 18% of the
  time. It moves the typical pick up and the best one down.
- No mode beats random selection on CASP15.

On the synthetic `real` benchmark, `low_clash` (0.618) and `plausibility`
(0.516) beat random (0.419). Those decoys are perturbations of the native,
and filtering out visibly broken ones is enough to help. That doesn't carry
over to real prediction pools.

### A negative result, recorded so it is not retried blindly

Hypothesis: `plausibility` misses the best candidate because its size target
is fitted on the candidate pools, which are mostly poor predictions. Test:
fit the size law on the 45 native chains in `data/real` instead. Those are
different RNAs, so no CASP15 information is used.

Result: worse. Best-of-5 fell to 0.060, below random. The native chains are
10–94 nt, so the law is extrapolated far past its data for CASP15 targets of
up to 720 nt. The best CASP15 candidates are also slightly more compact than
the typical candidate under either law (mean log(Rg / expected) −0.09 vs 0.00
under the pool law). The right size target seems to lie between "typical
prediction" and "collapsed". A size law fitted on long native RNAs would be
needed to test this properly. The shipped mode keeps the pool-fitted law.

## 2026-09-24 — the "weak candidate pool" was a metric artifact

### What changed

`riborank/usalign.py` now runs the official US-align binary, and CASP15 is
labelled with real TM-score (`usalign_tm`) instead of the internal `tm_like`
approximation. 1355 of 1392 candidates are scored; the rest are C4'-only traces
US-align cannot parse (docs/METRICS.md).

### What was wrong

Every earlier report in this repository concluded that the candidate pool was
almost worthless. `reports/evaluation/casp15_expanded_digest.md` reported a
best-of-pool around 0.32 and a median candidate around 0.036, and the README
said the ranker had little to find.

Under the official metric, best-of-pool per target is **0.45–0.79** and the
median candidate is **0.20–0.42**.

| target | `tm_like` best | official TM best |
|---|---:|---:|
| R1116 | 0.081 | **0.668** |
| R1136 | 0.459 | 0.748 |
| R1128 | 0.617 | 0.785 |
| R1138 | 0.200 | 0.650 |

`tm_like` applied the TM-score formula to one global RMSD, so a few badly
placed residues sank the whole score. The two metrics correlate at only
rho = 0.69 within a target and disagree on which candidate is best for 4 of 10
targets, so `tm_like` was not even a usable stand-in ordering.

### What this changes

- **The pool was never the problem.** There are genuinely good candidates to
  find; nothing was excusing the rankers.
- **The rankers look worse, not better.** With a correct metric, the top-1 pick
  of `hybrid`, `contact` and `compact` sits at percentile **13–16** instead of
  40–43. They are far below random, not slightly below.
- **`plausibility` is the only mode above random on the top-1 pick**
  (percentile 57.1) and has the best pairwise accuracy (0.625). It is still
  within the random interval on best-of-5.
- The conclusion that no mode beats random selection survives the metric change.

### Status of the `real` benchmark

`data/real` is entirely C4'-only, natives included, so it cannot be scored with
US-align and still reports `true_tm_like`. Its reports carry a warning. It is
synthetic anyway (native plus perturbed decoys) and should not be cited as
evidence about real prediction pools.

### Lesson

Three previous corrections here were about how candidates were *ordered*. This
one was about how they were *measured*, and it moved more than all the others
combined. A homemade metric that looks like a standard one, and correlates with
it at rho = 0.69, is not a stand-in for it — it is a different quantity with a
misleading name.

## 2026-09-24 — the retrieval hypothesis, tested and not supported

### The hypothesis

A mode can be useless at picking one candidate and still be useful at shrinking
139 candidates to 20 for an expensive downstream scorer. Pairwise accuracy is
0.58–0.63, clearly above chance, so the information might survive into top-k
even though argmax fails. If so, RiboRank is a retrieval stage, not a predictor.

### The test

`riborank.ranking.retrieval_curve` reports, per (mode, k), the tie-aware hit@k,
the exact random expectation, a bootstrap interval, a paired sign-flip
permutation p-value, and Holm-Bonferroni correction across the whole grid.

### The result

**No (mode, k) survives correction.** On CASP15, k = 10, 25, 50, 75:

| mode | k | hit@k | random | delta | p | survives |
|---|---:|---:|---:|---:|---:|---|
| `contact` | 50 | 0.800 | 0.375 | +0.425 | 0.014 | no |
| `contact` | 75 | 0.900 | 0.562 | +0.338 | 0.010 | no |
| `compact` | 75 | 0.800 | 0.562 | +0.238 | 0.050 | no |
| `contact` | 25 | 0.300 | 0.187 | +0.113 | 0.210 | no |
| `plausibility` | 25 | 0.100 | 0.187 | −0.087 | 0.756 | no |

`contact` at k = 50 and 75 is the only thing that looks real, and it is exactly
what a 20-comparison grid on 10 targets produces by chance. Its raw p of 0.014
needs to clear a Holm threshold of 0.0025.

At the k values that would actually be useful — k ≤ 25, a 5x reduction — every
mode is within noise of random, and `plausibility` is below it.

### The more useful finding: the benchmark is underpowered

A paired sign-flip test on *n* targets cannot produce a p-value below 2^−n. With
10 targets the floor is 0.001, so across a 20-comparison grid almost nothing can
reach significance however good it is.
`tests/test_random_baseline.py::test_a_small_benchmark_cannot_detect_even_a_perfect_ranker`
makes this concrete: on 5 targets, a **perfect** ranker fails to survive
correction.

`riborank.ranking.targets_needed` sizes the fix. Detecting a +0.15 hit-rate gain
at k = 25 over a 0.187 baseline, at 80% power, needs **≈42 targets**. CASP15 RNA
provides 10.

So the next step for RiboRank is not another scoring function. It is more
labelled targets — CASP16 RNA, RNA-Puzzles, or decoy sets built from PDB
structures — because at n = 10 the benchmark cannot distinguish a good reranker
from a lucky one.
