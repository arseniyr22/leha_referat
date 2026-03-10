from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRConclusionWorker(BaseSectionWorker):
    """
    VKR Conclusion section worker.

    Generates conclusion by calling AcademicGenerator.generate_section("conclusion").
    """

    section_id = "conclusion"
    agent_name = "vkr_conclusion"
