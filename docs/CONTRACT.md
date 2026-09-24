# The evaluation contract

Every benchmark writes the same two tables, validated before they are saved:
`contract_candidates.csv` and `contract_summary.csv`. `riborank/contract.py`
defines them and refuses anything that does not fit.

This exists because this repository has invalidated its own results four times
(docs/CORRECTIONS.md) — twice through a tie-break, once through a metric, once
through a hard-coded number. Each time, stored results could not be
re-interpreted, because they did not record the thing that turned out to matter.

## What every candidate row records

| column | why it is mandatory |
|---|---|
| `contract_version` | a reader can refuse a table it does not understand instead of guessing |
| `benchmark`, `benchmark_kind` | results from different kinds must never be averaged |
| `target_id`, `candidate_id` | identity |
| `method` | which scoring mode produced this ordering |
| `label_metric` | **per row.** A table can never be half official TM-score and half internal approximation |
| `label` | the measured quality, or empty |
| `rank` | 1-based position under that method |
| `selected` | whether it made the top-k |
| `tie_group_size` | how many candidates shared its score |
| `labelled` | whether a label exists, kept separate from its value |

Two of these are the direct product of past failures.

**`label_metric` is per row, not per file.** The metric change
(`tm_like` → `usalign_tm`) moved best-of-pool from ~0.32 to 0.45–0.79. Any
stored number without its metric attached is unusable.

**`tie_group_size` travels with every selection.** `low_clash` ties 96% of
CASP15 candidates, and its reported score moved between 0.039, 0.116 and 0.201
purely through tie-breaking. A rank stored without its tie group cannot be
audited afterwards.

**`labelled` is separate from `label`.** Validation rejects a row marked
labelled with no label, and a row marked unlabelled that carries one. An
unscoreable candidate is never silently a zero, which would rank a broken file
above a genuinely poor structure.

## What the summary records

`n_targets`, `n_candidates`, `label_coverage`, `mean_selected_label`,
`mean_oracle_label`, `selected_percentile`, `pairwise_accuracy`, `random_top1`,
`random_best_of_k`, `mean_best_of_k`, the interval, and a `verdict` against
random selection.

The random reference is stored **in the same row** as the result. A method's
number alone means nothing, and keeping the comparison in a separate file is how
it gets dropped when someone quotes the result.

`mean_selected_label` is computed from the candidate table rather than
recomputed, so a summary can never disagree with the rows it summarises.

## Schema changes

Adding a column ad hoc is rejected. Extend `CANDIDATE_COLUMNS` or
`SUMMARY_COLUMNS` and bump `CONTRACT_VERSION`. Old tables then fail validation
loudly instead of being silently misread — which is the point.

## Three benchmarks, never merged

`benchmark_kind` is required and has three values. They answer different
questions:

| kind | what it is | what it answers |
|---|---|---|
| `prediction_pool` | real predictions for a target (CASP15) | does this work on what predictors actually produce? |
| `experimental` | independent experimental structures with candidates | does it generalise, and can n be raised? |
| `controlled_decoy` | perturbations of a known structure | ablation: what do the features actually detect? |

`data/real` is the cautionary example. It is `controlled_decoy`: native plus
noise-perturbed copies. There, `low_clash` beats random (0.618 vs 0.419),
because rejecting visibly broken structures is enough when the decoys were made
by breaking a good one. On CASP15 the same mode is indistinguishable from
random. Averaging the two would have produced a number describing neither, and
the favourable one would have been the one quoted.

`controlled_decoy` is good for development and useless as evidence. Keep it, run
it, and never cite it as a result.

## Statistical power is part of the contract

Every report carries `power_table.csv`, generated, never written by hand.

`targets_needed` takes `comparisons` and splits alpha across them, because a
benchmark is never sized for one isolated test — a grid of modes against k
values is what actually gets run. Sizing for one test and then testing with
twenty understates the requirement by about half.

`detectable_effect` asks the inverse and more useful question: given the targets
that exist, what improvement would have to be true before this benchmark could
show it? For CASP15 today — 10 targets, 20 comparisons — the answer is **+0.45**.
Nothing smaller than that can be demonstrated here, no matter how good it is.

## Splits hold out whole targets

`riborank/splits.py` builds folds that group by target, and `check_leakage`
refuses any split that shares a group between train and test.

A candidate-level split is the standard way to get an encouraging number from a
reranker that has learned nothing. Candidates for one target are near-copies of
each other, so putting some in train and others in test lets a model recognise
the target instead of judging the structure. On CASP15 a random 1000/355
candidate split shares **all ten** targets across both sides; `check_leakage`
names them and raises.

Where homologous targets exist, use `family_level_folds`. Holding out one
member of a family while training on another is the same failure one level up.
`assign_families` raises on an unmapped target by default rather than treating
it as a singleton, because a silent singleton is how a homologue gets split.

Two refusals are deliberate:

- A fold with an empty test side raises. It would otherwise report the training
  score, which reads as an excellent result.
- Requesting more folds than there are groups raises, rather than producing
  folds that cannot test anything. If every target is one family, a
  family-level split correctly refuses to exist.

These are unused so far: there is no learned reranker in this repository yet,
and at n=10 there could not usefully be one. They are here so that when a model
does arrive, the split it is judged on is not the thing that has to be trusted.
