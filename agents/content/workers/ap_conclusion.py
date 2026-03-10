from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APConclusionWorker(BaseSectionWorker):
    """Abstract Paper Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "ap_conclusion"
