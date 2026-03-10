from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResIntroductionWorker(BaseSectionWorker):
    """Research Introduction section worker."""

    section_id = "introduction"
    agent_name = "res_introduction"
