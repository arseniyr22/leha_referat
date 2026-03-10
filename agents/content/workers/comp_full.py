from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CompositionFullWorker(BaseSectionWorker):
    """
    Composition stream worker.

    Generates the full composition in one API call.
    Register: general (from REGISTER_MAP).
    """

    section_id = "full"
    agent_name = "comp_full"
