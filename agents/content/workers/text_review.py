from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextReviewWorker(BaseSectionWorker):
    """
    Text stream worker — review subtype.

    Generates literature/product/topic review text in one API call.
    Used when explicitly requested (not auto-routed by domain).
    """

    section_id = "full"
    agent_name = "text_review"
