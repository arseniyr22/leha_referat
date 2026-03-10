from __future__ import annotations

import re
from typing import Optional

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class BaseSectionWorker(BaseAgent):
    """
    Base class for all content generation workers.

    Each worker wraps AcademicGenerator.generate_section() for one section_id.
    Workers are thin: they call generator, store result, count visualizations.

    Subclasses MUST set:
    - section_id: str — which section this worker generates
    - agent_name: str — unique name for logging/cost tracking

    Lifecycle (called by MicroManager):
    1. MM instantiates worker
    2. MM calls await worker.execute(state)
    3. Worker calls generator.generate_section(self.section_id, ...)
    4. Worker stores text in state.generated_sections[section_id]
    5. Worker updates state.last_section_text for next section's bridge
    6. Worker counts visualizations and updates state.visualization_count
    7. Worker appends section text to state.text

    Special workers (override execute()):
    - TOC workers: execute() returns placeholder; execute_pass_2() updates with real TOC
    - Single-gen workers (text/essay/composition): call generator.generate() instead
    """

    agent_type = "worker"

    # Subclasses MUST override
    section_id: str = ""

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Generate this section and store in state.

        Standard flow for multi-section workers.
        Single-generation workers override this entirely.
        """
        if not self.section_id:
            state.add_error(self.agent_name, "section_id is not set")
            return state

        # Format-only sections (title_page, toc): skip generation
        if self.section_id in ("title_page", "toc"):
            logger.info(f"[{self.agent_name}] Format-only section '{self.section_id}' — skipping generation")
            state.generated_sections[self.section_id] = ""
            return state

        logger.info(f"[{self.agent_name}] Generating section: {self.section_id}")

        try:
            section_text = self._call_generator(state)
        except Exception as e:
            state.add_error(self.agent_name, f"Generation failed for {self.section_id}: {e}")
            logger.error(f"[{self.agent_name}] Generation error: {e}")
            return state

        # Store in state
        state.generated_sections[self.section_id] = section_text
        state.last_section_text = section_text

        # Count visualizations (uses same logic as BaseMicroManager.count_visualizations)
        tables, figures = self._count_visualizations(section_text)
        state.visualization_count["tables"] = state.visualization_count.get("tables", 0) + tables
        state.visualization_count["figures"] = state.visualization_count.get("figures", 0) + figures

        # Append to running document text
        if section_text:
            if state.text:
                state.text += "\n\n" + section_text
            else:
                state.text = section_text

        word_count = len(section_text.split()) if section_text else 0
        logger.info(
            f"[{self.agent_name}] Generated {word_count} words | "
            f"viz: +{tables}t +{figures}f | "
            f"total viz: {state.visualization_count}"
        )

        return state

    def _call_generator(self, state: PipelineState) -> str:
        """
        Call AcademicGenerator.generate_section() for this section.

        Uses state fields to build GenerationParams and passes source_list.
        """
        from pipeline.generator import AcademicGenerator, GenerationParams
        from pipeline import load_config

        config = load_config()
        generator = AcademicGenerator(config)

        params = GenerationParams(
            stream_id=state.stream_id,
            topic=state.topic,
            language=state.language,
            domain=state.domain,
            level=state.level,
            research_type=state.research_type,
            university=state.university,
        )

        # Get last ~500 chars for logical bridge between sections
        previously_generated = ""
        if state.last_section_text:
            previously_generated = state.last_section_text[-500:]

        return generator.generate_section(
            section_id=self.section_id,
            params=params,
            source_list=state.source_list,
            previously_generated=previously_generated,
        )

    @staticmethod
    def _count_visualizations(text: str) -> tuple[int, int]:
        """
        Count tables and figure placeholders in generated text.

        Duplicates BaseMicroManager.count_visualizations() logic to avoid
        circular cross-import between workers and micro_managers packages.

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
