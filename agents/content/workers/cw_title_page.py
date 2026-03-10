from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWTitlePageWorker(BaseSectionWorker):
    """Coursework Title Page worker. Format-only — handled by formatter.py."""

    section_id = "title_page"
    agent_name = "cw_title_page"
