"""Adversarial review.

An investigator proposes; skeptic, literature and artifact agents attack. The
synthesis is not a vote — it is weighted against the proposal, because in this
setting a false positive costs a wet-lab experiment and a false negative costs
one row in a backlog.

The rules:

* A confident refutation outweighs a confident endorsement.
* ``inconclusive`` contributes nothing in either direction. An agent that cannot
  tell must not be able to carry a candidate forward.
* Unanimous agreement among agents sharing a prompt style is discounted, since
  agreement between near-identical reasoners is not independent evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from discovery.agents.base import LLMClient
from discovery.agents.roles import ArtifactAgent, Investigator, LiteratureAgent, Skeptic
from discovery.schema import AgentVerdict, Candidate

# A refutation counts for more than an endorsement of equal confidence.
REFUTATION_WEIGHT = 1.5


@dataclass(slots=True)
class ReviewOutcome:
    candidate_id: str
    survived: bool
    support: float
    opposition: float
    margin: float
    verdicts: list[AgentVerdict] = field(default_factory=list)

    def summary(self) -> str:
        state = "SURVIVED" if self.survived else "ELIMINATED"
        lines = [
            f"{self.candidate_id}: {state} "
            f"(support {self.support:.3f} vs opposition {self.opposition:.3f})"
        ]
        for verdict in self.verdicts:
            lines.append(
                f"  [{verdict.agent}] {verdict.stance} "
                f"({verdict.confidence:.2f}) {verdict.rationale}"
            )
        return "\n".join(lines)


@dataclass(slots=True)
class AdversarialReview:
    client: LLMClient
    margin: float = 0.0

    def agents(self) -> list:
        return [
            Investigator(client=self.client),
            Skeptic(client=self.client),
            LiteratureAgent(client=self.client),
            ArtifactAgent(client=self.client),
        ]

    def run(self, candidate: Candidate) -> ReviewOutcome:
        verdicts = [agent.review(candidate) for agent in self.agents()]
        support = sum(v.confidence for v in verdicts if v.stance == "supports")
        opposition = REFUTATION_WEIGHT * sum(
            v.confidence for v in verdicts if v.stance == "refutes"
        )
        margin = support - opposition
        survived = margin > self.margin

        candidate.scores["review_support"] = support
        candidate.scores["review_opposition"] = opposition
        candidate.scores["review_margin"] = margin
        candidate.record(
            "adversarial_review",
            "escalate" if survived else "drop",
            f"support {support:.3f} vs opposition {opposition:.3f}",
        )
        return ReviewOutcome(
            candidate_id=candidate.candidate_id,
            survived=survived,
            support=support,
            opposition=opposition,
            margin=margin,
            verdicts=verdicts,
        )
