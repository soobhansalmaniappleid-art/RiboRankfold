# The discovery engine

## What this is

A staged funnel for finding genomic loci worth a human's attention, with the
language model placed near the **end** of the pipeline rather than the start.

```
                    RAW LOCI  (millions)
                        |
   Cost.TRIVIAL    QC / complexity        <- string statistics
                        |
   Cost.CHEAP      known-system filter    <- indexed lookup
                        |
   Cost.CHEAP      independent support    <- seen in >1 taxon?
                        |
   Cost.MODERATE   feature + novelty score
                        |
   Cost.MODERATE   escalation threshold
                        |
   Cost.EXPENSIVE  agent investigation    <- the model finally runs
                        |
   Cost.EXPENSIVE  adversarial review     <- agents attack the claim
                        |
                    REPORTS  (tens)
```

`Pipeline` refuses to construct a funnel whose stages are not ordered
cheapest-first. That ordering is not a convention to remember, it is enforced:

```python
>>> Pipeline([expensive_agent_stage, cheap_qc_stage])
ValueError: stage 'qc' (cost TRIVIAL) cannot run after 'agents' (cost EXPENSIVE);
order stages cheapest-first so expensive analysis only sees survivors
```

Run the whole thing on synthetic data:

```bash
python -m discovery.demo
```

## Why the model goes last

A model asked to read a million loci and "find something interesting" will
produce a million paragraphs and one useful sentence, at enormous cost. The
deterministic layers exist to make the model's context small enough that its
actual strength — explaining why a *specific* combination of observations is
strange, and what would rule it out — is what gets used.

Concretely, in the demo funnel, 17 loci become 7 before any prompt is built.
On real data the ratio is the entire point.

## Why a score is not a verdict

`discovery/scoring.py` combines three quantities **multiplicatively**:

```
priority = novelty * coherence * max(reproducibility, 0.05)
```

- **novelty** — how poorly the architecture is explained by known systems
- **coherence** — does the locus look well-formed, or like an assembly artifact
- **reproducibility** — how many independent taxa show the same arrangement

The product matters. An additive score lets a spectacular novelty value carry a
candidate that was seen exactly once in one contaminated contig, which is the
single most common way a discovery pipeline embarrasses itself. Under a product,
failing any one term kills the candidate regardless of the others.

`reproducibility` saturates logarithmically: going from 1 genome to 3 is strong
evidence, 10 to 12 is almost none.

## Why "looks known" is a track, not a bin

`known_track()` separates candidates resembling described systems rather than
deleting them. A divergent member of a known family can be the interesting
result; a filter that equates "familiar" with "explained" discards its own best
findings. The two tracks are scored the same way and reviewed separately.

## Why the agents argue

`AdversarialReview` runs four roles with deliberately different priors:

| agent | asked to |
|---|---|
| `investigator` | propose explanations, *including mundane ones*, and say what would distinguish them |
| `skeptic` | build the strongest case that this is ordinary |
| `literature` | determine whether it is already described |
| `artifact` | argue it is mis-assembly, contamination or chance |

Three of the four are pointed at destroying the claim. A panel that all answers
"is this exciting?" will agree with itself, and that agreement carries no
information.

Two rules make the aggregation honest:

- **Refutation outweighs support** (`REFUTATION_WEIGHT = 1.5`). A false positive
  costs a wet-lab experiment; a false negative costs a backlog row.
- **`inconclusive` counts for nothing.** An agent that cannot tell must not be
  able to advance a candidate. Critically, a response that fails to parse becomes
  `inconclusive` with confidence 0.0 — never a guessed stance. A fabricated
  opinion in the audit trail is worse than a recorded failure to answer.

## Auditability

Every candidate serialises to one JSON file containing the complete chain:

```json
{
  "schema_version": 1,
  "candidate_id": "array_0",
  "features": { "repeat_copy_count": 9.0, "repeat_mean_period": 140.0, ... },
  "scores":   { "novelty": 0.87, "coherence": 1.0, "priority": 0.757, ... },
  "evidence": [
    { "key": "architecture", "value": "RT|orfX|orfY",
      "source": "discovery.features.neighborhood", "kind": "computed" },
    { "key": "skeptic_stance", "value": "refutes",
      "source": "agent:skeptic", "kind": "model" }
  ],
  "history":  [ { "stage": "qc_complexity", "decision": "keep",
                  "reason": "low_complexity_fraction=0 within range" } ],
  "verdicts": [ { "agent": "skeptic", "stance": "refutes",
                  "confidence": 0.6, "rationale": "..." } ],
  "dropped_by": null
}
```

Two properties this buys:

1. **`Evidence.kind` separates measurement from opinion.** A number a tool
   computed and a claim a model made never blur together.
2. **Nothing disappears silently.** Dropped candidates are retained with the
   stage and reason that dropped them, so "why did we never look at X?" is
   always answerable. `threshold_rule` treats a *missing* feature as a drop with
   a stated reason, never a silent pass — a stage that could not evaluate a
   candidate has not cleared it.

## What is real and what is not

| component | status |
|---|---|
| `discovery/schema.py` | complete, tested |
| `discovery/stages.py` | complete, tested |
| `discovery/scoring.py` | complete, tested |
| `discovery/features/sequence.py` | complete, tested |
| `discovery/features/repeats.py` | complete, tested — finds planted arrays, zero hits on random DNA |
| `discovery/features/neighborhood.py` | complete, tested — but expects *already annotated* genes |
| `discovery/agents/*` | protocol + roles + review complete, tested against an offline stub |
| real LLM client | **not written** — implement `LLMClient.complete` |
| ingestion from NCBI/UniProt | **not written** |
| MMseqs2 / HMMER adapters | **not written** |
| structure-based features | **not written** |

The honest summary: the *architecture* and the *deterministic detectors* are
real and tested. The engine has never been pointed at real metagenomic data, and
nothing here has discovered anything.

## Wiring a real model

```python
from discovery.agents.base import LLMClient

class AnthropicClient:
    def __init__(self, client, model="claude-opus-4-5"):
        self._client, self._model = client, model

    def complete(self, system: str, prompt: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
```

Pass it to `AdversarialReview(client=AnthropicClient(...))`. Nothing else
changes; the pipeline depends on the protocol, not the vendor.

## Prior art worth reading before extending this

- **MMseqs2** — sequence search and clustering at the scale this design assumes
- **antiSMASH** — a mature multi-stage biological detection pipeline
- **CRISPRidentify** — candidate → feature → classifier → confidence, the same
  shape as `stages.py` + `scoring.py`
- **BiG-SCAPE** — clustering gene systems by domain composition

The deterministic layers here are deliberately simple stand-ins. Replacing them
with these tools is the intended path, and is why the feature functions take
plain sequences and annotated neighbourhoods rather than owning their own I/O.
