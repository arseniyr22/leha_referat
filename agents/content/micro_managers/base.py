from __future__ import annotations

import re
from abc import abstractmethod  # Used in Phase 3 for _get_worker(); kept from Phase 2

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class BaseMicroManager(BaseAgent):
    """
    Abstract base for all content generation Micro Managers.

    Every MM defines:
    - SECTION_ORDER: list[str] — section generation sequence
    - VIZ_MINIMUMS: dict[str, int] — min visualizations by level (БЛОК 16.2)
    - DATA_HEAVY_SECTIONS: list[str] — sections to re-gen if viz deficit
    - STREAM_ID: str — which stream this MM handles

    Phase 3: execute() iterates SECTION_ORDER, calls worker per section,
    tracks viz count, re-gens data-heavy sections if needed, handles TOC 2-pass.
    """

    agent_type = "micro_manager"

    # Subclasses MUST override these
    STREAM_ID: str = ""
    SECTION_ORDER: list[str] = []
    VIZ_MINIMUMS: dict[str, int] = {}
    DATA_HEAVY_SECTIONS: list[str] = []

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Orchestrate section-by-section generation.

        Steps:
        1. Validate SECTION_ORDER is defined
        2. Initialize viz tracking
        3. For each section_id in SECTION_ORDER:
           a. Get worker for section_id via _get_worker()
           b. state = await worker.execute(state)
        4. TOC 2-pass: if has_toc() and toc worker has execute_pass_2, call it
        5. Check viz deficit → re-gen DATA_HEAVY_SECTIONS if needed (max 1 retry)
        6. Store final viz count in state
        """
        if not self.SECTION_ORDER:
            state.add_error(self.agent_name, "SECTION_ORDER is empty — cannot generate")
            return state

        logger.info(
            f"[{self.agent_name}] Starting | stream_id={self.STREAM_ID} | "
            f"sections={len(self.SECTION_ORDER)} | "
            f"order={self.SECTION_ORDER}"
        )

        # Initialize viz tracking
        state.visualization_count = {"tables": 0, "figures": 0}

        # Track TOC worker for 2-pass
        toc_worker = None

        # Step 3: Generate each section via worker
        for i, section_id in enumerate(self.SECTION_ORDER):
            worker = self._get_worker(section_id)

            if worker is None:
                logger.warning(
                    f"[{self.agent_name}] No worker for section '{section_id}' — skipping"
                )
                continue

            logger.info(
                f"[{self.agent_name}] Section {i + 1}/{len(self.SECTION_ORDER)}: "
                f"{section_id} → {worker.agent_name}"
            )

            state = await worker.execute(state)

            if state.has_errors():
                # Check if error is from this section specifically
                last_error = state.errors[-1] if state.errors else ""
                if f"Generation failed for {section_id}" in last_error:
                    logger.error(
                        f"[{self.agent_name}] Section '{section_id}' failed — "
                        f"continuing with remaining sections"
                    )
                    # Clear the error to allow pipeline to continue
                    # Individual section failure is non-fatal
                    continue

            # Remember TOC worker for pass 2
            if section_id == "toc":
                toc_worker = worker

        # Step 4: TOC 2-pass — update TOC with actual section titles
        if toc_worker is not None and hasattr(toc_worker, 'execute_pass_2'):
            logger.info(f"[{self.agent_name}] TOC Pass 2: updating with actual section titles")
            state = await toc_worker.execute_pass_2(state)

        # Step 5: Check viz deficit and re-gen data-heavy sections if needed
        deficit = self.check_viz_deficit(state)
        if deficit > 0 and self.DATA_HEAVY_SECTIONS:
            logger.warning(
                f"[{self.agent_name}] Viz deficit: {deficit} below minimum. "
                f"Re-generating data-heavy sections: {self.DATA_HEAVY_SECTIONS}"
            )
            state = await self._regen_data_heavy_sections(state, deficit)

        # Log completion
        total_viz = state.visualization_count.get("tables", 0) + state.visualization_count.get("figures", 0)
        viz_min = self.get_viz_minimum(state.level)
        logger.info(
            f"[{self.agent_name}] Complete | "
            f"sections_generated={len(state.generated_sections)} | "
            f"total_viz={total_viz} (minimum={viz_min}) | "
            f"total_words={state.word_count()}"
        )

        return state

    @abstractmethod
    def _get_worker(self, section_id: str):
        """
        Return the worker instance for a given section_id.

        Each concrete MM overrides this to return its stream-specific workers.
        Returns None if no worker exists for the section_id.

        Example (MicroManagerVKR):
            def _get_worker(self, section_id):
                from agents.content.workers.vkr_introduction import VKRIntroductionWorker
                WORKERS = {
                    "introduction": VKRIntroductionWorker,
                    "chapter_1": VKRChapter1Worker,
                    ...
                }
                cls = WORKERS.get(section_id)
                return cls() if cls else None
        """
        ...

    async def _regen_data_heavy_sections(self, state: PipelineState, deficit: int) -> PipelineState:
        """
        Re-generate data-heavy sections to meet visualization minimum.

        Called when total viz count < minimum after initial generation.
        Max 1 re-attempt per data-heavy section.
        """
        for section_id in self.DATA_HEAVY_SECTIONS:
            if deficit <= 0:
                break

            worker = self._get_worker(section_id)
            if worker is None:
                continue

            logger.info(
                f"[{self.agent_name}] Re-generating '{section_id}' for viz deficit "
                f"(current deficit: {deficit})"
            )

            # Save current viz count before re-gen
            old_tables = state.visualization_count.get("tables", 0)
            old_figures = state.visualization_count.get("figures", 0)

            # Remove old section text from state.text before re-gen
            old_section_text = state.generated_sections.get(section_id, "")
            if old_section_text and old_section_text in state.text:
                state.text = state.text.replace(old_section_text, "", 1)

            # Subtract old viz counts for this section
            old_t, old_f = self.count_visualizations(old_section_text)
            state.visualization_count["tables"] = max(0, state.visualization_count.get("tables", 0) - old_t)
            state.visualization_count["figures"] = max(0, state.visualization_count.get("figures", 0) - old_f)

            # Re-generate
            state = await worker.execute(state)

            # Recalculate deficit
            deficit = self.check_viz_deficit(state)

        return state

    def get_viz_minimum(self, level: str) -> int:
        """
        Get visualization minimum from VIZ_MINIMUMS for given level.

        Falls back to 'default' key if level not found.
        Returns 0 if no minimum defined.
        """
        return self.VIZ_MINIMUMS.get(level, self.VIZ_MINIMUMS.get("default", 0))

    def has_toc(self) -> bool:
        """Check if this stream has a TOC section (requires 2-pass)."""
        return "toc" in self.SECTION_ORDER

    def is_single_generation(self) -> bool:
        """Check if this stream uses single-call generation (SECTION_ORDER = ['full'])."""
        return self.SECTION_ORDER == ["full"]

    @staticmethod
    def count_visualizations(text: str) -> tuple[int, int]:
        """
        Count tables and figure placeholders in generated text.

        Tables: markdown table format (lines starting with |)
        Figures: [РИСУНОК N — ...] or [FIGURE N — ...] placeholders

        Returns:
            (table_count, figure_count)
        """
        # Count tables: groups of consecutive lines starting with |
        # Each group = 1 table
        table_count = 0
        in_table = False
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("|") and "|" in stripped[1:]:
                if not in_table:
                    table_count += 1
                    in_table = True
            else:
                in_table = False

        # Count figures: [РИСУНОК N — ...] or [FIGURE N — ...]
        figure_pattern = r'\[(?:РИСУНОК|FIGURE|Рисунок|Figure)\s+\d+'
        figure_count = len(re.findall(figure_pattern, text))

        return table_count, figure_count

    def check_viz_deficit(self, state: PipelineState) -> int:
        """
        Check if visualization count is below minimum.

        Returns deficit (positive number) or 0 if minimum met.
        """
        viz = state.visualization_count
        total = viz.get("tables", 0) + viz.get("figures", 0)
        minimum = self.get_viz_minimum(state.level)
        deficit = minimum - total
        return max(0, deficit)
