from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextJournalisticWorker(BaseSectionWorker):
    """
    Text stream worker — journalistic subtype.

    Generates news/feature article style text in one API call.
    Used when domain is media or journalistic.
    """

    section_id = "full"
    agent_name = "text_journalistic"
