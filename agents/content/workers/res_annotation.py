from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResAnnotationWorker(BaseSectionWorker):
    """Research Annotation (Abstract) section worker."""

    section_id = "annotation"
    agent_name = "res_annotation"
