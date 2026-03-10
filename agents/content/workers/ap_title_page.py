from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APTitlePageWorker(BaseSectionWorker):
    """Abstract Paper Title Page worker. Format-only — handled by formatter.py."""

    section_id = "title_page"
    agent_name = "ap_title_page"
