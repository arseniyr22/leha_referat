from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWChapter2Worker(BaseSectionWorker):
    """
    Coursework Chapter 2 (practical/empirical) worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_2"
    agent_name = "cw_chapter_2"
