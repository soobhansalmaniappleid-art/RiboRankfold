"""The agent roles.

The investigator is asked what would make the candidate interesting. Every other
role is asked to take it apart. That asymmetry is deliberate: a panel of agents
that all answer "is this exciting?" will agree with each other, and their
agreement carries no information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from discovery.agents.base import RESPONSE_CONTRACT, Agent, describe_candidate
from discovery.schema import Candidate

_SHARED = (
    "You are part of an automated genomic discovery pipeline. You are given only "
    "features computed by deterministic tools; you cannot run new analyses. "
    "Never assert a fact the features do not support, and never treat the "
    "absence of a database match as positive evidence of novelty."
)


@dataclass(slots=True)
class Investigator(Agent):
    """Proposes what the candidate might be, and what would confirm it."""

    name: ClassVar[str] = "investigator"
    system: ClassVar[str] = (
        f"{_SHARED} Your job is to state the most plausible explanations for this "
        "locus, ranked, and to say which observation would distinguish between "
        "them. Take 'supports' to mean the locus merits further investigation."
    )

    def build_prompt(self, candidate: Candidate) -> str:
        return (
            f"{describe_candidate(candidate)}\n\n"
            "List the plausible explanations for this locus, including mundane "
            "ones (assembly artifact, known mobile element, annotation error). "
            "Then judge whether it merits further investigation.\n\n"
            f"{RESPONSE_CONTRACT}"
        )


@dataclass(slots=True)
class Skeptic(Agent):
    """Argues the candidate is ordinary. Adopts the opposite prior on purpose."""

    name: ClassVar[str] = "skeptic"
    system: ClassVar[str] = (
        f"{_SHARED} Your job is to find the most likely boring explanation and "
        "argue for it as strongly as the evidence allows. Assume by default that "
        "the locus is an artifact, a known system, or a coincidence, and say what "
        "would be needed to change your mind. Take 'refutes' to mean the novelty "
        "claim does not hold up."
    )

    def build_prompt(self, candidate: Candidate) -> str:
        return (
            f"{describe_candidate(candidate)}\n\n"
            "Give the strongest case that this locus is NOT novel. Consider "
            "assembly artifacts, low-complexity sequence, a described system the "
            "features would not distinguish, and chance. Then state whether the "
            "novelty claim survives.\n\n"
            f"{RESPONSE_CONTRACT}"
        )


@dataclass(slots=True)
class LiteratureAgent(Agent):
    """Checks whether the arrangement is already described."""

    name: ClassVar[str] = "literature"
    system: ClassVar[str] = (
        f"{_SHARED} Your job is to say whether this architecture matches something "
        "already in the literature. Cite what you rely on. If you cannot identify "
        "a match and cannot rule one out, answer 'inconclusive' rather than "
        "treating silence as novelty. Take 'refutes' to mean it is already "
        "described."
    )

    def build_prompt(self, candidate: Candidate) -> str:
        return (
            f"{describe_candidate(candidate)}\n\n"
            "Is this architecture already described? Name any system it resembles "
            "and cite it. If nothing matches, say whether that is informative or "
            "simply unknown.\n\n"
            f"{RESPONSE_CONTRACT}"
        )


@dataclass(slots=True)
class ArtifactAgent(Agent):
    """Screens for the technical failure modes that mimic discovery."""

    name: ClassVar[str] = "artifact"
    system: ClassVar[str] = (
        f"{_SHARED} Your job is to assess whether the signal could be a technical "
        "artifact: mis-assembly, collapsed repeats, chimeric contigs, "
        "contamination, or a gene-calling error. Take 'refutes' to mean the "
        "signal is probably an artifact."
    )

    def build_prompt(self, candidate: Candidate) -> str:
        return (
            f"{describe_candidate(candidate)}\n\n"
            "Could this signal be a technical artifact rather than biology? "
            "Weigh repeat regularity, ambiguous bases and low-complexity content, "
            "and note that a perfectly regular repeat period can indicate "
            "collapsed assembly rather than a real array.\n\n"
            f"{RESPONSE_CONTRACT}"
        )
