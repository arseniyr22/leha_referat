from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerComposition(BaseMicroManager):
    """
    Micro Manager for Composition.

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker that calls generator.generate_section("full", ...)
    for the full composition in one API call.

    Visualization minimums from BLOCK 16.2:
    - default: 0 (none required)
    """

    agent_name = "mm_composition"
    STREAM_ID = "composition"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        if section_id != "full":
            return None

        from agents.content.workers.comp_full import CompositionFullWorker

        return CompositionFullWorker()
