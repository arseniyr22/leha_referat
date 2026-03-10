from __future__ import annotations

from loguru import logger

from agents.content.micro_managers.base import BaseMicroManager
from agents.state import PipelineState


class MicroManagerText(BaseMicroManager):
    """
    Micro Manager for Text.

    Single-generation stream: SECTION_ORDER = ["full"]
    Routes to subtype-specific worker based on domain.

    4 subtypes (determined by domain):
    - analytical: data-driven analysis, opinion with evidence
    - journalistic: news/feature article style
    - review: literature/product/topic review
    - descriptive: factual description, informational

    Subtype selection (from SUBTYPE_ROUTING):
    - domain "media" or "journalistic" -> journalistic
    - domain "it_cs", "economics", "law", "psychology" -> analytical
    - domain "humanities" -> descriptive
    - default -> analytical

    Visualization minimums from BLOCK 16.2:
    - default: 0 (context-dependent)
    """

    agent_name = "mm_text"
    STREAM_ID = "text"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []

    # Subtype routing: domain -> text_subtype
    SUBTYPE_ROUTING: dict[str, str] = {
        "media": "journalistic",
        "journalistic": "journalistic",
        "it_cs": "analytical",
        "economics": "analytical",
        "law": "analytical",
        "psychology": "analytical",
        "humanities": "descriptive",
        "general": "analytical",
    }

    def __init__(self) -> None:
        super().__init__()
        self._current_subtype: str = "analytical"

    def _get_worker(self, section_id: str):
        """
        Return worker for section_id.

        Uses self._current_subtype (set in execute() before super().execute())
        to select the correct text subtype worker.
        """
        if section_id != "full":
            return None

        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker

        WORKERS = {
            "analytical": TextAnalyticalWorker,
            "journalistic": TextJournalisticWorker,
            "review": TextReviewWorker,
            "descriptive": TextDescriptiveWorker,
        }
        cls = WORKERS.get(self._current_subtype, TextAnalyticalWorker)
        return cls()

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Execute text generation with subtype routing.

        Steps:
        1. Determine subtype from domain
        2. Store as self._current_subtype (read by _get_worker)
        3. Call super().execute() which iterates SECTION_ORDER and calls _get_worker
        """
        # Determine subtype BEFORE super().execute() calls _get_worker()
        self._current_subtype = self._determine_subtype(state.domain)
        logger.info(
            f"[{self.agent_name}] Text subtype determined: {self._current_subtype} "
            f"(domain={state.domain})"
        )

        # Base execute handles: _get_worker("full") -> worker.execute(state)
        state = await super().execute(state)

        return state

    def _determine_subtype(self, domain: str) -> str:
        """
        Determine text subtype from domain.

        Returns one of: analytical, journalistic, review, descriptive
        """
        return self.SUBTYPE_ROUTING.get(domain, "analytical")
