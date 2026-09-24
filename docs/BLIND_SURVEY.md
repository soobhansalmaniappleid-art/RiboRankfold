# The blind survey benchmark

## What this is, and what it is not

A synthetic corpus of 65 reverse-transcriptase-associated loci. Three of them
hide a conserved unit repeated at near-constant spacing. The engine is given one
generic instruction:

> Survey these reverse-transcriptase-associated genomic systems and identify
> unusual, previously uncharacterised systems worth investigating.

Nothing in the corpus, the question, the tools' selection or the ranking code
mentions repeats, arrays, CRISPR, spacing or periodicity. A test asserts this by
reading the source of the ranking function and failing if any of those words
appear in it. Putting the answer in the question is the easiest way to build a
demo that proves nothing.

**This is not Anthropic's data and this is not a reproduction of their result.**
The dataset behind their reported work has not been published in a form anyone
could download, so no corpus assembled here could be that corpus. What this
benchmark can honestly test is whether *this* engine's generic machinery
surfaces an unusual locus without being told what kind of unusual to look for.

## Why the corpus is built to be hard

A corpus of ordinary loci plus one array is trivial — anything noticing *any*
irregularity wins. So 14 of the 65 loci are confounders designed to defeat the
lazy heuristics:

| confounder | defeats |
|---|---|
| low-complexity regions (`AT` repeats) | "low entropy is interesting" |
| homopolymer runs | the same, and they are often sequencing artifacts |
| extreme GC bias | entropy shifts that mean nothing |
| a motif recurring at **irregular** spacing | "this sequence recurs, therefore array" |
| 8 known architectures | a novelty-seeker must rank these *down*, not up |

The dispersed-motif confounder needed fixing during development: with uniform
random gaps it occasionally produced a near-regular run (period CV 0.085),
making it a second planted locus rather than a decoy. It now uses bimodal gaps,
and the CV across seeds is 0.56–0.71. A test enforces this — without it the
benchmark would have been quietly measuring something easier than it claimed.

## Two arms

**Arm A — deterministic sweep.** Every cheap tool on every locus, then rank by
distance from the cohort. Tests the *machinery*.

**Arm B — budgeted agent.** A budget too small to run everything, so the agent
must choose which analysis to request. Tests *judgement*.

## Results

### Arm A, ten seeds

| | |
|---|---|
| median rank of the best planted locus | **1** of 65 |
| median rank of the worst planted locus | **21** of 65 |
| mean top-10 recall | **0.77** (random: 0.15) |
| known systems promoted into the top 10 | 0–1 |
| confounders above the worst planted locus | 0 or 10, depending on the seed |

The machinery works, with a real limit. One planted locus reaches rank 1 on
every seed tested. But the *other* planted loci are frequently buried: on half
the seeds, ten confounders rank above the worst planted locus. Generic anomaly
scoring finds *an* unusual thing reliably; it does not cleanly separate the
interesting kind of unusual from the boring kind.

### Arm B, the honest floor

The baseline investigator (`CheapestFirstInvestigator` — run the cheapest unused
tool, never look at what came back) **fails completely**:

| | |
|---|---|
| planted ranks | 30, 31, 35 of 65 |
| top-20 recall | **0%** |
| requested the decisive analysis | **0 of 3** |

It spent its budget on `sequence_stats` and `repeat_detail`. `repeat_detail`
returns a list of arrays rather than numeric features, so it contributed nothing
to the ranking at all — the budget bought a result that could not be scored.

This is the most useful number in the benchmark. It is the floor a model has to
beat, and it says plainly what is missing: **a policy for choosing which
analysis would explain an anomaly**. Arm A succeeds only because it runs
everything, which does not scale to a real corpus and is not judgement.

## Discovery is a rate, not an event

The most useful thing Anthropic published about ART is not 949 agents or 210
million tokens. It is that they re-ran the same campaign ten more times and
**no rerun read the DNA upstream of the enzyme; all ten missed the array**.

That makes the discovery roughly **1 in 11**, and it reframes the whole problem.
A discovery engine is not a function that returns a finding — it is a process
with a rate, and one successful run says almost nothing about that rate.

`sde.benchmarks.rate` measures ours the same way, with a Wilson interval
(the normal approximation collapses to a point at zero successes and would imply
certainty this data cannot support). Configuration: one planted locus among 201,
criterion = planted locus in the top 10, corpus varied per run.

| arm | discovery rate | 95% interval | requested the decisive analysis |
|---|---:|---|---:|
| A — full sweep | **9/11 = 0.82** | [0.52, 0.95] | 1.00 |
| B — budgeted agent | **6/11 = 0.55** | [0.28, 0.79] | **0.55** |
| *reference: Anthropic ART* | *1/11 = 0.09* | *[0.02, 0.38]* | — |

Two things in this table matter.

**The misses are not near-misses.** Ranks are bimodal: 1, or 23–65. The engine
either sees the locus immediately or loses it entirely. There is no gradual
degradation, which means a threshold-tuning exercise would not help.

**Arm B's failures line up exactly with its tool choices.** Every run that
missed also scored `decisive 0/1` — it never requested the repeat analysis. Every
run that found it had requested it. The ranking is not the bottleneck; the
decision about what to measure is.

### Our rate is higher than theirs, and that is not good news

0.82 and 0.55 against 0.09 does **not** mean this engine is better than the one
that found ART. It means this benchmark is far easier:

- the corpus is synthetic and the planted signal is cleaner than a real locus
- 201 loci, not 1.9 billion protein clusters
- the loci are already filtered to be RT-associated — the step that makes the
  real problem hard has been done for us

`DiscoveryRate.render()` prints this warning automatically whenever a rate sits
clear of the published reference, and a test asserts the wording, because a
number above the reference should prompt a harder benchmark rather than a claim.

## What is still untested

No model is connected in this repository, so the question the benchmark exists
to ask — *would an agent, seeing an unusual locus, request the analysis that
explains it?* — has not been answered. It can be: pass an `LLMInvestigator` into
`BudgetedSweep` and score it against the same corpus and the same floor.

Success should not be scored as "did it find the array". The criteria are:

1. Does the planted locus reach the top N?
2. Does the agent request the decisive analysis unprompted?
3. Does it connect the anomaly to the adjacent RT?
4. Does it compare against known systems?
5. Does it reach a structural hypothesis without a hint?
6. Can the adversarial review refute it?

A failure on any of these is a more useful result than a passing demo, because
it names which part of the architecture is absent rather than awarding a medal
for a diagram.

## Running it

```python
from sde.benchmarks import Corpus, deterministic_sweep, score_survey

corpus = Corpus.build(seed=2026)
print(score_survey(corpus, deterministic_sweep(corpus)).render())
```
