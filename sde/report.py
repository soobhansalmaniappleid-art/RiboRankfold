"""The discovery report.

Two sections are mandatory and are the reason the format exists:
**what remains unknown**, and **counter-evidence**. A report that lists only
supporting evidence is a pitch. These sections are rendered even when empty,
with an explicit statement that nothing was found, so their absence is always a
finding rather than an omission.

The report is generated from `CandidateState` alone. Nothing may appear in it
that is not in the event log, which is what makes the claim auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sde.adversary import ReviewOutcome
from sde.state import CandidateState


@dataclass(slots=True)
class DiscoveryReport:
    state: CandidateState
    review: ReviewOutcome | None = None

    def render(self) -> str:
        state = self.state
        lines = [
            f"# Candidate {state.candidate_id}",
            "",
            f"- Status: `{state.status}`",
            f"- Contig: `{state.contig_id or 'unknown'}`",
            f"- Sequence length: {len(state.sequence)}",
            f"- Budget spent: {state.spent}",
            f"- Events recorded: {len(state.events)}",
            "",
        ]
        lines += self._unusual()
        lines += self._evidence()
        lines += self._hypotheses()
        lines += self._counter_evidence()
        lines += self._analyses()
        lines += self._unknown()
        lines += self._validation()
        lines += self._provenance()
        return "\n".join(lines)

    # -- sections -------------------------------------------------------
    def _unusual(self) -> list[str]:
        observations = [
            f"- {event.summary}"
            for event in self.state.events
            if event.kind == "hypothesis"
        ]
        return [
            "## What is unusual",
            "",
            *(observations or ["- Nothing was flagged as unusual."]),
            "",
        ]

    def _evidence(self) -> list[str]:
        features = self.state.features
        if not features:
            return ["## Evidence", "", "No features were computed.", ""]
        rows = ["| feature | value | produced by |", "|---|---|---|"]
        producers = self._producers()
        for key in sorted(features):
            rows.append(f"| `{key}` | {features[key]} | {producers.get(key, 'unknown')} |")
        return ["## Evidence", "", *rows, ""]

    def _hypotheses(self) -> list[str]:
        if not self.state.hypotheses:
            return ["## Hypotheses", "", "None were proposed.", ""]
        rows = ["| statement | status | confidence | would be settled by |", "|---|---|---|---|"]
        for h in self.state.hypotheses:
            rows.append(
                f"| {h.statement} | {h.status} | {h.confidence:.2f} | "
                f"{h.discriminating_evidence} |"
            )
        return ["## Hypotheses", "", *rows, ""]

    def _counter_evidence(self) -> list[str]:
        """Mandatory. Rendered even when empty, and says so."""
        lines = ["## Counter-evidence", ""]
        if self.review is None:
            lines += ["No adversarial review was run. **This claim is unreviewed.**", ""]
            return lines
        refuted = [c for c in self.review.challenges if c.stance == "refuted"]
        if not refuted:
            lines.append(
                "Every challenge was attempted and none succeeded. That is weaker "
                "than it sounds: it means no mundane explanation was *found*, not "
                "that none exists."
            )
        for challenge in refuted:
            lines.append(
                f"- **{challenge.name}** ({challenge.confidence:.2f}): {challenge.argument}"
            )
        lines += [
            "",
            f"Support {self.review.support:.3f} vs opposition {self.review.opposition:.3f} "
            f"(refutations weighted higher than endorsements).",
            "",
        ]
        return lines

    def _analyses(self) -> list[str]:
        runs = [
            event
            for event in self.state.events
            if event.kind == "tool_result"
        ]
        if not runs:
            return ["## Analyses performed", "", "No tools were run.", ""]
        rows = ["| tool | outcome | cost | why it was run |", "|---|---|---|---|"]
        for event in runs:
            payload = event.payload
            outcome = "ok" if payload.get("ok") else f"failed: {payload.get('error', '')[:60]}"
            rows.append(
                f"| `{payload.get('tool')}` | {outcome} | {payload.get('cost')} | "
                f"{payload.get('reason', '')} |"
            )
        return ["## Analyses performed", "", *rows, ""]

    def _unknown(self) -> list[str]:
        """Mandatory. What the investigation did not settle."""
        lines = ["## What remains unknown", ""]
        open_hypotheses = self.state.open_hypotheses()
        for h in open_hypotheses:
            lines.append(f"- Unresolved: {h.statement} — needs {h.discriminating_evidence}")
        if self.review and self.review.unresolved:
            for name in self.review.unresolved:
                lines.append(f"- Challenge `{name}` was inconclusive on this evidence.")
        failed = [
            event.payload.get("tool")
            for event in self.state.events
            if event.kind == "tool_result" and not event.payload.get("ok")
        ]
        for tool in failed:
            lines.append(f"- `{tool}` failed, so that line of evidence is missing.")
        stops = [
            event for event in self.state.events
            if event.kind == "note" and event.summary.startswith("investigation stopped")
        ]
        if stops:
            detail = stops[-1].payload.get("detail", "")
            code = stops[-1].payload.get("code")
            lines.append(f"- Investigation ended because: {code} ({detail}).")
        if len(lines) == 2:
            lines.append(
                "- Nothing was recorded as unresolved. Treat that with suspicion: a "
                "real investigation usually leaves open questions."
            )
        lines.append("")
        return lines

    def _validation(self) -> list[str]:
        suggestions = [
            h.discriminating_evidence
            for h in self.state.hypotheses
            if h.status == "open" and h.discriminating_evidence
        ]
        if self.review:
            suggestions += [
                c.what_would_settle_it for c in self.review.challenges if c.what_would_settle_it
            ]
        unique = list(dict.fromkeys(s for s in suggestions if s))
        return [
            "## Suggested validation",
            "",
            *([f"- {item}" for item in unique] or ["- No validating experiment was proposed."]),
            "",
        ]

    def _provenance(self) -> list[str]:
        rows = ["| # | when | actor | event | summary |", "|---|---|---|---|---|"]
        for event in self.state.events:
            rows.append(
                f"| {event.seq} | {event.at} | `{event.actor}` | {event.kind} | {event.summary} |"
            )
        return [
            "## Provenance",
            "",
            "Every line above is derived from this log. Nothing in this report "
            "comes from anywhere else.",
            "",
            *rows,
            "",
        ]

    def _producers(self) -> dict[str, str]:
        """Which actor last set each feature."""
        producers: dict[str, str] = {}
        for event in self.state.events:
            if event.kind == "feature":
                for key in event.payload.get("changes", {}):
                    producers[key] = f"`{event.actor}`"
        return producers

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        return path
