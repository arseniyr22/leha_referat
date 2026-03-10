"""
Phase 3B Tests: Multi-Section Workers for VKR, Coursework, Research, Abstract Paper.
Run: pytest tests/test_phase3b_multi_section_workers.py -v

Tests:
1. All 30 workers instantiate correctly
2. All workers have correct section_id
3. All workers have correct agent_name
4. All workers inherit from BaseSectionWorker
5. All workers have agent_type == "worker"
6. MM _get_worker() returns correct worker class for each section_id
7. MM _get_worker() returns None for unknown section_id
8. TOC workers have execute_pass_2() method
9. TOC workers build correct TOC entries
10. WORKERS dict keys match SECTION_ORDER exactly
11. Phase 3A regression: BaseMicroManager is still abstract
12. Phase 2 regression: SECTION_ORDERs still match generator.py
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: VKR Workers ─────────────────────────────────────────


class TestVKRWorkers:
    def test_all_vkr_workers_instantiate(self):
        """All 9 VKR workers instantiate without error."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        workers = [
            VKRTitlePageWorker(),
            VKRAnnotationWorker(),
            VKRTOCWorker(),
            VKRIntroductionWorker(),
            VKRChapter1Worker(),
            VKRChapter2Worker(),
            VKRChapter3Worker(),
            VKRConclusionWorker(),
            VKRReferencesWorker(),
        ]
        assert len(workers) == 9
        for w in workers:
            assert w.agent_type == "worker"

    def test_vkr_worker_section_ids(self):
        """Each VKR worker has the correct section_id."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        expected = {
            VKRTitlePageWorker: "title_page",
            VKRAnnotationWorker: "annotation",
            VKRTOCWorker: "toc",
            VKRIntroductionWorker: "introduction",
            VKRChapter1Worker: "chapter_1",
            VKRChapter2Worker: "chapter_2",
            VKRChapter3Worker: "chapter_3",
            VKRConclusionWorker: "conclusion",
            VKRReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id, f"{cls.__name__}.section_id should be '{expected_id}'"

    def test_vkr_worker_agent_names(self):
        """Each VKR worker has agent_name matching 'vkr_{section_id}'."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        workers = [
            VKRTitlePageWorker(), VKRAnnotationWorker(), VKRTOCWorker(),
            VKRIntroductionWorker(), VKRChapter1Worker(), VKRChapter2Worker(),
            VKRChapter3Worker(), VKRConclusionWorker(), VKRReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"vkr_{w.section_id}", (
                f"{w.__class__.__name__}.agent_name should be 'vkr_{w.section_id}', got '{w.agent_name}'"
            )

    def test_vkr_workers_inherit_base(self):
        """All VKR workers inherit from BaseSectionWorker."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_toc import VKRTOCWorker

        assert isinstance(VKRTitlePageWorker(), BaseSectionWorker)
        assert isinstance(VKRChapter1Worker(), BaseSectionWorker)
        assert isinstance(VKRTOCWorker(), BaseSectionWorker)


# ── Test 2: Coursework Workers ──────────────────────────────────


class TestCourseworkWorkers:
    def test_all_cw_workers_instantiate(self):
        """All 7 Coursework workers instantiate without error."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        workers = [
            CWTitlePageWorker(), CWTOCWorker(), CWIntroductionWorker(),
            CWChapter1Worker(), CWChapter2Worker(),
            CWConclusionWorker(), CWReferencesWorker(),
        ]
        assert len(workers) == 7
        for w in workers:
            assert w.agent_type == "worker"

    def test_cw_worker_section_ids(self):
        """Each CW worker has the correct section_id."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        expected = {
            CWTitlePageWorker: "title_page",
            CWTOCWorker: "toc",
            CWIntroductionWorker: "introduction",
            CWChapter1Worker: "chapter_1",
            CWChapter2Worker: "chapter_2",
            CWConclusionWorker: "conclusion",
            CWReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_cw_worker_agent_names(self):
        """Each CW worker has agent_name matching 'cw_{section_id}'."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        workers = [
            CWTitlePageWorker(), CWTOCWorker(), CWIntroductionWorker(),
            CWChapter1Worker(), CWChapter2Worker(),
            CWConclusionWorker(), CWReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"cw_{w.section_id}"


# ── Test 3: Research Workers ────────────────────────────────────


class TestResearchWorkers:
    def test_all_res_workers_instantiate(self):
        """All 8 Research workers instantiate without error."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        workers = [
            ResAnnotationWorker(), ResIntroductionWorker(),
            ResLiteratureReviewWorker(), ResMethodologyWorker(),
            ResResultsWorker(), ResDiscussionWorker(),
            ResConclusionWorker(), ResReferencesWorker(),
        ]
        assert len(workers) == 8
        for w in workers:
            assert w.agent_type == "worker"

    def test_res_worker_section_ids(self):
        """Each Research worker has the correct section_id."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        expected = {
            ResAnnotationWorker: "annotation",
            ResIntroductionWorker: "introduction",
            ResLiteratureReviewWorker: "literature_review",
            ResMethodologyWorker: "methodology",
            ResResultsWorker: "results",
            ResDiscussionWorker: "discussion",
            ResConclusionWorker: "conclusion",
            ResReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_res_worker_agent_names(self):
        """Each Research worker has agent_name matching 'res_{section_id}'."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        workers = [
            ResAnnotationWorker(), ResIntroductionWorker(),
            ResLiteratureReviewWorker(), ResMethodologyWorker(),
            ResResultsWorker(), ResDiscussionWorker(),
            ResConclusionWorker(), ResReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"res_{w.section_id}"


# ── Test 4: Abstract Paper Workers ──────────────────────────────


class TestAbstractPaperWorkers:
    def test_all_ap_workers_instantiate(self):
        """All 6 Abstract Paper workers instantiate without error."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        workers = [
            APTitlePageWorker(), APTOCWorker(), APIntroductionWorker(),
            APChapter1Worker(), APConclusionWorker(), APReferencesWorker(),
        ]
        assert len(workers) == 6
        for w in workers:
            assert w.agent_type == "worker"

    def test_ap_worker_section_ids(self):
        """Each AP worker has the correct section_id."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        expected = {
            APTitlePageWorker: "title_page",
            APTOCWorker: "toc",
            APIntroductionWorker: "introduction",
            APChapter1Worker: "chapter_1",
            APConclusionWorker: "conclusion",
            APReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_ap_worker_agent_names(self):
        """Each AP worker has agent_name matching 'ap_{section_id}'."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        workers = [
            APTitlePageWorker(), APTOCWorker(), APIntroductionWorker(),
            APChapter1Worker(), APConclusionWorker(), APReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"ap_{w.section_id}"


# ── Test 5: MM _get_worker() routing ────────────────────────────


class TestMMWorkerRouting:
    def test_vkr_get_worker_returns_correct_classes(self):
        """VKR MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        mm = MicroManagerVKR()
        expected_names = {
            "title_page": "vkr_title_page",
            "annotation": "vkr_annotation",
            "toc": "vkr_toc",
            "introduction": "vkr_introduction",
            "chapter_1": "vkr_chapter_1",
            "chapter_2": "vkr_chapter_2",
            "chapter_3": "vkr_chapter_3",
            "conclusion": "vkr_conclusion",
            "references": "vkr_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"VKR _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_cw_get_worker_returns_correct_classes(self):
        """Coursework MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework

        mm = MicroManagerCoursework()
        expected_names = {
            "title_page": "cw_title_page",
            "toc": "cw_toc",
            "introduction": "cw_introduction",
            "chapter_1": "cw_chapter_1",
            "chapter_2": "cw_chapter_2",
            "conclusion": "cw_conclusion",
            "references": "cw_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"CW _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_res_get_worker_returns_correct_classes(self):
        """Research MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch

        mm = MicroManagerResearch()
        expected_names = {
            "annotation": "res_annotation",
            "introduction": "res_introduction",
            "literature_review": "res_literature_review",
            "methodology": "res_methodology",
            "results": "res_results",
            "discussion": "res_discussion",
            "conclusion": "res_conclusion",
            "references": "res_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"RES _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_ap_get_worker_returns_correct_classes(self):
        """Abstract Paper MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        mm = MicroManagerAbstractPaper()
        expected_names = {
            "title_page": "ap_title_page",
            "toc": "ap_toc",
            "introduction": "ap_introduction",
            "chapter_1": "ap_chapter_1",
            "conclusion": "ap_conclusion",
            "references": "ap_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"AP _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_all_mms_return_none_for_unknown_section(self):
        """All 4 MMs return None for unknown section_id."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        for mm_class in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_class()
            assert mm._get_worker("nonexistent_section") is None


# ── Test 6: WORKERS dict keys match SECTION_ORDER ───────────────


class TestWorkersMatchSectionOrder:
    def test_vkr_workers_cover_all_sections(self):
        """VKR WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        mm = MicroManagerVKR()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"VKR missing worker for '{section_id}'"

    def test_cw_workers_cover_all_sections(self):
        """CW WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework

        mm = MicroManagerCoursework()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"CW missing worker for '{section_id}'"

    def test_res_workers_cover_all_sections(self):
        """Research WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch

        mm = MicroManagerResearch()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"RES missing worker for '{section_id}'"

    def test_ap_workers_cover_all_sections(self):
        """AP WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        mm = MicroManagerAbstractPaper()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"AP missing worker for '{section_id}'"


# ── Test 7: TOC workers ─────────────────────────────────────────


class TestTOCWorkers:
    def test_vkr_toc_has_execute_pass_2(self):
        """VKR TOC worker has execute_pass_2() method."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        worker = VKRTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_cw_toc_has_execute_pass_2(self):
        """CW TOC worker has execute_pass_2() method."""
        from agents.content.workers.cw_toc import CWTOCWorker
        worker = CWTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_ap_toc_has_execute_pass_2(self):
        """AP TOC worker has execute_pass_2() method."""
        from agents.content.workers.ap_toc import APTOCWorker
        worker = APTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_vkr_toc_sections_correct(self):
        """VKR TOC_SECTIONS lists correct sections."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        worker = VKRTOCWorker()
        assert "annotation" in worker.TOC_SECTIONS
        assert "introduction" in worker.TOC_SECTIONS
        assert "chapter_1" in worker.TOC_SECTIONS
        assert "chapter_2" in worker.TOC_SECTIONS
        assert "chapter_3" in worker.TOC_SECTIONS
        assert "conclusion" in worker.TOC_SECTIONS
        # Should NOT include title_page, toc, references
        assert "title_page" not in worker.TOC_SECTIONS
        assert "toc" not in worker.TOC_SECTIONS
        assert "references" not in worker.TOC_SECTIONS

    def test_cw_toc_sections_correct(self):
        """CW TOC_SECTIONS lists correct sections (no annotation, no chapter_3)."""
        from agents.content.workers.cw_toc import CWTOCWorker
        worker = CWTOCWorker()
        assert worker.TOC_SECTIONS == ["introduction", "chapter_1", "chapter_2", "conclusion"]

    def test_ap_toc_sections_correct(self):
        """AP TOC_SECTIONS lists correct sections (intro, chapter_1, conclusion)."""
        from agents.content.workers.ap_toc import APTOCWorker
        worker = APTOCWorker()
        assert worker.TOC_SECTIONS == ["introduction", "chapter_1", "conclusion"]

    def test_vkr_toc_pass_2_builds_toc(self):
        """VKR TOC pass 2 builds TOC from generated_sections."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.state import PipelineState

        worker = VKRTOCWorker()
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            language="ru",
            text="Some existing text",
            generated_sections={
                "annotation": "## Аннотация\n\nТекст аннотации.",
                "introduction": "## Введение\n\nТекст введения.",
                "chapter_1": "## Глава 1. Теоретические основы\n\nТекст главы.",
                "chapter_2": "## Глава 2. Анализ данных\n\nТекст главы.",
                "chapter_3": "## Глава 3. Рекомендации\n\nТекст главы.",
                "conclusion": "## Заключение\n\nТекст заключения.",
                "references": "## Список литературы\n\n1. Источник.",
            },
        )

        result = asyncio.run(worker.execute_pass_2(state))

        toc = result.generated_sections["toc"]
        assert "Оглавление" in toc
        assert "Аннотация" in toc
        assert "Введение" in toc
        assert "Глава 1. Теоретические основы" in toc
        assert "Глава 2. Анализ данных" in toc
        assert "Глава 3. Рекомендации" in toc
        assert "Заключение" in toc
        assert "Список литературы" in toc

    def test_toc_pass_2_uses_fallback_names(self):
        """TOC pass 2 uses SECTION_NAMES fallback when no heading found."""
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.state import PipelineState

        worker = CWTOCWorker()
        state = PipelineState(
            mode="generation",
            stream_id="coursework",
            language="en",
            text="Some text",
            generated_sections={
                "introduction": "Some text without heading.",
                "chapter_1": "Also no heading here.",
                "chapter_2": "No heading either.",
                "conclusion": "Still no heading.",
            },
        )

        result = asyncio.run(worker.execute_pass_2(state))
        toc = result.generated_sections["toc"]
        assert "Introduction" in toc
        assert "Chapter 1" in toc
        assert "Chapter 2" in toc
        assert "Conclusion" in toc
        assert "References" in toc

    def test_toc_extract_heading(self):
        """_extract_heading finds ## headings correctly."""
        from agents.content.workers.vkr_toc import VKRTOCWorker

        assert VKRTOCWorker._extract_heading("## Введение\n\nТекст") == "Введение"
        assert VKRTOCWorker._extract_heading("### Подраздел\n\nТекст") == "Подраздел"
        assert VKRTOCWorker._extract_heading("No heading here") == ""
        assert VKRTOCWorker._extract_heading("") == ""

    def test_research_has_no_toc_worker(self):
        """Research MM has no toc in SECTION_ORDER — no TOC worker needed."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        assert "toc" not in mm.SECTION_ORDER
        assert not mm.has_toc()


# ── Test 8: Format-only workers execute correctly ────────────────


class TestFormatOnlyWorkers:
    def test_title_page_worker_returns_empty(self):
        """Title page worker stores empty string (format-only)."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.state import PipelineState

        worker = VKRTitlePageWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert result.generated_sections["title_page"] == ""

    def test_toc_worker_pass_1_returns_empty(self):
        """TOC worker pass 1 (execute) stores empty string."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.state import PipelineState

        worker = VKRTOCWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert result.generated_sections["toc"] == ""


# ── Test 9: Phase 3A regression ─────────────────────────────────


class TestPhase3ARegression:
    def test_base_micro_manager_still_abstract(self):
        """BaseMicroManager still cannot be instantiated (abstract _get_worker)."""
        from agents.content.micro_managers.base import BaseMicroManager
        with pytest.raises(TypeError):
            BaseMicroManager()

    def test_section_orders_still_match_generator(self):
        """All SECTION_ORDERs still match pipeline/generator.py constants."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from pipeline.generator import SECTION_ORDER

        assert MicroManagerVKR().SECTION_ORDER == SECTION_ORDER["vkr"]
        assert MicroManagerCoursework().SECTION_ORDER == SECTION_ORDER["coursework"]
        assert MicroManagerResearch().SECTION_ORDER == SECTION_ORDER["research"]
        assert MicroManagerAbstractPaper().SECTION_ORDER == SECTION_ORDER["abstract_paper"]

    def test_viz_minimums_still_match(self):
        """VIZ_MINIMUMS cross-check with ContentQAGate still passes."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.gates.content_qa import ContentQAGate

        mm = MicroManagerVKR()
        gate = ContentQAGate()
        gate_vkr = gate.VIZ_MINIMUMS["vkr"]

        for level in ["bachelor", "master", "specialist", "postgraduate"]:
            assert mm.get_viz_minimum(level) == gate_vkr[level]

    def test_count_visualizations_still_works(self):
        """count_visualizations still counts correctly after Phase 3B changes."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        text = "| A | B |\n|---|---|\n| 1 | 2 |\n\n[РИСУНОК 1 — Test]"
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 1
        assert figures == 1

    def test_total_worker_count_is_30(self):
        """Phase 3B creates exactly 30 workers across 4 streams."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        total = 0
        for mm_class in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_class()
            for section_id in mm.SECTION_ORDER:
                worker = mm._get_worker(section_id)
                assert worker is not None, f"{mm.agent_name} missing worker for '{section_id}'"
                total += 1

        assert total == 30, f"Expected 30 workers, got {total}"
