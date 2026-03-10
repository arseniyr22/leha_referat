from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRAnnotationWorker(BaseSectionWorker):
    """
    VKR Annotation (Abstract) section worker.

    Generates annotation by calling AcademicGenerator.generate_section("annotation").
    """

    section_id = "annotation"
    agent_name = "vkr_annotation"
