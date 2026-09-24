"""Tool adapters. See :mod:`sde.tools.builtin` for the shipped registry."""

from __future__ import annotations

from sde.tools.bio import register_real_tools
from sde.tools.builtin import available_tools, registry

#: Backends present on this machine replace their declared-but-absent stubs at
#: import time, so the catalogue always describes what can actually be run.
REAL_TOOLS = register_real_tools(registry)

__all__ = ["registry", "available_tools", "REAL_TOOLS"]
