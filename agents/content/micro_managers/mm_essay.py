from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerEssay(BaseMicroManager):
    """
    Micro Manager for Essay.

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker that calls generator.generate_section("full", ...)
    for the full essay in one API call.

    Visualization minimums from BLOCK 16.2:
    - default: 0 (optional)
    """

    agent_name = "mm_essay"
    STREAM_ID = "essay"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        if section_id != "full":
            return None

        from agents.content.workers.essay_full import EssayFullWorker

        return EssayFullWorker()
