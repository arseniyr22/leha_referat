from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter1Worker(BaseSectionWorker):
    """
    VKR Chapter 1 (theoretical framework / literature review) worker.

    Generates chapter_1 by calling AcademicGenerator.generate_section("chapter_1").
    """

    section_id = "chapter_1"
    agent_name = "vkr_chapter_1"
