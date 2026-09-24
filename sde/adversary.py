"""The adversarial scientist.

After an investigation concludes something is interesting, a separate agent is
given the same evidence and asked to destroy the claim. It runs *after* the
investigation and does not share its state object's optimism — it sees the
evidence, not the enthusiasm.

The asymmetry is deliberate and is the point. A second agent asked "do you
agree?" will agree, and that agreement carries no information. This one is
scored on whether it can find a mundane explanation, and a claim only survives
if it cannot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from sde.state import CandidateState

Stance = Literal["survives", "refuted", "undecided"]

#: A refutation outweighs an endorsement of equal confidence. A false positive
#: costs a wet-lab experiment; a false negative costs a row in a backlog.
REFUTATION_WEIGHT = 1.5

CHALLENGES: dict[str, str] = {
    "already_described": (
        "Argue that this is an already-described system. Name what it resembles. "
        "If you cannot name one, say the search was inconclusive rather than "
        "treating silence as novelty."
    ),
    "assembly_artifact": (
        "Argue that the signal is a technical artifact: mis-assembly, collapsed "
        "repeats, a chimeric contig, contamination, or a gene-calling error. Note "
        "that a perfectly regular repeat period can indicate collapsed assembly "
        "rather than a real array."
    ),
    "chance": (
        "Argue that the pattern is what random sequence of this composition and "
        "length would produce anyway. Consider how many candidates were screened "
        "before this one was singled out."
    ),
    "distant_homology": (
        "Argue that a distant homologue explains this, and that the novelty claim "
        "rests on a search not sensitive enough to find it."
    ),
}

PROMPT = """\
A candidate has been proposed as novel. Your job is to destroy that claim.

Evidence:
{evidence}

Hypotheses under consideration:
{hypotheses}

Your specific challenge:
{challenge}

Reply with a single JSON object and nothing else:

{{
  "stance": "refuted" | "survives" | "undecided",
  "confidence": 0.0,
  "argument": "<two or three sentences>",
  "what_would_settle_it": "<the observation that would decide>"
}}

"refuted" means your challenge succeeds and the novelty claim does not hold.
"survives" means you tried and could not make the challenge stick.
"undecided" means the evidence does not let you tell. Use it honestly: an
unsupported refutation is as damaging as an unsupported endorsement.
"""


@dataclass(slots=True)
class Challenge:
    name: str
    stance: Stance
    confidence: float
    argument: str
    what_would_settle_it: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge": self.name,
            "stance": self.stance,
            "confidence": self.confidence,
            "argument": self.argument,
            "what_would_settle_it": self.what_would_settle_it,
        }


@dataclass(slots=True)
class ReviewOutcome:
    candidate_id: str
    survived: bool
    support: float
    opposition: float
    challenges: list[Challenge] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    @property
    def margin(self) -> float:
        return self.support - self.opposition


@dataclass(slots=True)
class AdversarialReview:
    client: Any  # needs .complete(system, prompt) -> str
    challenges: tuple[str, ...] = tuple(CHALLENGES)
    system: str = (
        "You are a skeptical reviewer in an automated discovery engine. You are "
        "given only evidence computed by deterministic tools. Argue against the "
        "novelty claim as strongly as the evidence allows, and concede when it "
        "does not allow it."
    )

    def run(self, state: CandidateState) -> ReviewOutcome:
        results: list[Challenge] = []
        for name in self.challenges:
            raw = self._ask(state, name)
            results.append(_parse_challenge(raw, name))

        support = sum(c.confidence for c in results if c.stance == "survives")
        opposition = REFUTATION_WEIGHT * sum(
            c.confidence for c in results if c.stance == "refuted"
        )
        survived = support > opposition
        unresolved = [c.name for c in results if c.stance == "undecided"]

        for challenge in results:
            state.record(
                "verdict",
                f"adversary:{challenge.name}",
                f"{challenge.stance}: {challenge.argument[:160]}",
                **challenge.to_dict(),
            )
        state.decide(
            "investigating" if survived else "eliminated",
            "adversarial_review",
            f"support {support:.3f} vs opposition {opposition:.3f}",
        )
        return ReviewOutcome(
            candidate_id=state.candidate_id,
            survived=survived,
            support=support,
            opposition=opposition,
            challenges=results,
            unresolved=unresolved,
        )

    def _ask(self, state: CandidateState, challenge: str) -> str:
        evidence = "\n".join(
            f"  {key} = {state.features[key]}" for key in sorted(state.features)
        ) or "  (no computed features)"
        hypotheses = "\n".join(
            f"  - {h.statement}" for h in state.hypotheses
        ) or "  (none)"
        prompt = PROMPT.format(
            evidence=evidence,
            hypotheses=hypotheses,
            challenge=CHALLENGES.get(challenge, challenge),
        )
        try:
            return self.client.complete(self.system, prompt)
        except Exception as error:  # noqa: BLE001 - a failed challenge is undecided
            return json.dumps(
                {
                    "stance": "undecided",
                    "confidence": 0.0,
                    "argument": f"challenge could not be run: {error}",
                }
            )


def _parse_challenge(raw: str, name: str) -> Challenge:
    """Parse a reply; anything malformed is 'undecided', never a guessed stance."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        text = text.removeprefix("json").strip()
    payload: Any
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        try:
            payload = json.loads(text[start : end + 1]) if start != -1 and end > start else None
        except json.JSONDecodeError:
            payload = None
    if not isinstance(payload, dict):
        return Challenge(name, "undecided", 0.0, f"unparseable reply: {raw.strip()[:160]}")

    stance = str(payload.get("stance", "")).strip().lower()
    if stance not in ("survives", "refuted", "undecided"):
        return Challenge(name, "undecided", 0.0, f"invalid stance {stance!r}")
    try:
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.0))))
    except (TypeError, ValueError):
        confidence = 0.0
    return Challenge(
        name=name,
        stance=stance,  # type: ignore[arg-type]
        confidence=confidence,
        argument=str(payload.get("argument", "")).strip(),
        what_would_settle_it=str(payload.get("what_would_settle_it", "")).strip(),
    )
