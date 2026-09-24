"""Benchmarks for the discovery engine. See :mod:`sde.benchmarks.blind_rt`."""

from __future__ import annotations

from sde.benchmarks.blind_rt import RESEARCH_QUESTION, Corpus
from sde.benchmarks.survey import deterministic_sweep, score_survey

__all__ = ["Corpus", "RESEARCH_QUESTION", "deterministic_sweep", "score_survey"]
