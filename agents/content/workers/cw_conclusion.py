from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWConclusionWorker(BaseSectionWorker):
    """Coursework Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "cw_conclusion"
