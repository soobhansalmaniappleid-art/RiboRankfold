from __future__ import annotations

import pytest

from sde.registry import (
    ToolCost,
    ToolError,
    ToolRegistry,
    ToolRequest,
    ToolSpec,
)


def registry_with(**kwargs) -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool("echo", ToolCost.TRIVIAL, "returns its input", requires=("value",))
    def _echo(inputs):
        return {"echoed": inputs["value"]}

    @registry.tool("boom", ToolCost.CHEAP, "always fails")
    def _boom(inputs):
        raise RuntimeError("detonated")

    @registry.tool("bad_return", ToolCost.CHEAP, "returns a non-dict")
    def _bad(inputs):
        return [1, 2, 3]

    return registry


# -- requests -----------------------------------------------------------


def test_a_request_must_name_a_tool():
    with pytest.raises(ToolError, match="must name a tool"):
        ToolRequest(tool="", reason="because")


def test_a_request_must_carry_a_reason():
    """An investigation that cannot say why it ran something is not reasoning."""
    with pytest.raises(ToolError, match="no reason"):
        ToolRequest(tool="echo", reason="   ")


def test_request_key_ignores_input_order():
    a = ToolRequest("t", "r", {"x": 1, "y": 2})
    b = ToolRequest("t", "r", {"y": 2, "x": 1})
    assert a.key() == b.key()


def test_request_key_distinguishes_inputs():
    assert ToolRequest("t", "r", {"x": 1}).key() != ToolRequest("t", "r", {"x": 2}).key()


# -- registration -------------------------------------------------------


def test_duplicate_registration_is_rejected():
    registry = registry_with()
    with pytest.raises(ToolError, match="already registered"):
        registry.register(ToolSpec("echo", ToolCost.TRIVIAL, "dup", run=lambda i: {}))


def test_a_tool_without_an_implementation_is_rejected():
    with pytest.raises(ToolError, match="no implementation"):
        ToolRegistry().register(ToolSpec("x", ToolCost.TRIVIAL, "nothing"))


def test_catalogue_is_ordered_by_cost():
    registry = registry_with()
    costs = [spec.cost for spec in registry.catalogue()]
    assert costs == sorted(costs)


def test_catalogue_can_be_capped_by_cost():
    registry = registry_with()
    names = [spec.name for spec in registry.catalogue(max_cost=ToolCost.TRIVIAL)]
    assert names == ["echo"]


def test_describe_lists_requirements():
    assert "needs: value" in registry_with().describe()


# -- execution: the whitelist -------------------------------------------


def test_an_unregistered_tool_is_refused_not_executed():
    """The property that separates this from a model with shell access."""
    result = registry_with().execute(ToolRequest("rm_rf", "cleanup", {}))
    assert result.ok is False
    assert "unknown tool" in result.error
    assert result.cost == 0


def test_the_refusal_names_what_is_available():
    result = registry_with().execute(ToolRequest("nope", "why not", {}))
    assert "echo" in result.error


def test_a_missing_required_input_fails_before_running():
    calls = []
    registry = ToolRegistry()

    @registry.tool("needs_x", ToolCost.TRIVIAL, "needs x", requires=("x",))
    def _needs_x(inputs):
        calls.append(inputs)
        return {}

    result = registry.execute(ToolRequest("needs_x", "try", {}))
    assert result.ok is False
    assert "missing required input" in result.error
    assert calls == []  # never ran


def test_a_successful_call_reports_cost_and_outputs():
    result = registry_with().execute(ToolRequest("echo", "test", {"value": 7}))
    assert result.ok is True
    assert result.outputs == {"echoed": 7}
    assert result.cost == int(ToolCost.TRIVIAL)
    assert result.seconds >= 0.0


def test_the_reason_travels_into_the_result():
    result = registry_with().execute(ToolRequest("echo", "my reason", {"value": 1}))
    assert result.reason == "my reason"


def test_a_raising_tool_becomes_a_failed_result_not_an_exception():
    """One broken tool must not discard everything learned before it."""
    result = registry_with().execute(ToolRequest("boom", "test", {}))
    assert result.ok is False
    assert "RuntimeError: detonated" in result.error
    assert result.cost == int(ToolCost.CHEAP)  # it still cost something


def test_a_tool_returning_a_non_dict_is_a_failure():
    result = registry_with().execute(ToolRequest("bad_return", "test", {}))
    assert result.ok is False
    assert "expected dict" in result.error


def test_inputs_are_copied_so_a_tool_cannot_mutate_the_request():
    registry = ToolRegistry()

    @registry.tool("mutate", ToolCost.TRIVIAL, "mutates its input", requires=("d",))
    def _mutate(inputs):
        inputs["d"] = "clobbered"
        return {"ok": True}

    request = ToolRequest("mutate", "test", {"d": "original"})
    registry.execute(request)
    assert request.inputs["d"] == "original"
