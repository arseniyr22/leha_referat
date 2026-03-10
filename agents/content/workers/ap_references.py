from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APReferencesWorker(BaseSectionWorker):
    """Abstract Paper References worker. Formats GOST bibliography from Phase 0A sources."""

    section_id = "references"
    agent_name = "ap_references"
