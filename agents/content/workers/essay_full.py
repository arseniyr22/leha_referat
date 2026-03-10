from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class EssayFullWorker(BaseSectionWorker):
    """
    Essay stream worker.

    Generates the full essay in one API call.
    Register: academic-essay (from REGISTER_MAP).
    """

    section_id = "full"
    agent_name = "essay_full"
