from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerAbstractPaper(BaseMicroManager):
    """
    Micro Manager for Abstract Paper (Реферат).

    6 sections (from CLAUDE.md / GAP 4.4):
    title_page → toc → introduction → chapter_1 → conclusion → references

    Visualization minimums from БЛОК 16.2:
    - default: 1 table/figure (desirable, not mandatory)

    Data-heavy sections for viz re-gen:
    - chapter_1 (main content section)
    """

    agent_name = "mm_abstract_paper"
    STREAM_ID = "abstract_paper"

    SECTION_ORDER = [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "default": 1,
    }

    DATA_HEAVY_SECTIONS = ["chapter_1"]

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        WORKERS = {
            "title_page": APTitlePageWorker,
            "toc": APTOCWorker,
            "introduction": APIntroductionWorker,
            "chapter_1": APChapter1Worker,
            "conclusion": APConclusionWorker,
            "references": APReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
