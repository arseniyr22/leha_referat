from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResLiteratureReviewWorker(BaseSectionWorker):
    """Research Literature Review section worker."""

    section_id = "literature_review"
    agent_name = "res_literature_review"
