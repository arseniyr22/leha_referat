from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerCoursework(BaseMicroManager):
    """
    Micro Manager for Coursework (Курсовая работа).

    7 sections in GOST order (from CLAUDE.md / GAP 4.4):
    title_page → toc → introduction → chapter_1 → chapter_2 →
    conclusion → references

    Visualization minimums from БЛОК 16.2:
    - default: 3 tables/figures

    Data-heavy sections for viz re-gen:
    - chapter_2 (practical/empirical part)
    """

    agent_name = "mm_coursework"
    STREAM_ID = "coursework"

    SECTION_ORDER = [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "default": 3,
    }

    DATA_HEAVY_SECTIONS = ["chapter_2"]

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        WORKERS = {
            "title_page": CWTitlePageWorker,
            "toc": CWTOCWorker,
            "introduction": CWIntroductionWorker,
            "chapter_1": CWChapter1Worker,
            "chapter_2": CWChapter2Worker,
            "conclusion": CWConclusionWorker,
            "references": CWReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
