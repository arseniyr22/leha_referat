from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResDiscussionWorker(BaseSectionWorker):
    """
    Research Discussion section worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "discussion"
    agent_name = "res_discussion"
