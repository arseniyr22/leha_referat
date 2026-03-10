from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResConclusionWorker(BaseSectionWorker):
    """Research Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "res_conclusion"
