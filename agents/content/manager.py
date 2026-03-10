from __future__ import annotations

from typing import Optional

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState
from agents.content.micro_managers.mm_vkr import MicroManagerVKR
from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
from agents.content.micro_managers.mm_research import MicroManagerResearch
from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
from agents.content.micro_managers.mm_text import MicroManagerText
from agents.content.micro_managers.mm_essay import MicroManagerEssay
from agents.content.micro_managers.mm_composition import MicroManagerComposition


class ContentManager(BaseAgent):
    """
    Content Manager — orchestrates Phase 0 content generation.

    Responsibilities:
    1. Call SourceFinder to discover/validate bibliography (Phase 0A)
    2. Route to correct MicroManager by stream_id
    3. MM generates all sections via workers (Phase 3)

    Flow:
    1. source_list = SourceFinder.find(...) — FIRST call, always
    2. state.source_list = source_list
    3. mm = _get_micro_manager(stream_id)
    4. state = await mm.execute(state) — MM handles all sections

    This agent does NOT generate text itself. It delegates to MMs,
    which in turn delegate to workers (Phase 3).

    NOT wired into CEO yet — standalone until Phase 3 integration.
    """

    agent_name = "content_manager"
    agent_type = "manager"

    # Source minimums from CLAUDE.md / config.yaml generator.source_minimums
    # Used for validation — actual source discovery delegated to SourceFinder
    SOURCE_MINIMUMS: dict[str, int] = {
        "vkr_bachelor": 50,
        "vkr_master": 60,
        "vkr_specialist": 50,
        "vkr_postgraduate": 60,
        "coursework": 20,
        "research": 30,
        "abstract_paper": 10,
        "text": 0,
        "essay": 0,
        "composition": 0,
    }

    # MicroManager routing table: stream_id → MM class
    MM_ROUTING: dict[str, type] = {
        "vkr": MicroManagerVKR,
        "coursework": MicroManagerCoursework,
        "research": MicroManagerResearch,
        "abstract_paper": MicroManagerAbstractPaper,
        "text": MicroManagerText,
        "essay": MicroManagerEssay,
        "composition": MicroManagerComposition,
    }

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Main entry point for content generation.

        Steps:
        1. Validate state has required fields for generation
        2. Call SourceFinder (Phase 0A) — discover bibliography
        3. Store source_list in state
        4. Route to correct MicroManager by stream_id
        5. Return state with generated content
        """
        if state.mode != "generation":
            state.add_error(self.agent_name, "ContentManager only works in generation mode")
            return state

        if not state.topic:
            state.add_error(self.agent_name, "topic is required for generation mode")
            return state

        if not state.stream_id:
            state.add_error(self.agent_name, "stream_id is required for generation mode")
            return state

        logger.info(
            f"[ContentManager] Starting | stream_id={state.stream_id} | "
            f"topic={state.topic[:80]}... | language={state.language} | "
            f"domain={state.domain}"
        )

        # Step 1: Source discovery (Phase 0A)
        state = await self._discover_sources(state)
        if state.has_errors():
            # Source discovery failed — check if errors are fatal
            # For streams with 0 source minimum, source failure is non-fatal
            min_sources = self._get_source_minimum(state.stream_id, state.level)
            if min_sources > 0:
                logger.error("[ContentManager] Source discovery failed for stream requiring sources")
                return state
            else:
                logger.warning("[ContentManager] Source discovery failed but stream has 0 source minimum — continuing")

        # Step 2: Route to MicroManager
        mm = self._get_micro_manager(state.stream_id)
        if mm is None:
            state.add_error(self.agent_name, f"No MicroManager found for stream_id={state.stream_id}")
            return state

        logger.info(f"[ContentManager] Routing to {mm.agent_name}")

        # Step 3: Execute MicroManager
        state = await mm.execute(state)

        # Step 4: Validate source count meets minimum
        if state.source_list is not None:
            source_count = len(state.source_list.sources) if hasattr(state.source_list, 'sources') else 0
            min_required = self._get_source_minimum(state.stream_id, state.level)
            if source_count < min_required:
                state.add_error(
                    self.agent_name,
                    f"Source count {source_count} below minimum {min_required} "
                    f"for {state.stream_id}/{state.level}"
                )

        logger.info(
            f"[ContentManager] Complete | sections={len(state.generated_sections)} | "
            f"errors={len(state.errors)}"
        )

        return state

    async def _discover_sources(self, state: PipelineState) -> PipelineState:
        """
        Call SourceFinder (Phase 0A) to discover bibliography.

        Uses existing pipeline/source_finder.py — wrap, not rewrite.
        Stores result in state.source_list.
        """
        from pipeline.source_finder import SourceFinder
        from pipeline import load_config

        min_sources = self._get_source_minimum(state.stream_id, state.level)

        # Streams with 0 source minimum skip source discovery
        if min_sources == 0:
            logger.info(f"[ContentManager] Skipping source discovery — {state.stream_id} has 0 minimum")
            return state

        try:
            config = load_config()
            finder = SourceFinder(config)
            source_list = finder.find(
                topic=state.topic,
                domain=state.domain,
                language=state.language,
                stream_id=state.stream_id,
                min_sources=min_sources,
                additional_sources=[],  # Phase 3: user-provided sources from CLI args
            )
            state.source_list = source_list
            logger.info(
                f"[ContentManager] Sources discovered: {len(source_list.sources)} total | "
                f"minimum required: {min_sources}"
            )
        except Exception as e:
            state.add_error(self.agent_name, f"Source discovery failed: {e}")
            logger.error(f"[ContentManager] Source discovery error: {e}")

        return state

    def _get_micro_manager(self, stream_id: str) -> Optional[BaseAgent]:
        """Get MicroManager instance for stream_id."""
        mm_class = self.MM_ROUTING.get(stream_id)
        if mm_class is None:
            return None
        return mm_class()

    def _get_source_minimum(self, stream_id: str, level: str) -> int:
        """
        Get minimum source count for stream_id + level.

        VKR uses level-specific minimums (vkr_bachelor, vkr_master).
        Other streams have flat minimums.
        """
        if stream_id == "vkr":
            key = f"vkr_{level}" if level else "vkr_bachelor"
            return self.SOURCE_MINIMUMS.get(key, 50)
        return self.SOURCE_MINIMUMS.get(stream_id, 0)
