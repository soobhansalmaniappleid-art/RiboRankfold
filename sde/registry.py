"""The tool registry: what an agent is allowed to ask for.

An agent in this engine cannot run code. It can only emit a `ToolRequest`
naming a registered tool, and the orchestrator decides whether to run it. That
boundary is the difference between a system a scientist can audit and a model
with shell access.

Three properties the registry enforces rather than documents:

* **Whitelist.** A request naming an unregistered tool is rejected and
  *recorded*, never executed. What an agent tried to do is part of the record.
* **Declared cost.** Every tool states what it costs, and the orchestrator
  holds a budget. This is what stops an investigation from turning into a
  thousand sessions that each re-read the same FASTA.
* **Declared inputs.** A tool names the fields it requires, and a request
  missing one fails before anything runs.
"""

from __future__ import annotations

import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class ToolCost(IntEnum):
    """What running a tool costs, in units the orchestrator budgets against."""

    TRIVIAL = 1  # string statistics on data already in hand
    CHEAP = 2  # an indexed lookup, a k-mer scan
    MODERATE = 5  # alignment, HMM search, folding
    EXPENSIVE = 20  # structure prediction, a large database sweep
    EXTERNAL = 50  # a network call to somebody else's service


class ToolError(RuntimeError):
    """A tool could not be run, or was not allowed to run."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """A capability the engine offers, and the agent may request by name."""

    name: str
    cost: ToolCost
    summary: str
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    run: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    deterministic: bool = True

    def describe(self) -> str:
        """One line for the agent's prompt. Agents choose from this, not from code."""
        needs = ", ".join(self.requires) or "nothing"
        gives = ", ".join(self.produces) or "unspecified"
        return (
            f"{self.name} (cost {self.cost.name}): {self.summary} "
            f"| needs: {needs} | gives: {gives}"
        )


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """An agent's request to run a tool.

    ``reason`` is required and stored. An investigation that cannot say why it
    ran something is not reproducible reasoning, it is just expenditure.
    """

    tool: str
    reason: str
    inputs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tool:
            raise ToolError("a tool request must name a tool")
        if not self.reason.strip():
            raise ToolError(f"request for {self.tool!r} has no reason")

    def key(self) -> tuple[str, tuple[tuple[str, str], ...]]:
        """Identity for deduplication: same tool, same inputs."""
        return (self.tool, tuple(sorted((k, repr(v)) for k, v in self.inputs.items())))


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What happened, whether or not it worked."""

    tool: str
    ok: bool
    cost: int
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    seconds: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "ok": self.ok,
            "cost": self.cost,
            "outputs": self.outputs,
            "error": self.error,
            "seconds": round(self.seconds, 4),
            "reason": self.reason,
        }


class ToolRegistry:
    """The set of tools an agent may name."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ToolError(f"tool {spec.name!r} is already registered")
        if spec.run is None:
            raise ToolError(f"tool {spec.name!r} has no implementation")
        self._tools[spec.name] = spec
        return spec

    def tool(
        self,
        name: str,
        cost: ToolCost,
        summary: str,
        requires: tuple[str, ...] = (),
        produces: tuple[str, ...] = (),
        deterministic: bool = True,
    ) -> Callable[[Callable[[dict[str, Any]], dict[str, Any]]], Callable]:
        """Decorator form of :meth:`register`."""

        def decorate(function: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable:
            self.register(
                ToolSpec(
                    name=name,
                    cost=cost,
                    summary=summary,
                    requires=requires,
                    produces=produces,
                    run=function,
                    deterministic=deterministic,
                )
            )
            return function

        return decorate

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise ToolError(
                f"unknown tool {name!r}. Available: {sorted(self._tools)}. "
                "Agents may only request registered tools."
            )
        return self._tools[name]

    def catalogue(self, max_cost: ToolCost | None = None) -> list[ToolSpec]:
        """Tools an agent may choose from, optionally capped by cost."""
        specs = sorted(self._tools.values(), key=lambda s: (s.cost, s.name))
        if max_cost is not None:
            specs = [spec for spec in specs if spec.cost <= max_cost]
        return specs

    def describe(self, max_cost: ToolCost | None = None) -> str:
        return "\n".join(spec.describe() for spec in self.catalogue(max_cost))

    def execute(self, request: ToolRequest) -> ToolResult:
        """Run a request, converting any failure into a recorded result.

        A tool that raises produces ``ok=False`` with the message, not an
        exception that aborts the investigation. One broken tool must not
        discard everything learned before it.
        """
        try:
            spec = self.get(request.tool)
        except ToolError as error:
            return ToolResult(
                tool=request.tool, ok=False, cost=0, error=str(error), reason=request.reason
            )

        missing = [field_name for field_name in spec.requires if field_name not in request.inputs]
        if missing:
            return ToolResult(
                tool=spec.name,
                ok=False,
                cost=0,
                error=f"missing required input(s): {missing}",
                reason=request.reason,
            )

        started = time.perf_counter()
        try:
            outputs = spec.run(dict(request.inputs))  # type: ignore[misc]
        except Exception as error:  # noqa: BLE001 - deliberately broad, see docstring
            return ToolResult(
                tool=spec.name,
                ok=False,
                cost=int(spec.cost),
                error=f"{type(error).__name__}: {error}",
                seconds=time.perf_counter() - started,
                reason=request.reason,
            )
        if not isinstance(outputs, dict):
            return ToolResult(
                tool=spec.name,
                ok=False,
                cost=int(spec.cost),
                error=f"tool returned {type(outputs).__name__}, expected dict",
                seconds=time.perf_counter() - started,
                reason=request.reason,
            )
        return ToolResult(
            tool=spec.name,
            ok=True,
            cost=int(spec.cost),
            outputs=outputs,
            seconds=time.perf_counter() - started,
            reason=request.reason,
        )


def format_traceback(error: BaseException) -> str:
    """Full traceback, for a failure worth diagnosing rather than just recording."""
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))
