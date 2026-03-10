from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRReferencesWorker(BaseSectionWorker):
    """
    VKR References (Bibliography) section worker.

    AcademicGenerator.generate_section("references") formats the source_list
    from Phase 0A into GOST-compliant bibliography. If no source_list, falls
    back to LLM generation.
    """

    section_id = "references"
    agent_name = "vkr_references"
