from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextDescriptiveWorker(BaseSectionWorker):
    """
    Text stream worker — descriptive subtype.

    Generates factual descriptive/informational text in one API call.
    Used when domain is humanities.
    """

    section_id = "full"
    agent_name = "text_descriptive"
