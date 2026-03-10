from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState
from agents.config import load_agent_config


class CEOAgent(BaseAgent):
    """
    CEO Agent — top-level orchestrator of the multi-agent system.

    Responsibilities:
    1. Route request based on state.mode: generation → Content + Humanize + Export
                                          humanization → Humanize + Export
    2. Execute pipeline stages via existing Pipeline class (wrap, not rewrite)
    3. Manage feedback loop: if HM-5 fails → route to HM-2/3/4 (max 2 iterations)
    4. Escalation: after 2 failed iterations → partial accept with full score_report
    5. Track costs via state.cost_report

    This agent does NOT implement Stages 1-5 itself. It delegates to Pipeline.run()
    and Pipeline.run_from_params() from the existing pipeline/ package.
    """

    agent_name = "ceo"
    agent_type = "ceo"

    MAX_FEEDBACK_ITERATIONS = 2  # From IMPLEMENTATION_PLAN GAP 3

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Main entry point.

        Routes:
        - mode == "generation": Phase 0 (sources + generate) → Stages 1-5 → Export
        - mode == "humanization": Stages 1-5 → Export

        Feedback loop:
        - After Stages 1-5, check score_report for failures
        - If failures found AND iterations < MAX_FEEDBACK_ITERATIONS:
            → determine_feedback_route() → re-run Pipeline.run() with state.text
        - If iterations >= MAX_FEEDBACK_ITERATIONS → escalate (partial accept)
        """
        t0 = time.time()
        config = load_agent_config()

        logger.info(
            f"[CEO] Starting | mode={state.mode} | language={state.language} | "
            f"domain={state.domain} | stream_id={state.stream_id}"
        )

        try:
            if state.mode == "generation":
                state = await self._run_generation(state)
            elif state.mode == "humanization":
                state = await self._run_humanization(state)
            else:
                state.add_error(self.agent_name, f"Unknown mode: {state.mode}")
                return state

        except Exception as e:
            state.add_error(self.agent_name, f"Pipeline execution failed: {e}")
            logger.error(f"[CEO] Fatal error: {e}")

        elapsed = time.time() - t0
        logger.info(
            f"[CEO] Complete | elapsed={elapsed:.1f}s | "
            f"errors={len(state.errors)} | "
            f"feedback_iterations={state.feedback_iterations}"
        )

        return state

    async def _run_generation(self, state: PipelineState) -> PipelineState:
        """
        Generation mode: Phase 0 (ContentManager) → Stages 1-5 (Pipeline).

        Steps:
        1. ContentManager.execute(state) — runs Phase 0A (sources) + Phase 0B (generation)
           via MicroManager → Worker → generator.py chain
        2. Content QA gate — validates Phase 0 output
        3. Pipeline.run(state.text) — runs Stages 1-5 (humanization)
        4. Feedback loop — re-run if score fails
        """
        from pipeline import Pipeline
        from agents.content.manager import ContentManager

        logger.info("[CEO] Generation mode: ContentManager → Stages 1-5")

        # Step 1: Phase 0 via ContentManager → MM → Worker
        content_manager = ContentManager()
        state = await content_manager.execute(state)

        if not state.text:
            state.add_error(self.agent_name, "ContentManager produced no text")
            return state

        logger.info(
            f"[CEO] Phase 0 complete | words={state.word_count()} | "
            f"sections={len(state.generated_sections)} | "
            f"sources={len(state.source_list.sources) if state.source_list and hasattr(state.source_list, 'sources') else 0}"
        )

        # Step 2: Content QA gate
        state = await self._content_qa_check(state)

        # Step 3: Stages 1-5 (humanization) via Pipeline
        pipe = Pipeline()
        pipe._current_language = state.language

        output_text, score_report = pipe.run(
            text=state.text,
            verbose=True,
            domain_override=state.domain if state.domain != "general" else None,
            register_override=state.register if state.register != "general" else None,
        )

        state.text = output_text
        state.final_score_report = score_report

        # Step 4: Feedback loop
        state = await self._feedback_loop(state)

        return state

    async def _run_humanization(self, state: PipelineState) -> PipelineState:
        """
        Humanization mode: Stages 1-5 on existing text.

        Uses Pipeline.run() which internally runs all 5 stages.
        """
        from pipeline import Pipeline

        if not state.text:
            state.add_error(self.agent_name, "Humanization mode requires text input")
            return state

        logger.info(f"[CEO] Humanization mode: {state.word_count()} words input")

        pipe = Pipeline()

        # Set language for pipeline (it reads _current_language)
        pipe._current_language = state.language

        output_text, score_report = pipe.run(
            text=state.text,
            verbose=True,
            domain_override=state.domain if state.domain != "general" else None,
            register_override=state.register if state.register != "general" else None,
        )

        state.text = output_text
        state.final_score_report = score_report

        # Feedback loop
        state = await self._feedback_loop(state)

        return state

    async def _feedback_loop(self, state: PipelineState) -> PipelineState:
        """
        Feedback loop: check score_report, re-run if needed.

        Algorithm (from IMPLEMENTATION_PLAN GAP 3):
        1. Check score_report for hard/soft failures
        2. If all pass → return
        3. If failures AND iterations < MAX → determine route → re-run pipeline
        4. If iterations >= MAX → escalate (log warning, partial accept)
        """
        from pipeline import Pipeline

        while state.feedback_iterations < self.MAX_FEEDBACK_ITERATIONS:
            route = self._determine_feedback_route(state.final_score_report)

            if route is None:
                logger.info("[CEO] Feedback loop: all metrics pass")
                return state

            state.feedback_iterations += 1
            state.feedback_target = route
            state.feedback_from_qa = {
                "iteration": state.feedback_iterations,
                "route": route,
                "failed_metrics": self._get_failed_metrics(state.final_score_report),
            }

            logger.warning(
                f"[CEO] Feedback iteration {state.feedback_iterations}: "
                f"routing to {route} | failed metrics: "
                f"{state.feedback_from_qa['failed_metrics']}"
            )

            # Re-run full pipeline on current text
            # In future phases, this will route to specific HM stages (HM-2/3/4)
            # For Phase 1, we re-run the full pipeline as a simple feedback mechanism
            pipe = Pipeline()
            pipe._current_language = state.language
            output_text, score_report = pipe.run(
                text=state.text,
                verbose=True,
                domain_override=state.domain if state.domain != "general" else None,
                register_override=state.register if state.register != "general" else None,
            )

            state.text = output_text
            state.final_score_report = score_report

        # Max iterations reached — escalate
        if self._determine_feedback_route(state.final_score_report) is not None:
            logger.warning(
                f"[CEO] Escalation: max {self.MAX_FEEDBACK_ITERATIONS} iterations reached. "
                f"Partial accept with remaining failures."
            )
            state.add_error(
                self.agent_name,
                f"Feedback loop exhausted after {self.MAX_FEEDBACK_ITERATIONS} iterations. "
                f"Remaining failures: {self._get_failed_metrics(state.final_score_report)}"
            )

        return state

    def _determine_feedback_route(self, score_report: dict) -> Optional[str]:
        """
        Determine which HM stage to route feedback to.

        Uses priority-weighted routing from IMPLEMENTATION_PLAN GAP 3:
        - Collect all failed metrics with priorities
        - Group by route (hm2/hm3/hm4)
        - Return route with highest weighted score
        - Return None if all pass

        Route mapping:
        - hm2: structural issues (triplets, scaffold, connectors, paragraph CV)
        - hm3: lexical issues (P7 vocab, hedging, attribution, pattern elimination)
        - hm4: voice issues (burstiness, coherence, perplexity, generalization endings)
        """
        if not score_report:
            return None

        # Routing table: metric → (route, priority)
        # Priority: P1=highest(5), P2=4, P3=3, P4=2, P5=1
        ROUTING_TABLE: dict[str, tuple[str, int]] = {
            "triplet_count":                    ("hm2", 5),
            "announcement_opener_count":        ("hm2", 5),
            "para_ending_generalization_count":  ("hm4", 4),
            "paragraph_cv":                     ("hm2", 3),
            "section_cv":                       ("hm2", 3),
            "sentence_cv":                      ("hm4", 2),
            "p7_violation_count":               ("hm3", 3),
            "modal_hedging_on_results":         ("hm3", 3),
            "but_however_ratio":                ("hm2", 2),
            "no_odnako_ratio":                  ("hm2", 2),   # RU equivalent of but_however (AC-12)
            "connector_density_per_page":       ("hm2", 2),
            "pattern_elimination_rate":         ("hm3", 3),
            "perplexity_lift":                  ("hm4", 1),
            "coherence_score":                  ("hm4", 4),
            "length_reduction_ratio":           ("hm3", 1),
            "scaffold_signals_count":           ("hm2", 4),
            "attributive_passive_count":        ("hm3", 3),
        }

        # Threshold checks: metric_name → pass condition
        THRESHOLDS = {
            "triplet_count":                    lambda v: v is None or v == 0,
            "announcement_opener_count":        lambda v: v is None or v == 0,
            "para_ending_generalization_count":  lambda v: v is None or v == 0,
            "attributive_passive_count":        lambda v: v is None or v == 0,
            "scaffold_signals_count":           lambda v: v is None or v == 0,
            "p7_violation_count":               lambda v: v is None or v == 0,
            "modal_hedging_on_results":         lambda v: v is None or v == 0,
            "paragraph_cv":                     lambda v: v is not None and v >= 0.50,
            "section_cv":                       lambda v: v is not None and v >= 0.30,
            "sentence_cv":                      lambda v: v is not None and v >= 0.45,
            "but_however_ratio":                lambda v: v is None or v >= 2.0,  # None = RU, skip
            "no_odnako_ratio":                  lambda v: v is None or v >= 2.0,  # RU equivalent (AC-12)
            "connector_density_per_page":       lambda v: v is None or v <= 1.2,
            "pattern_elimination_rate":         lambda v: v is None or v >= 0.85,
            "perplexity_lift":                  lambda v: v is None or v >= 1.5,  # None = RU, skip
            "coherence_score":                  lambda v: v is None or v >= 0.80,
            "length_reduction_ratio":           lambda v: v is None or v <= 0.90,
        }

        # Collect failures
        route_scores: dict[str, int] = {"hm2": 0, "hm3": 0, "hm4": 0}

        for metric, (route, priority) in ROUTING_TABLE.items():
            value = score_report.get(metric)
            threshold_fn = THRESHOLDS.get(metric)

            if threshold_fn and not threshold_fn(value):
                route_scores[route] += priority

        # If no failures, return None
        if all(v == 0 for v in route_scores.values()):
            return None

        return max(route_scores, key=route_scores.get)

    def _get_failed_metrics(self, score_report: dict) -> list[str]:
        """Return list of metric names that failed their thresholds."""
        if not score_report:
            return []

        # Thresholds identical to _determine_feedback_route — extracted here
        # because _get_failed_metrics is a reporting utility, not a routing method.
        # In Phase 4+, both will use a shared class-level THRESHOLDS constant.
        THRESHOLDS = {
            "triplet_count":                    lambda v: v is None or v == 0,
            "announcement_opener_count":        lambda v: v is None or v == 0,
            "para_ending_generalization_count":  lambda v: v is None or v == 0,
            "attributive_passive_count":        lambda v: v is None or v == 0,
            "scaffold_signals_count":           lambda v: v is None or v == 0,
            "p7_violation_count":               lambda v: v is None or v == 0,
            "modal_hedging_on_results":         lambda v: v is None or v == 0,
            "paragraph_cv":                     lambda v: v is not None and v >= 0.50,
            "section_cv":                       lambda v: v is not None and v >= 0.30,
            "sentence_cv":                      lambda v: v is not None and v >= 0.45,
            "but_however_ratio":                lambda v: v is None or v >= 2.0,
            "no_odnako_ratio":                  lambda v: v is None or v >= 2.0,  # RU equivalent (AC-12)
            "connector_density_per_page":       lambda v: v is None or v <= 1.2,
            "pattern_elimination_rate":         lambda v: v is None or v >= 0.85,
            "perplexity_lift":                  lambda v: v is None or v >= 1.5,
            "coherence_score":                  lambda v: v is None or v >= 0.80,
            "length_reduction_ratio":           lambda v: v is None or v <= 0.90,
        }

        failed: list[str] = []
        for metric, threshold_fn in THRESHOLDS.items():
            value = score_report.get(metric)
            if not threshold_fn(value):
                failed.append(f"{metric}={value}")
        return failed

    async def _content_qa_check(self, state: PipelineState) -> PipelineState:
        """
        Run ContentQAGate on Phase 0 output (generation mode only).
        Checks: announcement openers=0, triplets=0, Block 12=0, viz count >= minimum.
        """
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()
        state = await gate.execute(state)
        return state
