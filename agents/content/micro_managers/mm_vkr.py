from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerVKR(BaseMicroManager):
    """
    Micro Manager for VKR (Выпускная квалификационная работа).

    9 sections in GOST order (from CLAUDE.md / GAP 4.4):
    title_page → annotation → toc → introduction → chapter_1 →
    chapter_2 → chapter_3 → conclusion → references

    Visualization minimums from БЛОК 16.2:
    - bachelor: 5 tables/figures
    - master: 8 tables/figures
    - specialist: 5 tables/figures
    - postgraduate: 10 tables/figures

    Data-heavy sections for viz re-gen:
    - chapter_2 (empirical results, data analysis)
    - chapter_3 (practical application, recommendations)
    """

    agent_name = "mm_vkr"
    STREAM_ID = "vkr"

    SECTION_ORDER = [
        "title_page",
        "annotation",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "chapter_3",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "bachelor": 5,
        "master": 8,
        "specialist": 5,
        "postgraduate": 10,
    }

    DATA_HEAVY_SECTIONS = ["chapter_2", "chapter_3"]

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        WORKERS = {
            "title_page": VKRTitlePageWorker,
            "annotation": VKRAnnotationWorker,
            "toc": VKRTOCWorker,
            "introduction": VKRIntroductionWorker,
            "chapter_1": VKRChapter1Worker,
            "chapter_2": VKRChapter2Worker,
            "chapter_3": VKRChapter3Worker,
            "conclusion": VKRConclusionWorker,
            "references": VKRReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
