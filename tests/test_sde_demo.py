from __future__ import annotations

from sde.adversary import AdversarialReview
from sde.demo import CautiousAdversary, script, synthesise
from sde.loop import InvestigationLoop, ScriptedInvestigator
from sde.report import DiscoveryReport
from sde.state import CandidateState
from sde.tools import registry


def run():
    sequence = synthesise()
    state = CandidateState(candidate_id="t", sequence=sequence, contig_id="c")
    result = InvestigationLoop(registry, ScriptedInvestigator(script(sequence))).run(state)
    review = AdversarialReview(client=CautiousAdversary()).run(state)
    return state, result, review


def test_the_planted_array_is_recovered():
    state, _, _ = run()
    assert state.features["repeat_copy_count"] == 9.0
    assert state.features["repeat_mean_period"] == 140.0


def test_cheap_tools_run_before_expensive_ones():
    state, _, _ = run()
    costs = [
        e.payload["cost"] for e in state.events if e.kind == "tool_result"
    ]
    assert costs == sorted(costs)


def test_an_uninstalled_tool_fails_loudly_rather_than_returning_numbers():
    state, _, _ = run()
    failed = [
        e for e in state.events
        if e.kind == "tool_result" and e.payload.get("tool") == "infernal_scan"
    ]
    assert failed and not failed[0].payload["ok"]
    assert "not installed" in failed[0].payload["error"]


def test_the_report_records_that_novelty_was_not_established():
    state, _, review = run()
    text = DiscoveryReport(state, review).render()
    assert "`infernal_scan` failed" in text
    assert "already_described` was inconclusive" in text


def test_every_feature_traces_to_the_tool_that_produced_it():
    state, _, _ = run()
    producers = {
        key
        for event in state.events
        if event.kind == "feature"
        for key in event.payload.get("changes", {})
    }
    assert set(state.features) <= producers


def test_the_whole_run_costs_little_because_the_agent_enters_late():
    state, _, _ = run()
    assert state.spent < 20


def test_the_state_survives_a_round_trip(tmp_path):
    state, _, _ = run()
    restored = CandidateState.load(state.save(tmp_path / "s.json"))
    assert restored.features == state.features
    assert len(restored.events) == len(state.events)
