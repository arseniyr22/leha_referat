from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRIntroductionWorker(BaseSectionWorker):
    """
    VKR Introduction section worker.

    Generates introduction by calling AcademicGenerator.generate_section("introduction").
    """

    section_id = "introduction"
    agent_name = "vkr_introduction"
