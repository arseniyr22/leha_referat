from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextAnalyticalWorker(BaseSectionWorker):
    """
    Text stream worker — analytical subtype.

    Generates data-driven analytical text in one API call.
    Used when domain is it_cs, economics, law, psychology, or general.
    """

    section_id = "full"
    agent_name = "text_analytical"
