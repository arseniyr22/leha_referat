from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResResultsWorker(BaseSectionWorker):
    """
    Research Results section worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "results"
    agent_name = "res_results"
