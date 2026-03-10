from __future__ import annotations

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class ContentQAGate(BaseAgent):
    """
    Content QA Gate — validates Phase 0 generation output.

    Checks (from IMPLEMENTATION_PLAN Phase 1):
    1. Announcement openers = 0
    2. Triplet instances = 0
    3. Block 12 violations = 0
    4. Visualization count >= stream minimum (БЛОК 16.2)

    If hard failures detected → adds warnings to state.errors
    (actual re-generation is handled by Content Manager in Phase 2).
    In Phase 1, this gate only REPORTS — it does not trigger re-generation.
    """

    agent_name = "content_qa_gate"
    agent_type = "gate"

    # БЛОК 16.2 visualization minimums
    VIZ_MINIMUMS: dict[str, dict[str, int]] = {
        "vkr": {"bachelor": 5, "master": 8, "specialist": 5, "postgraduate": 10},
        "coursework": {"default": 3},
        "research": {"default": 3},
        "abstract_paper": {"default": 1},
        "text": {"default": 0},
        "essay": {"default": 0},
        "composition": {"default": 0},
    }

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Validate Phase 0 output quality.

        Reads metrics from state.final_score_report (populated by Pipeline.run_from_params).
        Reports violations as warnings — does not block pipeline.
        """
        if state.mode != "generation":
            return state

        report = state.final_score_report
        if not report:
            logger.warning("[ContentQA] No score report available — skipping QA")
            return state

        violations: list[str] = []

        # Check 1: Announcement openers
        opener_count = report.get("announcement_opener_count", 0)
        if opener_count and opener_count > 0:
            violations.append(f"announcement_openers={opener_count} (target: 0)")

        # Check 2: Triplet instances
        triplet_count = report.get("triplet_count", 0)
        if triplet_count and triplet_count > 0:
            violations.append(f"triplets={triplet_count} (target: 0)")

        # Check 3: Block 12 violations (structural patterns)
        block12 = report.get("block12_violations", 0)
        if block12 and block12 > 0:
            violations.append(f"block12_violations={block12} (target: 0)")

        # Check 4: Visualization count
        viz_count = report.get("generation", {}).get("viz_count", None)
        if viz_count is not None:
            total_viz = viz_count if isinstance(viz_count, int) else viz_count.get("total", 0)
            minimum = self._get_viz_minimum(state.stream_id, state.level)
            if total_viz < minimum:
                violations.append(
                    f"visualizations={total_viz} (minimum: {minimum} for {state.stream_id}/{state.level})"
                )

        if violations:
            logger.warning(f"[ContentQA] {len(violations)} violations found: {violations}")
            for v in violations:
                state.add_error(self.agent_name, f"Content QA violation: {v}")
        else:
            logger.info("[ContentQA] All checks passed")

        return state

    def _get_viz_minimum(self, stream_id: str, level: str) -> int:
        """Get visualization minimum from БЛОК 16.2 table."""
        stream_mins = self.VIZ_MINIMUMS.get(stream_id, {"default": 0})
        return stream_mins.get(level, stream_mins.get("default", 0))
