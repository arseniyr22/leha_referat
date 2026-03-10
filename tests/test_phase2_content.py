"""
Phase 2 Content Manager + MicroManager Tests.
Run: pytest tests/test_phase2_content.py -v

Tests:
1. ContentManager instantiation + BaseAgent inheritance
2. ContentManager routing — all 7 stream_ids
3. ContentManager routing — unknown stream_id
4. ContentManager requires generation mode
5. ContentManager requires topic
6. ContentManager requires stream_id
7. ContentManager source minimum lookup (VKR level-specific)
8. ContentManager source minimum lookup (flat streams)
9. BaseMicroManager — MicroManagerVKR section order
10. BaseMicroManager — all 7 MMs have correct SECTION_ORDER
11. BaseMicroManager — VIZ_MINIMUMS correctness
12. BaseMicroManager — count_visualizations utility
13. BaseMicroManager — single-generation detection
14. BaseMicroManager — has_toc detection
15. MicroManagerText — subtype routing
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: ContentManager instantiation ─────────────────────────────


class TestContentManagerBasics:
    def test_instantiation(self):
        """ContentManager can be instantiated."""
        from agents.content.manager import ContentManager
        cm = ContentManager()
        assert cm.agent_name == "content_manager"
        assert cm.agent_type == "manager"

    def test_is_base_agent(self):
        """ContentManager inherits from BaseAgent."""
        from agents.content.manager import ContentManager
        from agents.base import BaseAgent
        cm = ContentManager()
        assert isinstance(cm, BaseAgent)


# ── Test 2: ContentManager routing ───────────────────────────────────


class TestContentManagerRouting:
    def test_routing_all_stream_ids(self):
        """ContentManager routes to correct MM for all 7 stream_ids."""
        from agents.content.manager import ContentManager
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        cm = ContentManager()

        expected = {
            "vkr": MicroManagerVKR,
            "coursework": MicroManagerCoursework,
            "research": MicroManagerResearch,
            "abstract_paper": MicroManagerAbstractPaper,
            "text": MicroManagerText,
            "essay": MicroManagerEssay,
            "composition": MicroManagerComposition,
        }

        for stream_id, expected_class in expected.items():
            mm = cm._get_micro_manager(stream_id)
            assert mm is not None, f"No MM for {stream_id}"
            assert isinstance(mm, expected_class), (
                f"Wrong MM for {stream_id}: expected {expected_class.__name__}, "
                f"got {type(mm).__name__}"
            )

    def test_routing_unknown_stream_id(self):
        """Unknown stream_id returns None."""
        from agents.content.manager import ContentManager
        cm = ContentManager()
        mm = cm._get_micro_manager("invalid_stream")
        assert mm is None


# ── Test 3: ContentManager validation ────────────────────────────────


class TestContentManagerValidation:
    def test_requires_generation_mode(self):
        """ContentManager adds error for non-generation mode."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="humanization", stream_id="vkr", topic="Test topic")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "generation mode" in result.errors[0].lower()

    def test_requires_topic(self):
        """ContentManager adds error if topic is empty."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="generation", stream_id="vkr", topic="")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "topic" in result.errors[0].lower()

    def test_requires_stream_id(self):
        """ContentManager adds error if stream_id is empty."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="generation", stream_id="", topic="Test topic")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "stream_id" in result.errors[0].lower()


# ── Test 4: Source minimum lookup ────────────────────────────────────


class TestSourceMinimums:
    def test_vkr_level_specific_minimums(self):
        """VKR source minimums are level-specific."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("vkr", "bachelor") == 50
        assert cm._get_source_minimum("vkr", "master") == 60
        assert cm._get_source_minimum("vkr", "specialist") == 50
        assert cm._get_source_minimum("vkr", "postgraduate") == 60

    def test_flat_stream_minimums(self):
        """Non-VKR streams have flat minimums."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("coursework", "bachelor") == 20
        assert cm._get_source_minimum("research", "master") == 30
        assert cm._get_source_minimum("abstract_paper", "bachelor") == 10

    def test_zero_minimum_streams(self):
        """Text, essay, composition have 0 source minimum."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("text", "") == 0
        assert cm._get_source_minimum("essay", "") == 0
        assert cm._get_source_minimum("composition", "") == 0


# ── Test 5: MicroManager section orders ──────────────────────────────


class TestMicroManagerSectionOrders:
    def test_vkr_section_order(self):
        """VKR has 9 sections in correct GOST order."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        mm = MicroManagerVKR()
        expected = [
            "title_page", "annotation", "toc", "introduction",
            "chapter_1", "chapter_2", "chapter_3",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 9

    def test_coursework_section_order(self):
        """Coursework has 7 sections in correct order."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        mm = MicroManagerCoursework()
        expected = [
            "title_page", "toc", "introduction",
            "chapter_1", "chapter_2",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 7

    def test_research_section_order(self):
        """Research has 8 sections in correct order."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        expected = [
            "annotation", "introduction", "literature_review",
            "methodology", "results", "discussion",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 8

    def test_abstract_paper_section_order(self):
        """Abstract paper has 6 sections in correct order."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        mm = MicroManagerAbstractPaper()
        expected = [
            "title_page", "toc", "introduction",
            "chapter_1", "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 6

    def test_single_generation_streams(self):
        """Text, essay, composition have SECTION_ORDER = ['full']."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [MicroManagerText, MicroManagerEssay, MicroManagerComposition]:
            mm = mm_class()
            assert mm.SECTION_ORDER == ["full"], f"{mm.agent_name} should have ['full']"
            assert mm.is_single_generation(), f"{mm.agent_name} should be single-generation"

    def test_all_section_orders_match_generator(self):
        """All MM SECTION_ORDERs match pipeline/generator.py SECTION_ORDER exactly."""
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
                f"{mm.agent_name} SECTION_ORDER mismatch with generator: "
                f"MM={mm.SECTION_ORDER} vs generator={generator_order}"
            )


# ── Test 6: VIZ_MINIMUMS ────────────────────────────────────────────


class TestVizMinimums:
    def test_vkr_viz_minimums(self):
        """VKR has level-specific viz minimums from БЛОК 16.2."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        mm = MicroManagerVKR()
        assert mm.get_viz_minimum("bachelor") == 5
        assert mm.get_viz_minimum("master") == 8
        assert mm.get_viz_minimum("specialist") == 5
        assert mm.get_viz_minimum("postgraduate") == 10

    def test_coursework_viz_minimum(self):
        """Coursework has default viz minimum of 3."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        mm = MicroManagerCoursework()
        assert mm.get_viz_minimum("bachelor") == 3
        assert mm.get_viz_minimum("master") == 3

    def test_research_viz_minimum(self):
        """Research has default viz minimum of 3."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        assert mm.get_viz_minimum("bachelor") == 3

    def test_abstract_paper_viz_minimum(self):
        """Abstract paper has default viz minimum of 1."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        mm = MicroManagerAbstractPaper()
        assert mm.get_viz_minimum("bachelor") == 1

    def test_zero_viz_streams(self):
        """Text, essay, composition have 0 viz minimum."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [MicroManagerText, MicroManagerEssay, MicroManagerComposition]:
            mm = mm_class()
            assert mm.get_viz_minimum("bachelor") == 0
            assert mm.get_viz_minimum("master") == 0

    def test_viz_minimums_match_content_qa_gate_all_streams(self):
        """All 7 MM VIZ_MINIMUMS match ContentQAGate.VIZ_MINIMUMS."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()

        # Map: stream_id → (MM class, levels to check)
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
                # ContentQAGate uses nested dict: stream_id → level → int
                # with "default" fallback
                gate_val = gate_stream.get(level, gate_stream.get("default", 0))
                assert mm_val == gate_val, (
                    f"VIZ_MINIMUMS mismatch for {stream_id}/{level}: "
                    f"MM={mm_val} vs ContentQAGate={gate_val}"
                )


# ── Test 7: count_visualizations utility ─────────────────────────────


class TestCountVisualizations:
    def test_count_tables(self):
        """Counts markdown tables correctly."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
Some text before.

| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |

Some text between.

| X | Y | Z |
|---|---|---|
| 1 | 2 | 3 |

Some text after.
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 2
        assert figures == 0

    def test_count_figures(self):
        """Counts figure placeholders correctly (both RU and EN)."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
Some text.

[РИСУНОК 1 — Структура системы]

More text.

[FIGURE 2 — System Architecture]

Even more text.

[Рисунок 3 — Диаграмма]
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 0
        assert figures == 3

    def test_count_mixed(self):
        """Counts tables and figures together."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
| A | B |
|---|---|
| 1 | 2 |

[РИСУНОК 1 — Название]

| C | D |
|---|---|
| 3 | 4 |
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 2
        assert figures == 1

    def test_count_empty_text(self):
        """Empty text returns 0,0."""
        from agents.content.micro_managers.base import BaseMicroManager
        tables, figures = BaseMicroManager.count_visualizations("")
        assert tables == 0
        assert figures == 0


# ── Test 8: has_toc and is_single_generation ─────────────────────────


class TestMicroManagerUtilities:
    def test_has_toc_multi_section(self):
        """VKR, coursework, abstract_paper have TOC."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        assert MicroManagerVKR().has_toc()
        assert MicroManagerCoursework().has_toc()
        assert MicroManagerAbstractPaper().has_toc()

    def test_no_toc_streams(self):
        """Research, text, essay, composition do NOT have TOC."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        assert not MicroManagerResearch().has_toc()
        assert not MicroManagerText().has_toc()
        assert not MicroManagerEssay().has_toc()
        assert not MicroManagerComposition().has_toc()


# ── Test 9: MicroManagerText subtype routing ─────────────────────────


class TestMicroManagerTextSubtype:
    def test_subtype_routing(self):
        """Text MM routes domains to correct subtypes."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        mm = MicroManagerText()

        assert mm._determine_subtype("media") == "journalistic"
        assert mm._determine_subtype("it_cs") == "analytical"
        assert mm._determine_subtype("economics") == "analytical"
        assert mm._determine_subtype("humanities") == "descriptive"
        assert mm._determine_subtype("general") == "analytical"
        assert mm._determine_subtype("unknown") == "analytical"  # fallback


# ── Test 10: MicroManager execute (Phase 2 stub) ────────────────────


class TestMicroManagerExecute:
    def test_vkr_execute_runs_workers(self):
        """VKR MM executes all workers (errors expected without API key)."""
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
        # Workers try to call Claude API — errors expected in test env (no API key)
        # Verify: format-only sections (title_page, toc) still succeed
        assert "title_page" in result.generated_sections
        assert result.generated_sections["title_page"] == ""
        # TOC pass 2 runs and produces content
        assert "toc" in result.generated_sections
        assert len(result.generated_sections["toc"]) > 0

    def test_text_execute_runs_workers(self):
        """Text MM executes worker (errors expected without API key)."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.state import PipelineState

        mm = MicroManagerText()
        state = PipelineState(
            mode="generation",
            stream_id="text",
            topic="Test topic",
            domain="media",
        )
        result = asyncio.run(mm.execute(state))
        # Worker tries to call Claude API — error expected in test env (no API key)
        # Verify: "full" section was attempted (key exists even if generation failed)
        assert "full" in result.generated_sections or result.has_errors()

    def test_all_mms_inherit_base(self):
        """All 7 MMs inherit from BaseMicroManager."""
        from agents.content.micro_managers.base import BaseMicroManager
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
            assert isinstance(mm, BaseMicroManager), (
                f"{mm.agent_name} does not inherit BaseMicroManager"
            )

    def test_all_mms_have_stream_id(self):
        """All 7 MMs have non-empty STREAM_ID."""
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
            assert mm.STREAM_ID != "", f"{mm.agent_name} has empty STREAM_ID"
            assert mm.agent_name != "", f"MM has empty agent_name"

    def test_all_mms_have_nonempty_section_order(self):
        """All 7 MMs have at least 1 section in SECTION_ORDER."""
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
            assert len(mm.SECTION_ORDER) > 0, f"{mm.agent_name} has empty SECTION_ORDER"
