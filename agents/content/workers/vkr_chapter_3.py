from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter3Worker(BaseSectionWorker):
    """
    VKR Chapter 3 (practical application / recommendations) worker.

    Generates chapter_3 by calling AcademicGenerator.generate_section("chapter_3").
    This is a DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_3"
    agent_name = "vkr_chapter_3"
