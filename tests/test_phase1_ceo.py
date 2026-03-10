"""
Phase 1 CEO Agent Tests.
Run: pytest tests/test_phase1_ceo.py -v
"""
from __future__ import annotations

import pytest


# ── Test 1: CEO routing ─────────────────────────────────────────────────


class TestCEORouting:
    def test_ceo_instantiation(self):
        """CEOAgent can be instantiated."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()
        assert ceo.agent_name == "ceo"
        assert ceo.agent_type == "ceo"

    def test_ceo_is_base_agent(self):
        """CEOAgent inherits from BaseAgent."""
        from agents.ceo import CEOAgent
        from agents.base import BaseAgent
        ceo = CEOAgent()
        assert isinstance(ceo, BaseAgent)

    def test_unknown_mode_produces_error(self):
        """Unknown mode adds error to state."""
        import asyncio
        from agents.ceo import CEOAgent
        from agents.state import PipelineState

        ceo = CEOAgent()
        state = PipelineState(mode="invalid_mode")
        result = asyncio.run(ceo.execute(state))
        assert result.has_errors()
        assert "Unknown mode" in result.errors[0]

    def test_humanization_without_text_produces_error(self):
        """Humanization mode with empty text adds error."""
        import asyncio
        from agents.ceo import CEOAgent
        from agents.state import PipelineState

        ceo = CEOAgent()
        state = PipelineState(mode="humanization", text="")
        result = asyncio.run(ceo.execute(state))
        assert result.has_errors()
        assert "requires text input" in result.errors[0]


# ── Test 2: Feedback routing logic ───────────────────────────────────────


class TestFeedbackRouting:
    def test_all_pass_returns_none(self):
        """When all metrics pass, route is None."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "scaffold_signals_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route is None

    def test_structural_failures_route_to_hm2(self):
        """Structural failures (triplets, scaffold) route to HM-2."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 3,             # FAIL → hm2 (P1=5)
            "announcement_opener_count": 2,  # FAIL → hm2 (P1=5)
            "scaffold_signals_count": 1,     # FAIL → hm2 (P2=4)
            # Everything else passes:
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route == "hm2"

    def test_lexical_failures_route_to_hm3(self):
        """Lexical failures (P7, hedging) route to HM-3."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "scaffold_signals_count": 0,
            "para_ending_generalization_count": 0,
            "p7_violation_count": 5,              # FAIL → hm3 (P3=3)
            "modal_hedging_on_results": 3,        # FAIL → hm3 (P3=3)
            "attributive_passive_count": 2,       # FAIL → hm3 (P3=3)
            "pattern_elimination_rate": 0.60,     # FAIL → hm3 (P3=3)
            # Everything else passes:
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route == "hm3"

    def test_russian_skips_perplexity_and_but_however(self):
        """Russian metrics (perplexity=None, but_however=None) are skipped."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "scaffold_signals_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": None,            # RU → skip
            "no_odnako_ratio": 2.5,               # RU equivalent active
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": None,              # RU → skip
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route is None  # No failures

    def test_empty_score_report_returns_none(self):
        """Empty score report returns None (no failures detected)."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()
        assert ceo._determine_feedback_route({}) is None
        assert ceo._determine_feedback_route(None) is None


# ── Test 3: ContentQA Gate ───────────────────────────────────────────────


class TestContentQAGate:
    def test_gate_instantiation(self):
        """ContentQAGate can be instantiated."""
        from agents.gates.content_qa import ContentQAGate
        gate = ContentQAGate()
        assert gate.agent_name == "content_qa_gate"
        assert gate.agent_type == "gate"

    def test_gate_skips_humanization_mode(self):
        """ContentQAGate skips if mode is humanization."""
        import asyncio
        from agents.gates.content_qa import ContentQAGate
        from agents.state import PipelineState

        gate = ContentQAGate()
        state = PipelineState(mode="humanization")
        result = asyncio.run(gate.execute(state))
        assert not result.has_errors()

    def test_viz_minimum_lookup(self):
        """Visualization minimums match БЛОК 16.2."""
        from agents.gates.content_qa import ContentQAGate
        gate = ContentQAGate()
        assert gate._get_viz_minimum("vkr", "bachelor") == 5
        assert gate._get_viz_minimum("vkr", "master") == 8
        assert gate._get_viz_minimum("coursework", "bachelor") == 3
        assert gate._get_viz_minimum("composition", "bachelor") == 0
        assert gate._get_viz_minimum("unknown_stream", "bachelor") == 0


# ── Test 4: Phase 0 not broken ──────────────────────────────────────────


class TestPhase0Intact:
    def test_foundation_imports(self):
        """Phase 0 imports still work after Phase 1 additions."""
        from agents.base import BaseAgent
        from agents.state import PipelineState, CostReport
        from agents.config import load_agent_config, AgentConfig
        assert True  # If we get here, imports work

    def test_pipeline_imports(self):
        """Existing pipeline imports still work."""
        from pipeline import Pipeline, load_config
        pipe = Pipeline()
        assert hasattr(pipe, "run")
        assert hasattr(pipe, "run_from_params")
