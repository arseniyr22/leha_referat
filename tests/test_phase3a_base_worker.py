"""
Phase 3A Tests: BaseSectionWorker + MicroManager Integration + HandoffGate.
Run: pytest tests/test_phase3a_base_worker.py -v

Tests:
1. BaseSectionWorker instantiation and properties
2. BaseSectionWorker format-only section handling
3. BaseSectionWorker viz counting integration
4. BaseMicroManager._get_worker() is abstract
5. Concrete MMs implement _get_worker() (returns None in 3A)
6. BaseMicroManager.execute() skips when no workers
7. HandoffGate validation — clean text passes
8. HandoffGate validation — detects violations
9. HandoffGate metadata packaging
10. HandoffGate register/domain mapping
11. PipelineState has last_section_text field
12. AcademicGenerator has generate_section() method
13. Cross-check: DOMAIN_MAP matches generator.py
14. Cross-check: REGISTER_MAP matches generator.py
15. Phase 2 tests still pass (regression)
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: BaseSectionWorker basics ──────────────────────────────


class TestBaseSectionWorker:
    def test_instantiation(self):
        """BaseSectionWorker cannot be instantiated directly (abstract execute via BaseAgent)."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        # BaseSectionWorker inherits from BaseAgent which has abstract execute()
        # But BaseSectionWorker implements execute(), so it CAN be instantiated
        worker = BaseSectionWorker()
        assert worker.agent_type == "worker"
        assert worker.section_id == ""

    def test_agent_type_is_worker(self):
        """All section workers have agent_type 'worker'."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        worker = BaseSectionWorker()
        assert worker.agent_type == "worker"

    def test_format_only_sections_skip(self):
        """title_page and toc sections skip generation."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.state import PipelineState

        class TitlePageWorker(BaseSectionWorker):
            section_id = "title_page"
            agent_name = "test_title_page"

        worker = TitlePageWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert "title_page" in result.generated_sections
        assert result.generated_sections["title_page"] == ""

    def test_empty_section_id_produces_error(self):
        """Worker with empty section_id adds error."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.state import PipelineState

        worker = BaseSectionWorker()  # section_id = ""
        worker.agent_name = "test_empty"
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert result.has_errors()
        assert "section_id" in result.errors[0].lower()


# ── Test 2: BaseMicroManager abstract _get_worker ─────────────────


class TestBaseMicroManagerAbstract:
    def test_get_worker_is_abstract(self):
        """BaseMicroManager._get_worker() is abstract — cannot instantiate base directly."""
        from agents.content.micro_managers.base import BaseMicroManager

        # BaseMicroManager has abstract _get_worker(), so direct instantiation should fail
        with pytest.raises(TypeError):
            BaseMicroManager()

    def test_concrete_mms_implement_get_worker(self):
        """All 7 concrete MMs implement _get_worker()."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [
            MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch,
            MicroManagerAbstractPaper, MicroManagerText, MicroManagerEssay,
            MicroManagerComposition,
        ]:
            mm = mm_class()
            # Should not raise — method exists
            result = mm._get_worker("test_section")
            # Phase 3A: all return None
            assert result is None, f"{mm.agent_name}._get_worker() should return None in Phase 3A"


# ── Test 3: MicroManager execute with no workers ──────────────────


class TestMicroManagerExecuteNoWorkers:
    def test_execute_skips_all_sections(self):
        """MM execute() skips all sections when _get_worker returns None."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.state import PipelineState

        mm = MicroManagerVKR()
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            topic="Test topic",
            level="bachelor",
        )
        result = asyncio.run(mm.execute(state))

        # Should not error — skipping sections is graceful
        # (workers are None, so sections are skipped with warning)
        assert result.visualization_count == {"tables": 0, "figures": 0}

    def test_execute_preserves_section_order(self):
        """MM SECTION_ORDER is unchanged after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from pipeline.generator import SECTION_ORDER

        mm = MicroManagerVKR()
        assert mm.SECTION_ORDER == SECTION_ORDER["vkr"]


# ── Test 4: HandoffGate basics ────────────────────────────────────


class TestHandoffGate:
    def test_instantiation(self):
        """HandoffGate instantiates with correct properties."""
        from agents.gates.handoff_gate import HandoffGate
        gate = HandoffGate()
        assert gate.agent_name == "handoff_gate"
        assert gate.agent_type == "gate"

    def test_is_base_agent(self):
        """HandoffGate inherits from BaseAgent."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.base import BaseAgent
        gate = HandoffGate()
        assert isinstance(gate, BaseAgent)

    def test_no_text_produces_error(self):
        """HandoffGate adds error when state has no text."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        gate = HandoffGate()
        state = PipelineState(mode="generation", text="")
        result = asyncio.run(gate.execute(state))
        assert result.has_errors()
        assert "no text" in result.errors[0].lower()

    def test_clean_text_passes(self):
        """HandoffGate passes clean text without violations."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        gate = HandoffGate()
        state = PipelineState(
            mode="generation",
            text="This is a clean paragraph without any AI patterns. "
                 "It discusses economics and monetary policy.",
            stream_id="text",
            language="en",
            domain="economics",
        )
        result = asyncio.run(gate.execute(state))

        # No errors from handoff itself
        handoff = result.analysis_report.get("handoff_metadata")
        assert handoff is not None
        assert handoff["register"] == "journalistic"  # text → journalistic
        assert handoff["domain"] == "economics"

    def test_detects_announcement_openers(self):
        """HandoffGate detects announcement opener violations."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        text_with_openers = (
            "Here's the problem with modern economics. "
            "This topic also deserves mention in the context of policy."
        )
        gate = HandoffGate()
        state = PipelineState(
            mode="generation",
            text=text_with_openers,
            stream_id="text",
            language="en",
        )
        result = asyncio.run(gate.execute(state))

        handoff = result.analysis_report.get("handoff_metadata")
        assert handoff is not None
        assert len(handoff["structural_violations"]) > 0
        assert any("announcement" in v for v in handoff["structural_violations"])


# ── Test 5: HandoffGate register/domain mapping ──────────────────


class TestHandoffGateMapping:
    def test_register_mapping_all_streams(self):
        """HandoffGate maps all stream_ids to correct registers."""
        from agents.gates.handoff_gate import HandoffGate
        from pipeline.generator import REGISTER_MAP

        gate = HandoffGate()
        for stream_id, expected_register in REGISTER_MAP.items():
            assert gate.REGISTER_MAP[stream_id] == expected_register, (
                f"Register mismatch for {stream_id}: "
                f"HandoffGate={gate.REGISTER_MAP[stream_id]} vs generator={expected_register}"
            )

    def test_domain_mapping_all_domains(self):
        """HandoffGate maps all domains to correct pipeline codes."""
        from agents.gates.handoff_gate import HandoffGate
        from pipeline.generator import DOMAIN_MAP

        gate = HandoffGate()
        for domain, expected_code in DOMAIN_MAP.items():
            assert gate.DOMAIN_MAP[domain] == expected_code, (
                f"Domain mismatch for {domain}: "
                f"HandoffGate={gate.DOMAIN_MAP[domain]} vs generator={expected_code}"
            )


# ── Test 6: PipelineState new field ──────────────────────────────


class TestPipelineStateNewField:
    def test_last_section_text_exists(self):
        """PipelineState has last_section_text field with default empty string."""
        from agents.state import PipelineState
        state = PipelineState(mode="generation")
        assert hasattr(state, "last_section_text")
        assert state.last_section_text == ""

    def test_last_section_text_mutable(self):
        """last_section_text can be set and read."""
        from agents.state import PipelineState
        state = PipelineState(mode="generation")
        state.last_section_text = "Some generated text here"
        assert state.last_section_text == "Some generated text here"


# ── Test 7: AcademicGenerator.generate_section() exists ──────────


class TestGeneratorNewMethod:
    def test_generate_section_method_exists(self):
        """AcademicGenerator has generate_section() method."""
        from pipeline.generator import AcademicGenerator
        assert hasattr(AcademicGenerator, "generate_section")

    def test_generate_section_signature(self):
        """generate_section() accepts expected parameters."""
        import inspect
        from pipeline.generator import AcademicGenerator

        sig = inspect.signature(AcademicGenerator.generate_section)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "section_id" in params
        assert "params" in params
        assert "source_list" in params
        assert "previously_generated" in params

    def test_generate_section_format_only_returns_empty(self):
        """generate_section('title_page') returns empty string."""
        from pipeline.generator import AcademicGenerator, GenerationParams
        from pipeline import load_config

        config = load_config()
        gen = AcademicGenerator(config)
        params = GenerationParams(stream_id="vkr", topic="Test", language="ru")

        result = gen.generate_section("title_page", params)
        assert result == ""

        result2 = gen.generate_section("toc", params)
        assert result2 == ""


# ── Test 8: HandoffMetadata dataclass ─────────────────────────────


class TestHandoffMetadata:
    def test_creation(self):
        """HandoffMetadata can be created with required fields."""
        from agents.gates.handoff_gate import HandoffMetadata
        meta = HandoffMetadata(text="Some text")
        assert meta.text == "Some text"
        assert meta.source_count == 0
        assert meta.viz_count_tables == 0
        assert meta.structural_violations == []

    def test_full_creation(self):
        """HandoffMetadata with all fields."""
        from agents.gates.handoff_gate import HandoffMetadata
        meta = HandoffMetadata(
            text="Full text",
            source_count=25,
            viz_count_tables=3,
            viz_count_figures=2,
            domain="cs",
            register="academic",
            language="ru",
            stream_id="vkr",
            level="bachelor",
            sections_generated=9,
            structural_violations=["triplets=2"],
        )
        assert meta.source_count == 25
        assert meta.viz_count_tables == 3
        assert meta.sections_generated == 9
        assert len(meta.structural_violations) == 1


# ── Test 9: Phase 2 regression — SECTION_ORDERs still match ──────


class TestPhase2Regression:
    def test_all_section_orders_still_match_generator(self):
        """Phase 2 SECTION_ORDER cross-check still passes after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from pipeline.generator import SECTION_ORDER

        mm_map = {
            "vkr": MicroManagerVKR,
            "coursework": MicroManagerCoursework,
            "research": MicroManagerResearch,
            "abstract_paper": MicroManagerAbstractPaper,
            "text": MicroManagerText,
            "essay": MicroManagerEssay,
            "composition": MicroManagerComposition,
        }

        for stream_id, mm_class in mm_map.items():
            mm = mm_class()
            generator_order = SECTION_ORDER[stream_id]
            assert mm.SECTION_ORDER == generator_order, (
                f"{mm.agent_name} SECTION_ORDER mismatch: "
                f"MM={mm.SECTION_ORDER} vs generator={generator_order}"
            )

    def test_all_viz_minimums_still_match_content_qa_gate(self):
        """Phase 2 VIZ_MINIMUMS cross-check still passes after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()

        stream_checks = {
            "vkr": (MicroManagerVKR, ["bachelor", "master", "specialist", "postgraduate"]),
            "coursework": (MicroManagerCoursework, ["default", "bachelor", "master"]),
            "research": (MicroManagerResearch, ["default", "bachelor", "master"]),
            "abstract_paper": (MicroManagerAbstractPaper, ["default", "bachelor"]),
            "text": (MicroManagerText, ["default", "bachelor"]),
            "essay": (MicroManagerEssay, ["default", "bachelor"]),
            "composition": (MicroManagerComposition, ["default", "bachelor"]),
        }

        for stream_id, (mm_class, levels) in stream_checks.items():
            mm = mm_class()
            gate_stream = gate.VIZ_MINIMUMS.get(stream_id, {})

            for level in levels:
                mm_val = mm.get_viz_minimum(level)
                gate_val = gate_stream.get(level, gate_stream.get("default", 0))
                assert mm_val == gate_val, (
                    f"VIZ_MINIMUMS mismatch for {stream_id}/{level}: "
                    f"MM={mm_val} vs ContentQAGate={gate_val}"
                )


# ── Test 10: count_visualizations still works ─────────────────────


class TestCountVisualizationsRegression:
    def test_count_tables(self):
        """count_visualizations still counts markdown tables correctly."""
        text = """
| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |

Some text.

| X | Y |
|---|---|
| 1 | 2 |
"""
        # Cannot call static method on abstract class directly in Phase 3A
        # because BaseMicroManager is now abstract. Use a concrete MM instead.
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 2
        assert figures == 0

    def test_count_figures(self):
        """count_visualizations still counts figure placeholders correctly."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        text = """
[РИСУНОК 1 — Структура]

Some text.

[FIGURE 2 — Architecture]
"""
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 0
        assert figures == 2
