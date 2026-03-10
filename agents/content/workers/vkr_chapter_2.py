from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter2Worker(BaseSectionWorker):
    """
    VKR Chapter 2 (empirical results / data analysis) worker.

    Generates chapter_2 by calling AcademicGenerator.generate_section("chapter_2").
    This is a DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_2"
    agent_name = "vkr_chapter_2"
