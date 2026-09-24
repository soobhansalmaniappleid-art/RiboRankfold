"""RiboRank: evaluation harness for ranking RNA 3D structure candidates.

The package deliberately separates three layers:

* ``structure``/``geometry`` -- deterministic, label-free computation
* ``pipeline``               -- manifest, features, native-derived labels
* ``ranking``                -- regret and pairwise metrics against an oracle

Nothing here claims state-of-the-art performance. The current honest status of
the baselines is recorded in ``reports/evaluation/`` and summarised in the
README; see docs/METRICS.md for why ``tm_like`` is not a published TM-score.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
