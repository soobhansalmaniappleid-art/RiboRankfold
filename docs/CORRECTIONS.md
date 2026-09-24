# Corrections

## 2026-09-24 — the `low_clash` baseline was a tie-breaking artifact

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
  `candidate_id` as the last key.
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
