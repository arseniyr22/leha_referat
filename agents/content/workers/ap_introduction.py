from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APIntroductionWorker(BaseSectionWorker):
    """Abstract Paper Introduction section worker."""

    section_id = "introduction"
    agent_name = "ap_introduction"
