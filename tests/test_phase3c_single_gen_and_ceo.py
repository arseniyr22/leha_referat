"""
Phase 3C Tests: Single-Generation Workers + CEO Integration.
Run: pytest tests/test_phase3c_single_gen_and_ceo.py -v

Tests:
1. All 6 single-gen workers instantiate correctly
2. All workers have section_id = "full"
3. All workers have correct agent_name
4. All workers inherit from BaseSectionWorker
5. MM routing: mm_text subtype -> correct worker class
6. MM routing: mm_essay -> EssayFullWorker
7. MM routing: mm_composition -> CompositionFullWorker
8. MM routing: all 3 MMs return None for unknown section_id
9. MicroManagerText subtype routing by domain
10. MicroManagerText._current_subtype set before worker dispatch
11. CEO._run_generation uses ContentManager (not Pipeline.run_from_params)
12. CEO._run_humanization unchanged (still uses Pipeline.run)
13. Phase 3A regression: BaseSectionWorker still works
14. Phase 3B regression: multi-section worker count = 30
15. Phase 2 regression: ContentManager routing still works for all 7 streams
"""
from __future__ import annotations

import asyncio
import inspect

import pytest


# -- Test 1: Single-Gen Worker Instantiation ---------------------------------


class TestSingleGenWorkers:
    def test_all_workers_instantiate(self):
        """All 6 single-gen workers instantiate without error."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        workers = [
            TextAnalyticalWorker(),
            TextJournalisticWorker(),
            TextReviewWorker(),
            TextDescriptiveWorker(),
            EssayFullWorker(),
            CompositionFullWorker(),
        ]
        assert len(workers) == 6
        for w in workers:
            assert w.agent_type == "worker"

    def test_all_section_ids_are_full(self):
        """All single-gen workers have section_id = 'full'."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        for cls in [
            TextAnalyticalWorker,
            TextJournalisticWorker,
            TextReviewWorker,
            TextDescriptiveWorker,
            EssayFullWorker,
            CompositionFullWorker,
        ]:
            w = cls()
            assert w.section_id == "full", f"{cls.__name__}.section_id = {w.section_id!r}, expected 'full'"

    def test_agent_names(self):
        """All single-gen workers have correct agent_name."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        expected = {
            TextAnalyticalWorker: "text_analytical",
            TextJournalisticWorker: "text_journalistic",
            TextReviewWorker: "text_review",
            TextDescriptiveWorker: "text_descriptive",
            EssayFullWorker: "essay_full",
            CompositionFullWorker: "comp_full",
        }
        for cls, name in expected.items():
            w = cls()
            assert w.agent_name == name, f"{cls.__name__}.agent_name = {w.agent_name!r}, expected {name!r}"

    def test_all_inherit_base_section_worker(self):
        """All single-gen workers inherit from BaseSectionWorker."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        for cls in [
            TextAnalyticalWorker,
            TextJournalisticWorker,
            TextReviewWorker,
            TextDescriptiveWorker,
            EssayFullWorker,
            CompositionFullWorker,
        ]:
            w = cls()
            assert isinstance(w, BaseSectionWorker), f"{cls.__name__} does not inherit BaseSectionWorker"


# -- Test 2: MM Routing ------------------------------------------------------


class TestMMRouting:
    def test_text_mm_subtype_analytical(self):
        """MicroManagerText routes analytical subtype to TextAnalyticalWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker

        mm = MicroManagerText()
        mm._current_subtype = "analytical"
        w = mm._get_worker("full")
        assert isinstance(w, TextAnalyticalWorker)

    def test_text_mm_subtype_journalistic(self):
        """MicroManagerText routes journalistic subtype to TextJournalisticWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_journalistic import TextJournalisticWorker

        mm = MicroManagerText()
        mm._current_subtype = "journalistic"
        w = mm._get_worker("full")
        assert isinstance(w, TextJournalisticWorker)

    def test_text_mm_subtype_review(self):
        """MicroManagerText routes review subtype to TextReviewWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_review import TextReviewWorker

        mm = MicroManagerText()
        mm._current_subtype = "review"
        w = mm._get_worker("full")
        assert isinstance(w, TextReviewWorker)

    def test_text_mm_subtype_descriptive(self):
        """MicroManagerText routes descriptive subtype to TextDescriptiveWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_descriptive import TextDescriptiveWorker

        mm = MicroManagerText()
        mm._current_subtype = "descriptive"
        w = mm._get_worker("full")
        assert isinstance(w, TextDescriptiveWorker)

    def test_text_mm_unknown_subtype_falls_back(self):
        """MicroManagerText falls back to TextAnalyticalWorker for unknown subtype."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker

        mm = MicroManagerText()
        mm._current_subtype = "nonexistent"
        w = mm._get_worker("full")
        assert isinstance(w, TextAnalyticalWorker)

    def test_text_mm_returns_none_for_unknown_section(self):
        """MicroManagerText returns None for unknown section_id."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("introduction") is None
        assert mm._get_worker("nonexistent") is None

    def test_essay_mm_returns_correct_worker(self):
        """MicroManagerEssay routes 'full' to EssayFullWorker."""
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.workers.essay_full import EssayFullWorker

        mm = MicroManagerEssay()
        w = mm._get_worker("full")
        assert isinstance(w, EssayFullWorker)

    def test_essay_mm_returns_none_for_unknown_section(self):
        """MicroManagerEssay returns None for unknown section_id."""
        from agents.content.micro_managers.mm_essay import MicroManagerEssay

        mm = MicroManagerEssay()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("nonexistent") is None

    def test_composition_mm_returns_correct_worker(self):
        """MicroManagerComposition routes 'full' to CompositionFullWorker."""
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.content.workers.comp_full import CompositionFullWorker

        mm = MicroManagerComposition()
        w = mm._get_worker("full")
        assert isinstance(w, CompositionFullWorker)

    def test_composition_mm_returns_none_for_unknown_section(self):
        """MicroManagerComposition returns None for unknown section_id."""
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        mm = MicroManagerComposition()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("nonexistent") is None


# -- Test 3: Text Subtype Determination --------------------------------------


class TestTextSubtypeRouting:
    def test_domain_to_subtype_mapping(self):
        """MicroManagerText._determine_subtype returns correct subtype for each domain."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        expected = {
            "media": "journalistic",
            "journalistic": "journalistic",
            "it_cs": "analytical",
            "economics": "analytical",
            "law": "analytical",
            "psychology": "analytical",
            "humanities": "descriptive",
            "general": "analytical",
        }
        for domain, subtype in expected.items():
            assert mm._determine_subtype(domain) == subtype, (
                f"domain={domain!r}: expected {subtype!r}, got {mm._determine_subtype(domain)!r}"
            )

    def test_unknown_domain_defaults_to_analytical(self):
        """Unknown domain defaults to analytical subtype."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._determine_subtype("unknown_domain") == "analytical"
        assert mm._determine_subtype("") == "analytical"

    def test_current_subtype_initialized(self):
        """MicroManagerText._current_subtype is 'analytical' on init."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._current_subtype == "analytical"

    def test_subtype_routing_all_domains_to_workers(self):
        """Full chain: domain -> subtype -> worker class (integration)."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker

        mm = MicroManagerText()

        domain_to_worker = {
            "media": TextJournalisticWorker,
            "journalistic": TextJournalisticWorker,
            "it_cs": TextAnalyticalWorker,
            "economics": TextAnalyticalWorker,
            "law": TextAnalyticalWorker,
            "psychology": TextAnalyticalWorker,
            "humanities": TextDescriptiveWorker,
            "general": TextAnalyticalWorker,
        }

        for domain, expected_cls in domain_to_worker.items():
            mm._current_subtype = mm._determine_subtype(domain)
            w = mm._get_worker("full")
            assert isinstance(w, expected_cls), (
                f"domain={domain!r}: expected {expected_cls.__name__}, got {type(w).__name__}"
            )


# -- Test 4: CEO Integration -------------------------------------------------


class TestCEOIntegration:
    def test_run_generation_uses_content_manager(self):
        """CEO._run_generation() calls ContentManager (not Pipeline.run_from_params)."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)

        # Must use ContentManager
        assert "ContentManager" in source, (
            "_run_generation must use ContentManager"
        )
        assert "content_manager" in source.lower() or "ContentManager()" in source, (
            "_run_generation must instantiate ContentManager"
        )

        # Must NOT use Pipeline.run_from_params
        assert "run_from_params" not in source, (
            "_run_generation must NOT call Pipeline.run_from_params (use ContentManager instead)"
        )

    def test_run_generation_still_calls_pipeline_run(self):
        """CEO._run_generation() still calls Pipeline.run() for Stages 1-5."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "pipe.run(" in source or "Pipeline()" in source, (
            "_run_generation must still use Pipeline.run() for Stages 1-5"
        )

    def test_run_generation_calls_content_qa(self):
        """CEO._run_generation() still calls _content_qa_check."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "_content_qa_check" in source, (
            "_run_generation must call _content_qa_check"
        )

    def test_run_generation_calls_feedback_loop(self):
        """CEO._run_generation() still calls _feedback_loop."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "_feedback_loop" in source, (
            "_run_generation must call _feedback_loop"
        )

    def test_run_humanization_unchanged(self):
        """CEO._run_humanization() still uses Pipeline.run() directly (no ContentManager)."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_humanization)
        assert "ContentManager" not in source, (
            "_run_humanization must NOT use ContentManager (humanization mode has no Phase 0)"
        )
        assert "pipe.run(" in source or "Pipeline()" in source, (
            "_run_humanization must use Pipeline.run()"
        )

    def test_ceo_feedback_loop_unchanged(self):
        """CEO._feedback_loop still has MAX_FEEDBACK_ITERATIONS = 2."""
        from agents.ceo import CEOAgent

        ceo = CEOAgent()
        assert ceo.MAX_FEEDBACK_ITERATIONS == 2

    def test_ceo_determine_feedback_route_unchanged(self):
        """CEO._determine_feedback_route still returns None for empty report."""
        from agents.ceo import CEOAgent

        ceo = CEOAgent()
        assert ceo._determine_feedback_route({}) is None
        assert ceo._determine_feedback_route(None) is None


# -- Test 5: Regression ------------------------------------------------------


class TestPhase3CRegression:
    def test_base_section_worker_still_has_execute(self):
        """BaseSectionWorker still has execute() method."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        assert hasattr(BaseSectionWorker, "execute")

    def test_multi_section_worker_count_still_30(self):
        """Phase 3B: 30 multi-section workers still exist."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        total = 0
        for mm_cls in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_cls.__new__(mm_cls)
            for sid in mm_cls.SECTION_ORDER:
                w = mm._get_worker(sid)
                if w is not None:
                    total += 1
        assert total == 30, f"Expected 30 multi-section workers, got {total}"

    def test_content_manager_routes_all_7_streams(self):
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
        for stream_id, mm_cls in expected.items():
            mm = cm._get_micro_manager(stream_id)
            assert isinstance(mm, mm_cls), (
                f"stream_id={stream_id!r}: expected {mm_cls.__name__}, got {type(mm).__name__}"
            )

    def test_total_worker_count_is_33(self):
        """Total active worker slots across all 7 MMs = 33 (30 multi + 3 single)."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        total = 0

        # Multi-section MMs
        for mm_cls in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_cls.__new__(mm_cls)
            for sid in mm_cls.SECTION_ORDER:
                w = mm._get_worker(sid)
                if w is not None:
                    total += 1

        # Single-gen MMs: each returns 1 worker for "full"
        mm_text = MicroManagerText()
        w = mm_text._get_worker("full")
        if w is not None:
            total += 1

        mm_essay = MicroManagerEssay()
        w = mm_essay._get_worker("full")
        if w is not None:
            total += 1

        mm_comp = MicroManagerComposition()
        w = mm_comp._get_worker("full")
        if w is not None:
            total += 1

        # 30 multi + 1 (text, any subtype) + 1 (essay) + 1 (composition) = 33 active slots
        assert total == 33, f"Expected 33 active worker slots, got {total}"

    def test_unique_worker_file_count_is_36(self):
        """36 unique worker files exist (30 multi-section + 6 single-gen)."""
        import pkgutil

        import agents.content.workers as workers_pkg

        worker_modules = []
        for importer, modname, ispkg in pkgutil.iter_modules(workers_pkg.__path__):
            if modname.startswith("__") or modname == "base_section_worker":
                continue
            worker_modules.append(modname)

        assert len(worker_modules) == 36, (
            f"Expected 36 worker modules (30 multi + 6 single), "
            f"got {len(worker_modules)}: {sorted(worker_modules)}"
        )

    def test_section_orders_still_match_generator(self):
        """All MM SECTION_ORDERs still match pipeline/generator.py."""
        from pipeline.generator import SECTION_ORDER as GEN_ORDER
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        assert MicroManagerVKR.SECTION_ORDER == GEN_ORDER["vkr"]
        assert MicroManagerCoursework.SECTION_ORDER == GEN_ORDER["coursework"]
        assert MicroManagerResearch.SECTION_ORDER == GEN_ORDER["research"]
        assert MicroManagerAbstractPaper.SECTION_ORDER == GEN_ORDER["abstract_paper"]
        assert MicroManagerText.SECTION_ORDER == GEN_ORDER["text"]
        assert MicroManagerEssay.SECTION_ORDER == GEN_ORDER["essay"]
        assert MicroManagerComposition.SECTION_ORDER == GEN_ORDER["composition"]
