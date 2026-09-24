"""Scientific Discovery Engine.

An independent engine that investigates candidates: a tool registry the agent
may request from, persistent auditable state, a dynamic investigation loop,
adversarial review, and a report.

RiboRank is one of its instruments, not its core. The dependency runs one way:
``sde`` imports ``riborank`` and ``discovery``; neither imports ``sde``.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
