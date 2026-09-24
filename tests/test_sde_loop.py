from __future__ import annotations

import json

import pytest

from sde.adversary import AdversarialReview
from sde.loop import InvestigationLoop, LLMInvestigator, ScriptedInvestigator, _parse_step
from sde.registry import ToolCost, ToolRegistry, ToolRequest
from sde.report import DiscoveryReport
from sde.state import CandidateState, Hypothesis


def demo_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool("cheap", ToolCost.TRIVIAL, "cheap tool", requires=("sequence",))
    def _cheap(inputs):
        return {"length": len(inputs["sequence"])}

    @registry.tool("pricey", ToolCost.EXPENSIVE, "expensive tool")
    def _pricey(inputs):
        return {"deep_result": 1}

    @registry.tool("barren", ToolCost.TRIVIAL, "returns nothing")
    def _barren(inputs):
        return {}

    return registry


def state() -> CandidateState:
    return CandidateState(candidate_id="c1", sequence="ACGT" * 25)


def step(tool=None, stop=False, reason="because", hypotheses=None, inputs=None):
    out = {"stop": stop, "hypotheses": hypotheses or []}
    if tool:
        out["request"] = {"tool": tool, "reason": reason, "inputs": inputs or {}}
    return out


# -- state --------------------------------------------------------------


def test_creation_is_itself_an_event():
    assert state().events[0].kind == "created"


def test_features_record_their_previous_value():
    s = state()
    s.set_features({"gc": 0.5}, actor="tool:x")
    s.set_features({"gc": 0.7}, actor="tool:y")
    changes = [e for e in s.events if e.kind == "feature"]
    assert changes[-1].payload["changes"]["gc"] == {"from": 0.5, "to": 0.7}


def test_an_unchanged_feature_records_nothing():
    s = state()
    s.set_features({"gc": 0.5}, actor="a")
    before = len(s.events)
    s.set_features({"gc": 0.5}, actor="a")
    assert len(s.events) == before


def test_a_hypothesis_without_a_test_is_rejected():
    """A claim nobody can imagine testing is not carried forward."""
    with pytest.raises(ValueError, match="discriminating evidence"):
        Hypothesis(statement="it is novel", proposed_by="x", discriminating_evidence="")


def test_state_round_trips_with_its_whole_log(tmp_path):
    s = state()
    s.set_features({"gc": 0.5}, actor="tool:x")
    s.add_hypothesis(Hypothesis("novel array", "agent", "check Rfam"))
    s.decide("investigating", "agent", "looks worth it")
    restored = CandidateState.load(s.save(tmp_path / "c.json"))
    assert restored.status == "investigating"
    assert len(restored.events) == len(s.events)
    assert restored.hypotheses[0].discriminating_evidence == "check Rfam"


def test_loading_an_unknown_version_is_refused(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"state_version": 99, "candidate_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="state version"):
        CandidateState.load(path)


def test_has_run_distinguishes_inputs():
    s = state()
    s.note_request(ToolRequest("cheap", "r", {"sequence": "AAA"}), "agent")
    assert s.has_run("cheap", {"sequence": "AAA"})
    assert not s.has_run("cheap", {"sequence": "CCC"})


# -- loop control -------------------------------------------------------


def test_the_loop_stops_when_the_agent_says_so():
    loop = InvestigationLoop(demo_registry(), ScriptedInvestigator([step(stop=True)]))
    result = loop.run(state())
    assert result.stop.code == "agent_stopped"
    assert result.requests_made == 0


def test_a_tool_result_becomes_a_feature():
    loop = InvestigationLoop(
        demo_registry(),
        ScriptedInvestigator([step("cheap", inputs={"sequence": "ACGTACGT"}), step(stop=True)]),
    )
    result = loop.run(state())
    assert result.state.features["length"] == 8
    assert result.requests_made == 1


def test_budget_caps_expensive_work():
    # Distinct inputs, so the budget is the binding constraint rather than the
    # repeat guard (which fires first for identical calls).
    loop = InvestigationLoop(
        demo_registry(),
        ScriptedInvestigator([step("pricey", inputs={"n": i}) for i in range(10)]),
        budget=25,
    )
    result = loop.run(state())
    assert result.stop.code == "budget_exhausted"
    assert result.state.spent <= 25


def test_a_tool_it_cannot_afford_is_refused_before_running():
    loop = InvestigationLoop(
        demo_registry(), ScriptedInvestigator([step("pricey")]), budget=5
    )
    result = loop.run(state())
    assert result.stop.code == "budget_exhausted"
    assert result.state.spent == 0


def test_repeating_a_call_is_refused():
    """Asking again is not a strategy."""
    same = step("cheap", inputs={"sequence": "ACGT"})
    loop = InvestigationLoop(
        demo_registry(), ScriptedInvestigator([same, same, same, same])
    )
    result = loop.run(state())
    assert result.requests_made == 1
    assert result.requests_refused >= 1
    assert result.stop.code == "no_progress"


def test_the_refusal_is_recorded():
    same = step("cheap", inputs={"sequence": "ACGT"})
    loop = InvestigationLoop(demo_registry(), ScriptedInvestigator([same, same, same, same]))
    result = loop.run(state())
    notes = [e.summary for e in result.state.events if e.kind == "note"]
    assert any("refused repeat" in note for note in notes)


def test_barren_rounds_end_the_loop():
    loop = InvestigationLoop(
        demo_registry(),
        ScriptedInvestigator([step("barren", inputs={"n": i}) for i in range(8)]),
        max_barren_rounds=3,
    )
    result = loop.run(state())
    assert result.stop.code == "no_progress"


def test_iterations_are_bounded():
    steps = [step("cheap", inputs={"sequence": "A" * i}) for i in range(50)]
    loop = InvestigationLoop(demo_registry(), ScriptedInvestigator(steps), max_iterations=4)
    result = loop.run(state())
    assert result.iterations <= 4


def test_an_unknown_tool_is_recorded_and_the_loop_survives():
    loop = InvestigationLoop(
        demo_registry(),
        ScriptedInvestigator([step("rm_rf"), step("cheap", inputs={"sequence": "AC"})]),
    )
    result = loop.run(state())
    failures = [
        e for e in result.state.events
        if e.kind == "tool_result" and not e.payload.get("ok")
    ]
    assert failures and "unknown tool" in failures[0].payload["error"]
    assert result.state.features.get("length") == 2  # loop carried on


def test_an_untestable_hypothesis_is_rejected_and_logged():
    bad = step(stop=True, hypotheses=[{"statement": "novel!", "discriminating_evidence": ""}])
    result = InvestigationLoop(demo_registry(), ScriptedInvestigator([bad])).run(state())
    assert result.state.hypotheses == []
    assert any("rejected hypothesis" in e.summary for e in result.state.events)


def test_a_good_hypothesis_is_kept():
    good = step(
        stop=True,
        hypotheses=[
            {"statement": "repeat array", "discriminating_evidence": "scan Rfam", "confidence": 0.7}
        ],
    )
    result = InvestigationLoop(demo_registry(), ScriptedInvestigator([good])).run(state())
    assert result.state.hypotheses[0].statement == "repeat array"


def test_an_investigator_that_raises_stops_the_loop_cleanly():
    class Broken:
        name = "broken"

        def next_step(self, state, catalogue):
            raise RuntimeError("model down")

    result = InvestigationLoop(demo_registry(), Broken()).run(state())
    assert result.stop.code == "agent_stopped"
    assert any("investigator failed" in e.summary for e in result.state.events)


def test_every_tool_run_is_in_the_log():
    loop = InvestigationLoop(
        demo_registry(),
        ScriptedInvestigator([step("cheap", inputs={"sequence": "ACGT"}), step(stop=True)]),
    )
    result = loop.run(state())
    kinds = [e.kind for e in result.state.events]
    assert "tool_request" in kinds and "tool_result" in kinds


# -- parsing ------------------------------------------------------------


def test_step_parses_from_a_fenced_block():
    assert _parse_step('```json\n{"stop": true}\n```')["stop"] is True


def test_step_parses_json_embedded_in_prose():
    assert _parse_step('sure: {"stop": false, "request": {}} ok')["stop"] is False


def test_an_unparseable_reply_stops_rather_than_inventing_a_step():
    parsed = _parse_step("I think we should look at the repeats!")
    assert parsed["stop"] is True
    assert "unparseable" in parsed["stop_reason"]


def test_llm_investigator_builds_a_prompt_naming_the_tools():
    seen = {}

    class Client:
        def complete(self, system, prompt):
            seen["prompt"] = prompt
            return '{"stop": true}'

    LLMInvestigator(client=Client()).next_step(state(), demo_registry().describe())
    assert "cheap" in seen["prompt"] and "pricey" in seen["prompt"]


# -- adversary and report -----------------------------------------------


class FixedClient:
    def __init__(self, stance, confidence=0.8):
        self.stance, self.confidence = stance, confidence

    def complete(self, system, prompt):
        return json.dumps(
            {
                "stance": self.stance,
                "confidence": self.confidence,
                "argument": "an argument",
                "what_would_settle_it": "an experiment",
            }
        )


def test_unanimous_refutation_eliminates():
    s = state()
    outcome = AdversarialReview(client=FixedClient("refuted")).run(s)
    assert outcome.survived is False
    assert s.status == "eliminated"


def test_surviving_every_challenge_keeps_it_alive():
    s = state()
    outcome = AdversarialReview(client=FixedClient("survives")).run(s)
    assert outcome.survived is True
    assert s.status == "investigating"


def test_refutation_outweighs_equal_support():
    from sde.adversary import REFUTATION_WEIGHT

    assert REFUTATION_WEIGHT > 1.0


def test_undecided_challenges_carry_no_weight():
    outcome = AdversarialReview(client=FixedClient("undecided")).run(state())
    assert outcome.support == 0.0 and outcome.opposition == 0.0
    assert outcome.unresolved


def test_a_broken_adversary_is_undecided_not_agreement():
    class Broken:
        def complete(self, system, prompt):
            raise RuntimeError("down")

    outcome = AdversarialReview(client=Broken()).run(state())
    assert all(c.stance == "undecided" for c in outcome.challenges)


def test_a_malformed_reply_is_undecided():
    class Garbage:
        def complete(self, system, prompt):
            return "looks novel to me!"

    outcome = AdversarialReview(client=Garbage()).run(state())
    assert all(c.stance == "undecided" for c in outcome.challenges)


def test_report_always_has_the_mandatory_sections():
    s = state()
    review = AdversarialReview(client=FixedClient("survives")).run(s)
    text = DiscoveryReport(s, review).render()
    assert "## What remains unknown" in text
    assert "## Counter-evidence" in text
    assert "## Provenance" in text


def test_an_unreviewed_report_says_so():
    text = DiscoveryReport(state(), None).render()
    assert "unreviewed" in text.lower()


def test_report_attributes_each_feature_to_its_producer():
    s = state()
    s.set_features({"gc_content": 0.61}, actor="tool:sequence_stats")
    text = DiscoveryReport(s, None).render()
    assert "gc_content" in text and "tool:sequence_stats" in text


def test_report_lists_failed_tools_under_unknowns():
    registry = demo_registry()

    @registry.tool("flaky", ToolCost.TRIVIAL, "fails")
    def _flaky(inputs):
        raise RuntimeError("nope")

    loop = InvestigationLoop(registry, ScriptedInvestigator([step("flaky"), step(stop=True)]))
    result = loop.run(state())
    text = DiscoveryReport(result.state, None).render()
    assert "`flaky` failed" in text


def test_report_is_saved_to_disk(tmp_path):
    path = DiscoveryReport(state(), None).save(tmp_path / "r.md")
    assert path.read_text(encoding="utf-8").startswith("# Candidate c1")
