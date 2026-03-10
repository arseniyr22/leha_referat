from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerResearch(BaseMicroManager):
    """
    Micro Manager for Research (Научно-исследовательская работа).

    8 sections (from CLAUDE.md / GAP 4.4):
    annotation → introduction → literature_review → methodology →
    results → discussion → conclusion → references

    Note: research does NOT have title_page or toc in section order.
    Title page is handled separately by formatter.

    Visualization minimums from БЛОК 16.2:
    - default: 3 tables/figures

    Data-heavy sections for viz re-gen:
    - results (empirical data, statistical analysis)
    - discussion (data interpretation)
    """

    agent_name = "mm_research"
    STREAM_ID = "research"

    SECTION_ORDER = [
        "annotation",
        "introduction",
        "literature_review",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "default": 3,
    }

    DATA_HEAVY_SECTIONS = ["results", "discussion"]

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        WORKERS = {
            "annotation": ResAnnotationWorker,
            "introduction": ResIntroductionWorker,
            "literature_review": ResLiteratureReviewWorker,
            "methodology": ResMethodologyWorker,
            "results": ResResultsWorker,
            "discussion": ResDiscussionWorker,
            "conclusion": ResConclusionWorker,
            "references": ResReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
