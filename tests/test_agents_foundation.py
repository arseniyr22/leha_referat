"""
Phase 0 Foundation Tests.
Run: pytest tests/test_agents_foundation.py -v
"""
from __future__ import annotations

import pytest


# ── Test 1: PipelineState creation with defaults ──────────────────────

class TestPipelineState:
    def test_creation_with_mode_only(self):
        """PipelineState can be created with just mode — all else defaults."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization")
        assert state.mode == "humanization"
        assert state.text == ""
        assert state.language == "en"
        assert state.domain == "general"
        assert state.errors == []
        assert state.feedback_iterations == 0
        assert state.skipped_workers == []

    def test_creation_generation_mode(self):
        """PipelineState for generation mode has all needed fields."""
        from agents.state import PipelineState
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            topic="Влияние цифровизации на банковский сектор РФ",
            language="ru",
            domain="economics",
            register="academic",
            level="bachelor",
        )
        assert state.mode == "generation"
        assert state.stream_id == "vkr"
        assert state.language == "ru"
        assert state.register == "academic"
        assert state.word_count() == 0  # text not yet generated

    def test_add_error(self):
        """add_error() formats and appends correctly."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization")
        state.add_error("hm2_triplet_buster", "Regex timeout on chunk 3")
        assert len(state.errors) == 1
        assert "[hm2_triplet_buster]" in state.errors[0]
        assert state.has_errors() is True

    def test_word_count(self):
        """word_count() returns correct count."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization", text="This is a test sentence with eight words total.")
        assert state.word_count() == 9  # 9 words in the sentence above


# ── Test 2: CostReport accumulation ───────────────────────────────────

class TestCostReport:
    def test_add_usage(self):
        """CostReport.add_usage() accumulates tokens and call counts."""
        from agents.state import CostReport
        report = CostReport()
        report.add_usage("hm2_scaffold_breaker", {
            "input_tokens": 1500,
            "output_tokens": 800,
            "cache_read_input_tokens": 1200,
            "cache_creation_input_tokens": 0,
        })
        assert report.total_input_tokens == 1500
        assert report.total_output_tokens == 800
        assert report.total_cache_read_tokens == 1200
        assert report.total_api_calls == 1
        assert report.calls_by_agent["hm2_scaffold_breaker"] == 1

    def test_multiple_agents(self):
        """CostReport tracks calls from multiple agents independently."""
        from agents.state import CostReport
        report = CostReport()
        report.add_usage("hm2_scaffold_breaker", {"input_tokens": 100, "output_tokens": 50})
        report.add_usage("hm2_triplet_buster", {"input_tokens": 200, "output_tokens": 100})
        report.add_usage("hm2_scaffold_breaker", {"input_tokens": 150, "output_tokens": 75})
        assert report.total_api_calls == 3
        assert report.calls_by_agent["hm2_scaffold_breaker"] == 2
        assert report.calls_by_agent["hm2_triplet_buster"] == 1
        assert report.total_input_tokens == 450


# ── Test 3: BaseAgent interface ───────────────────────────────────────

class TestBaseAgent:
    def test_cannot_instantiate_abstract(self):
        """BaseAgent cannot be instantiated directly — it's abstract."""
        from agents.base import BaseAgent
        with pytest.raises(TypeError):
            BaseAgent()

    def test_concrete_agent_works(self):
        """A concrete agent implementing execute() can be instantiated."""
        from agents.base import BaseAgent
        from agents.state import PipelineState

        class DummyAgent(BaseAgent):
            agent_name = "dummy"
            agent_type = "worker"

            async def execute(self, state: PipelineState) -> PipelineState:
                state.text = "transformed"
                return state

        agent = DummyAgent()
        assert agent.agent_name == "dummy"
        assert agent.agent_type == "worker"
        assert repr(agent) == "<DummyAgent name=dummy type=worker>"

    def test_load_prompt_not_found(self):
        """load_prompt() raises FileNotFoundError for missing prompts."""
        from agents.base import BaseAgent
        from agents.state import PipelineState

        class DummyAgent(BaseAgent):
            agent_name = "dummy"
            agent_type = "worker"
            async def execute(self, state: PipelineState) -> PipelineState:
                return state

        agent = DummyAgent()
        with pytest.raises(FileNotFoundError):
            agent.load_prompt("nonexistent_prompt")


# ── Test 4: AgentConfig loading ───────────────────────────────────────

class TestAgentConfig:
    def test_load_with_existing_config(self):
        """AgentConfig loads defaults from pipeline section of config.yaml."""
        from agents.config import load_agent_config
        config = load_agent_config()
        assert config.rewrite_model == "claude-sonnet-4-6"
        assert config.max_retries == 3
        assert config.max_feedback_iterations == 2

    def test_default_values(self):
        """AgentConfig has sensible defaults for agent-specific fields."""
        from agents.config import AgentConfig
        config = AgentConfig()
        assert config.max_cost_per_request_usd == 15.0
        assert config.enable_smart_skip is True


# ── Test 5: Existing pipeline not broken ──────────────────────────────

class TestExistingPipelineIntact:
    def test_pipeline_imports_still_work(self):
        """Importing pipeline modules still works after agents/ package added."""
        from pipeline import load_config, load_prompt, chunk_text
        cfg = load_config()
        assert "pipeline" in cfg
        assert "scoring" in cfg

    def test_pipeline_class_instantiation(self):
        """Pipeline class can still be instantiated."""
        from pipeline import Pipeline
        pipe = Pipeline()
        assert hasattr(pipe, "run")
        assert hasattr(pipe, "run_from_params")
