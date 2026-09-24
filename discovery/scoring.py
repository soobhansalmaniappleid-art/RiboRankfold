"""Novelty scoring.

Two design decisions are load-bearing here.

**Novelty alone is not a score.** A sequence no database recognises is usually
contamination, a frameshift or an assembly artifact, not a discovery. What
distinguishes an interesting locus is that it is *simultaneously* unusual,
internally coherent, and seen independently more than once. These are combined
multiplicatively, so a candidate that fails any one of them cannot be rescued by
excelling at the others.

**A score is not a verdict.** This module ranks what deserves attention. It does
not decide what is real; that is the job of the agent layer, which can argue
back, and of an experiment, which can settle it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from discovery.schema import Candidate

# Deliberately few and blunt. Fitting many weights to a handful of known systems
# is how you build something that only rediscovers what it was shown.
DEFAULT_WEIGHTS: dict[str, float] = {
    "architecture_novelty": 0.35,
    "unexplained_partner_fraction": 0.25,
    "repeat_anomaly": 0.25,
    "sequence_novelty": 0.15,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value != value:
        return math.nan
    return max(low, min(high, value))


def repeat_anomaly(features: dict[str, float]) -> float:
    """How array-like the repeat structure is, in [0, 1].

    Rewards many copies at a regular period with high identity between them.
    A handful of loosely spaced near-matches scores close to zero, because that
    is what random sequence produces.
    """
    copies = features.get("repeat_copy_count", 0.0) or 0.0
    if copies < 3:
        return 0.0
    identity = features.get("repeat_unit_identity", math.nan)
    period_cv = features.get("repeat_period_cv", math.nan)
    if identity != identity or period_cv != period_cv:
        return 0.0
    # Saturating in copy number: 3 copies is interesting, 30 is not ten times so.
    copy_term = _clamp(math.log(copies - 1) / math.log(11))
    regularity = _clamp(1.0 - period_cv / 0.25)
    return _clamp(copy_term * regularity * _clamp(identity))


def sequence_novelty(features: dict[str, float]) -> float:
    """Penalise low-complexity sequence, which mimics novelty without being it."""
    low_complexity = features.get("low_complexity_fraction", math.nan)
    ambiguous = features.get("ambiguous_fraction", 0.0) or 0.0
    if low_complexity != low_complexity:
        return math.nan
    return _clamp(1.0 - low_complexity) * _clamp(1.0 - ambiguous)


def coherence(features: dict[str, float]) -> float:
    """Is this a well-formed locus, or a pile of artifacts?

    Contamination and mis-assembly present as ambiguous bases and
    low-complexity runs. A candidate that looks broken is down-weighted no
    matter how novel it appears.
    """
    ambiguous = features.get("ambiguous_fraction", 0.0) or 0.0
    low_complexity = features.get("low_complexity_fraction", 0.0) or 0.0
    return _clamp(1.0 - ambiguous) * _clamp(1.0 - low_complexity)


def reproducibility(features: dict[str, float], saturate_at: int = 5) -> float:
    """Independent observations, saturating.

    One sighting is not evidence. The curve is steep at the start -- going from
    one genome to three matters far more than going from ten to twelve.
    """
    support = features.get("cross_genome_support", 1.0) or 1.0
    if support <= 1:
        return 0.0
    return _clamp(math.log(support) / math.log(saturate_at))


@dataclass(slots=True)
class NoveltyScorer:
    weights: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.weights is None:
            self.weights = dict(DEFAULT_WEIGHTS)
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"weights must sum to 1.0, got {total}")

    def novelty(self, features: dict[str, float]) -> float:
        derived = dict(features)
        derived["repeat_anomaly"] = repeat_anomaly(features)
        derived["sequence_novelty"] = sequence_novelty(features)

        total = 0.0
        used = 0.0
        for key, weight in self.weights.items():
            value = derived.get(key, math.nan)
            if value != value:
                continue  # renormalise over available components
            total += weight * _clamp(value)
            used += weight
        if used == 0.0:
            return math.nan
        return total / used

    def score(self, candidate: Candidate) -> dict[str, float]:
        """Attach novelty, coherence, reproducibility and their product."""
        features = candidate.features
        novelty = self.novelty(features)
        coh = coherence(features)
        rep = reproducibility(features)
        priority = (
            math.nan if novelty != novelty else novelty * coh * max(rep, 0.05)
        )
        scores = {
            "novelty": novelty,
            "coherence": coh,
            "reproducibility": rep,
            "repeat_anomaly": repeat_anomaly(features),
            "priority": priority,
        }
        candidate.scores.update(scores)
        candidate.add_evidence(
            "priority",
            priority,
            source="discovery.scoring.NoveltyScorer",
            note="novelty * coherence * max(reproducibility, 0.05)",
        )
        return scores


def known_track(features: dict[str, float], threshold: float = 0.25) -> bool:
    """True when a candidate resembles a described system.

    Kept as a separate track rather than discarded. A variant of a known system
    can be the interesting thing; treating "looks familiar" as "already
    explained" is how a pipeline filters out its own best result.
    """
    novelty = features.get("architecture_novelty", math.nan)
    if novelty != novelty:
        return False
    return novelty < threshold
