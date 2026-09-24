# Scientific Discovery Engine (`sde/`)

An independent engine. RiboRank is one of its instruments, not its core:

```
                 Scientific Discovery Engine
                              |
                    Candidate Discovery
                              |
             +----------------+----------------+
             |                |                |
            RNA           Proteins          Genomes
             |                |                |
       RiboRank-Fold      MMseqs2          Context
             |                |                |
             +----------------+----------------+
                              |
                       Feature Engine
                              |
                     Novelty / Anomaly
                              |
                         Agent Loop
                              |
                    Next Investigation
                              |
                    Adversarial Review
                              |
                       Final Finding
```

The dependency runs one way: `sde` imports `riborank` and `discovery`; neither
imports `sde`.

```bash
python -m sde.demo
```

## The boundary that defines this design

**An agent cannot run code.** It emits a request naming a registered tool:

```json
{"tool": "infernal_scan",
 "reason": "rule out a described structured RNA family",
 "inputs": {"sequence": "..."}}
```

The orchestrator decides whether to run it, pays for it, and records what came
back. That split is the difference between a system a scientist can audit and a
model with shell access.

`ToolRegistry` enforces three things rather than documenting them:

| property | what it prevents |
|---|---|
| whitelist | a request naming an unregistered tool is refused *and recorded* — what the agent tried is part of the record |
| declared cost | the orchestrator holds a budget, so an investigation cannot become a thousand sessions re-reading the same FASTA |
| declared inputs | a request missing a required field fails before anything runs |

A tool that raises becomes a recorded failure, not an exception. One broken tool
must not discard everything learned before it.

## The investigation loop

```
observe -> hypothesise -> request evidence -> execute -> update -> stop?
```

Loops like this fail in three ways, and each has a guard:

- **Never stops** → bounded by iterations, by budget, and by a
  no-new-evidence counter.
- **Goes in circles** → a repeated tool call with identical inputs is refused
  and recorded. Asking again is not a strategy.
- **Spends everything on one candidate** → the budget is per candidate and
  declared up front.

Two refusals are worth stating plainly:

**A hypothesis without a test is rejected.** `Hypothesis` requires
`discriminating_evidence` — what observation would tell it apart from the
alternatives. A claim nobody can imagine testing is not carried forward as if it
were science. The rejection is logged, not silent.

**An unparseable agent reply stops the loop.** It never becomes a guessed step.

## Adversarial review

Four challenges, each asked to destroy the claim: `already_described`,
`assembly_artifact`, `chance`, `distant_homology`. A second agent asked "do you
agree?" will agree, and that agreement carries no information.

- Refutation outweighs endorsement (`REFUTATION_WEIGHT = 1.5`). A false positive
  costs a wet-lab experiment; a false negative costs a backlog row.
- `undecided` carries no weight in either direction, and a malformed or failed
  challenge becomes `undecided` — never agreement by default.

## State is append-only

`CandidateState` has one mutation primitive, `record`. Features can be updated,
but the update is itself an event and the prior value stays in the log:

```json
{"kind": "feature", "actor": "tool:repeat_scan",
 "payload": {"changes": {"repeat_copy_count": {"from": null, "to": 9.0}}}}
```

An investigation that overwrites what it previously believed cannot be audited
afterwards. This is what makes it possible to answer "why does it think that?"
months later.

## The report

Generated from the event log alone — nothing may appear in it that is not in the
log. Two sections are mandatory and are rendered even when empty, so their
absence is always a finding rather than an omission:

- **Counter-evidence.** When no challenge succeeded, it says so in the weaker
  form that is actually true: no mundane explanation was *found*, not that none
  exists. An unreviewed candidate is labelled unreviewed.
- **What remains unknown.** Open hypotheses, inconclusive challenges, tools that
  failed, and why the investigation stopped. When nothing is listed, it says to
  treat that with suspicion.

## What is real, and what is declared

```
python -c "from sde.tools import registry, available_tools; print(available_tools())"
```

| tool | status |
|---|---|
| `sequence_stats`, `repeat_scan`, `repeat_detail` | implemented (`discovery.features`) |
| `neighbourhood_novelty` | implemented, but expects *already annotated* genes |
| `structure_compare` | implemented (official US-align) |
| `structure_rank` | implemented (RiboRank) |
| `mmseqs_search`, `mmseqs_cluster`, `hmmsearch`, `infernal_scan`, `rnafold`, `literature_search`, `taxonomy_lookup` | **declared, not installed** |

The absent tools are registered so the gap is visible in the catalogue, and they
**raise** with the install command. A stub returning plausible numbers would be
indistinguishable from a working tool in the final report, which is the one
outcome worth preventing.

`hmmsearch` and `mmseqs_cluster` being absent is not a detail. They are the step
that makes a billion-sequence space tractable at all. Without them this engine
can investigate candidates it is handed; it cannot find them.

## RiboRank ships its own caveat

`structure_rank` returns `ranker_caveat` alongside the ranking:

> RiboRank scoring modes do not beat random selection on real prediction pools.
> Treat this ordering as a pool reduction with no demonstrated skill, not as
> evidence of structural quality.

Putting the caveat inside the tool output is the only way to be sure it travels
with the number into whatever reads it next.

## What the demo shows

`python -m sde.demo` runs a scripted investigator down the path the ART account
describes — neighbourhood, then something odd, then back to the raw DNA, then
the repeats. It recovers the planted array (9 copies, 140 bp period) for a
budget of 12.

Then it does the thing that matters: `infernal_scan` is not installed, so the
run **stops without claiming novelty**, and the report says why under "What
remains unknown". A system that concluded "novel!" there would be the failure
mode this whole design exists to avoid.

The data is generated by the demo file. It demonstrates the mechanism and the
record, not a discovery.
