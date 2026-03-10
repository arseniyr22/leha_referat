from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRTitlePageWorker(BaseSectionWorker):
    """
    VKR Title Page worker.

    Format-only section: BaseSectionWorker.execute() returns empty string
    for section_id="title_page". Actual title page is built by formatter.py.
    """

    section_id = "title_page"
    agent_name = "vkr_title_page"
