from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APChapter1Worker(BaseSectionWorker):
    """
    Abstract Paper Chapter 1 (main content) worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_1"
    agent_name = "ap_chapter_1"
