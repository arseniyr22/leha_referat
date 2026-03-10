from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWIntroductionWorker(BaseSectionWorker):
    """Coursework Introduction section worker."""

    section_id = "introduction"
    agent_name = "cw_introduction"
