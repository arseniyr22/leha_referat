# Phase 3A: BaseSectionWorker + MicroManager Integration + HandoffGate

## Overview

Phase 3A upgrades Phase 2 stubs to working orchestration and creates the worker infrastructure.

**What this prompt does:**
1. Creates `BaseSectionWorker` — template class all 36 workers inherit from
2. Creates `workers/__init__.py` — package init
3. **Upgrades** `BaseMicroManager.execute()` from Phase 2 stub → real worker orchestration with viz tracking, TOC 2-pass, and data-heavy section re-gen
4. Creates `HandoffGate` — validates Phase 0 output and packages metadata for humanization
5. Creates `agents/prompts/handoff_gate.md` — prompt template
6. **Adds** `last_section_text` field to `PipelineState`
7. Creates comprehensive tests

**Principle**: wrap, not rewrite. Workers call existing `pipeline/generator.py` methods. Workers do NOT assemble megaprompts — `generator.py` does that internally.

**Key architectural insight**: `AcademicGenerator` in `pipeline/generator.py` already has:
- `generate(params)` → full text generation (for text/essay/composition)
- `_generate_sectional(params, source_list, sections)` → section-by-section (for VKR/coursework/research/abstract_paper)

Workers are thin wrappers that call `AcademicGenerator` methods and store results in `PipelineState`.

BUT: the existing `AcademicGenerator.generate()` does EVERYTHING internally (source discovery + all sections + structural check). Workers need to call it at a LOWER level — individual section generation. The key method is `_generate_sectional()` which iterates sections internally.

**Decision**: Workers call `AcademicGenerator` at the PUBLIC `generate()` level for single-generation streams (text/essay/composition). For multi-section streams, workers call a NEW public method `generate_section()` that we expose on `AcademicGenerator`. This method wraps the internal `_build_system_prompt()` + `_build_section_prompt()` + API call logic that currently lives inside `_generate_sectional()`.

**IMPORTANT**: This means we need to ADD one method to `pipeline/generator.py`: `generate_section(section_id, params, source_list, previously_generated)`. This is the ONLY modification to existing pipeline code.

---

## Files to Create (5 new files)

```
agents/content/workers/__init__.py                # Package init
agents/content/workers/base_section_worker.py     # BaseSectionWorker template class
agents/gates/handoff_gate.py                      # HandoffGate
agents/prompts/handoff_gate.md                    # HandoffGate prompt
tests/test_phase3a_base_worker.py                 # Tests
```

## Files to Modify (3 existing files)

```
agents/content/micro_managers/base.py             # Upgrade execute() from stub → real orchestration
agents/state.py                                   # Add last_section_text field
pipeline/generator.py                             # Add public generate_section() method
```

---

## File 1: `pipeline/generator.py` — ADD `generate_section()` method

**Add this public method to the `AcademicGenerator` class**, right after the existing `generate()` method (after line ~270 in current file). Do NOT modify any existing methods.

```python
    def generate_section(
        self,
        section_id: str,
        params: GenerationParams,
        source_list: Optional[SourceList] = None,
        previously_generated: str = "",
    ) -> str:
        """
        Generate a single section of academic text.

        Public API for Phase 3 workers. Wraps the internal section generation
        logic that was previously only called from _generate_sectional().

        Args:
            section_id: Section to generate (e.g., "introduction", "chapter_1")
            params: Generation parameters (topic, domain, language, etc.)
            source_list: GOST bibliography from Phase 0A (injected into megaprompt)
            previously_generated: Last ~500 chars of previous section (for logical bridge)

        Returns:
            Generated section text as string.

        Special cases:
            - "title_page", "toc": Returns empty string (format-only, handled by formatter)
            - "references": Returns formatted source list if source_list provided,
              otherwise generates via LLM
            - "full": Calls _generate_full() for single-generation streams
        """
        import anthropic

        # Format-only sections: return empty (handled by formatter.py / TOC worker)
        if section_id in ("title_page", "toc"):
            logger.debug(f"AcademicGenerator.generate_section: '{section_id}' is format-only, returning empty")
            return ""

        # Full generation (text/essay/composition)
        if section_id == "full":
            return self._generate_full(params, source_list)

        # References section: format source list directly
        if section_id == "references":
            if source_list and source_list.sources:
                section_names = SECTION_NAMES_RU if params.language == "ru" else SECTION_NAMES_EN
                section_header = section_names.get("references", "References")
                return f"## {section_header}\n\n{source_list.as_numbered_list()}"
            # Fall through to LLM generation if no source list

        # Standard section generation via LLM
        system_prompt = self._build_system_prompt(params, source_list)
        target_words = params.word_count or self._get_target_words(section_id, params)
        user_prompt = self._build_section_prompt(
            section_id, params, previously_generated, target_words
        )

        logger.info(
            f"AcademicGenerator.generate_section: '{section_id}' (~{target_words} words)"
        )

        client = anthropic.Anthropic()
        temperature = 0.1 if section_id == "references" else self.temperature

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text.strip()
```

**Verification**: After adding, `AcademicGenerator` has these public methods:
- `generate(params)` — existing, unchanged
- `generate_section(section_id, params, source_list, previously_generated)` — NEW

---

## File 2: `agents/state.py` — ADD `last_section_text` field

Add this field to `PipelineState` in the "Phase 0 output" section (after line 70, after `visualization_count`):

```python
    last_section_text: str = ""              # Last generated section text (for logical bridge between sections)
```

The full "Phase 0 output" section becomes:

```python
    # ── Phase 0 output ─────────────────────────────────────────────
    source_list: Any = None          # SourceList from source_finder (Phase 0A)
    generated_sections: dict = field(default_factory=dict)  # section_id → text (Phase 0B)
    visualization_count: dict = field(default_factory=lambda: {"tables": 0, "figures": 0})
    last_section_text: str = ""              # Last generated section text (for logical bridge between sections)
```

**Do NOT modify any other fields or methods in state.py.**

---

## File 3: `agents/content/workers/__init__.py`

```python
"""
Content generation workers package.

Each worker generates one section of academic text by calling
AcademicGenerator.generate_section() from pipeline/generator.py.

Worker hierarchy:
- BaseSectionWorker (base class)
  - Multi-section workers: vkr_*, cw_*, res_*, ap_* (Prompt 3B)
  - Single-generation workers: text_*, essay_full, comp_full (Prompt 3C)

Workers are instantiated by MicroManagers and called in SECTION_ORDER sequence.
"""
```

---

## File 4: `agents/content/workers/base_section_worker.py`

```python
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
```

---

## File 5: `agents/content/micro_managers/base.py` — FULL REPLACEMENT

Replace the entire file. This upgrades the Phase 2 stub `execute()` to real worker orchestration.

**Changes from Phase 2:**
1. `execute()` now iterates SECTION_ORDER and calls workers
2. NEW: `_get_worker(section_id)` returns the correct worker instance
3. NEW: `_regen_data_heavy_section()` for viz deficit recovery
4. NEW: TOC 2-pass logic in `execute()`
5. `count_visualizations()`, `get_viz_minimum()`, `has_toc()`, `is_single_generation()`, `check_viz_deficit()` — PRESERVED unchanged
6. Phase 2 `abstractmethod` import comment — PRESERVED

```python
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
```

**CRITICAL**: After this change, `_get_worker()` is abstract. All 7 concrete MMs (mm_vkr.py, mm_coursework.py, etc.) MUST implement `_get_worker()`. But concrete workers don't exist yet — they come in Prompt 3B and 3C. Therefore:

**Each concrete MM must be updated to implement `_get_worker()` that returns `None` for now.** This preserves testability while making the abstract contract explicit.

---

## File 6: Update ALL 7 Concrete MicroManagers

**For each of the 7 MMs**, add the `_get_worker()` method. The pattern is identical for all — they return `None` for now (workers come in Prompt 3B/3C).

### `agents/content/micro_managers/mm_vkr.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """
        Return worker for section_id.

        Phase 3A: returns None (workers created in Prompt 3B).
        Phase 3B will add imports and WORKERS dict mapping section_id → worker class.
        """
        # Phase 3B will populate this:
        # WORKERS = {
        #     "title_page": VKRTitlePageWorker,
        #     "annotation": VKRAnnotationWorker,
        #     "toc": VKRTOCWorker,
        #     "introduction": VKRIntroductionWorker,
        #     "chapter_1": VKRChapter1Worker,
        #     "chapter_2": VKRChapter2Worker,
        #     "chapter_3": VKRChapter3Worker,
        #     "conclusion": VKRConclusionWorker,
        #     "references": VKRReferencesWorker,
        # }
        # cls = WORKERS.get(section_id)
        # return cls() if cls else None
        return None
```

### `agents/content/micro_managers/mm_coursework.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3B."""
        return None
```

### `agents/content/micro_managers/mm_research.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3B."""
        return None
```

### `agents/content/micro_managers/mm_abstract_paper.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3B."""
        return None
```

### `agents/content/micro_managers/mm_text.py` — add after `SUBTYPE_ROUTING`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None
```

Also update `mm_text.py`'s `execute()` to call `super().execute()` which now does real orchestration:

The existing `execute()` in mm_text.py already calls `super().execute()`. No change needed — the base class upgrade propagates automatically.

### `agents/content/micro_managers/mm_essay.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None
```

### `agents/content/micro_managers/mm_composition.py` — add after `DATA_HEAVY_SECTIONS`:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None
```

---

## File 7: `agents/gates/handoff_gate.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


@dataclass
class HandoffMetadata:
    """
    Metadata package passed from Phase 0 (generation) to humanization pipeline.

    Created by HandoffGate after Phase 0 content generation is complete.
    Contains all information needed by HumanizerManager (Phase 4) to process the text.
    """
    text: str                          # Full Phase 0 output (all sections concatenated)
    source_count: int = 0              # Number of sources from Phase 0A
    viz_count_tables: int = 0          # Table count from Phase 0B
    viz_count_figures: int = 0         # Figure count from Phase 0B
    domain: str = "general"            # Domain for HM stages
    register: str = "general"          # Register for HM stages
    language: str = "en"               # Language for AC-rules gating
    stream_id: str = ""                # Stream type for context
    level: str = ""                    # Academic level for context
    sections_generated: int = 0        # Number of sections generated
    structural_violations: list[str] = field(default_factory=list)  # Any QA violations found


class HandoffGate(BaseAgent):
    """
    Handoff Gate — validates Phase 0 output and packages for humanization.

    Sits between Phase 0 (content generation) and Phase 4 (humanization).
    Responsibilities:
    1. Validate Phase 0 structural requirements:
       - Announcement openers = 0
       - Triplet instances = 0
       - Visualization count >= stream minimum (БЛОК 16.2)
    2. Package HandoffMetadata for HumanizerManager
    3. Map domain → pipeline domain, stream_id → register
    4. Return state ready for humanization pipeline entry

    This gate REPORTS violations but does NOT block. ContentQAGate (Phase 1)
    handles blocking logic. HandoffGate is a metadata packager that also validates.
    """

    agent_name = "handoff_gate"
    agent_type = "gate"

    # Domain → pipeline code mapping (from generator.py DOMAIN_MAP)
    DOMAIN_MAP: dict[str, str] = {
        "it_cs": "cs",
        "law": "general",
        "psychology": "social-science",
        "economics": "economics",
        "humanities": "humanities",
        "media": "journalistic",
        "general": "general",
    }

    # stream_id → register mapping (from generator.py REGISTER_MAP)
    REGISTER_MAP: dict[str, str] = {
        "vkr": "academic",
        "coursework": "academic",
        "research": "academic",
        "abstract_paper": "academic",
        "text": "journalistic",
        "essay": "academic-essay",
        "composition": "general",
    }

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Validate Phase 0 output and package metadata for humanization.

        Steps:
        1. Validate: state must have generated text
        2. Run structural validation (announcement openers, triplets)
        3. Check visualization count vs. minimum
        4. Build HandoffMetadata
        5. Set state.register and state.domain for downstream stages
        6. Return state ready for humanization
        """
        if not state.text:
            state.add_error(self.agent_name, "No text to hand off — Phase 0 produced no output")
            return state

        logger.info(
            f"[HandoffGate] Validating Phase 0 output | "
            f"words={state.word_count()} | "
            f"sections={len(state.generated_sections)} | "
            f"stream_id={state.stream_id}"
        )

        violations: list[str] = []

        # Step 2: Structural validation
        violations.extend(self._check_structural_quality(state))

        # Step 3: Visualization check
        violations.extend(self._check_visualization_count(state))

        # Log violations (non-blocking)
        if violations:
            logger.warning(f"[HandoffGate] {len(violations)} violations found:")
            for v in violations:
                logger.warning(f"  - {v}")
        else:
            logger.info("[HandoffGate] All structural checks passed")

        # Step 4-5: Set register and domain for humanization pipeline
        state.register = self.REGISTER_MAP.get(state.stream_id, "general")
        pipeline_domain = self.DOMAIN_MAP.get(state.domain, "general")

        # Build metadata (stored for Phase 4 HumanizerManager)
        source_count = 0
        if state.source_list is not None:
            source_count = len(state.source_list.sources) if hasattr(state.source_list, 'sources') else 0

        metadata = HandoffMetadata(
            text=state.text,
            source_count=source_count,
            viz_count_tables=state.visualization_count.get("tables", 0),
            viz_count_figures=state.visualization_count.get("figures", 0),
            domain=pipeline_domain,
            register=state.register,
            language=state.language,
            stream_id=state.stream_id,
            level=state.level,
            sections_generated=len(state.generated_sections),
            structural_violations=violations,
        )

        # Store metadata in state for HumanizerManager (Phase 4)
        # Using analysis_report as a temporary container until Phase 4 defines its own
        state.analysis_report["handoff_metadata"] = {
            "source_count": metadata.source_count,
            "viz_count_tables": metadata.viz_count_tables,
            "viz_count_figures": metadata.viz_count_figures,
            "domain": metadata.domain,
            "register": metadata.register,
            "language": metadata.language,
            "stream_id": metadata.stream_id,
            "level": metadata.level,
            "sections_generated": metadata.sections_generated,
            "structural_violations": metadata.structural_violations,
            "word_count": state.word_count(),
        }

        logger.info(
            f"[HandoffGate] Handoff complete | "
            f"register={state.register} | domain={pipeline_domain} | "
            f"sources={source_count} | violations={len(violations)}"
        )

        return state

    def _check_structural_quality(self, state: PipelineState) -> list[str]:
        """
        Check for announcement openers and triplets in generated text.

        Uses simple regex detection (same patterns as generator.py structural check).
        Returns list of violation strings.
        """
        import re
        violations: list[str] = []
        text = state.text

        # Announcement openers (target: 0)
        patterns_en = [
            r"Here's the problem with",
            r"is worth a brief detour",
            r"There's also a .{1,30} worth flagging",
            r"also deserves mention",
            r"I mention this mostly because",
            r"is instructive about",
            r"is actually remarkable",
        ]
        patterns_ru = [
            r"следует отметить, что",
            r"необходимо отметить, что",
            r"важно подчеркнуть, что",
            r"стоит отметить, что",
            r"обратим внимание на то",
            r"отметим, что",
        ]
        patterns = patterns_ru if state.language == "ru" else patterns_en
        opener_count = 0
        for p in patterns:
            opener_count += len(re.findall(p, text, re.IGNORECASE))
        if opener_count > 0:
            violations.append(f"announcement_openers={opener_count} (target: 0)")

        # Triplets: X, Y, and Z pattern (matches generator.py _count_triplets logic)
        en_triplet = r'\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+and\s+\w'
        ru_triplet = r'\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+и\s+\w'
        triplet_pattern = ru_triplet if state.language == "ru" else en_triplet
        triplet_count = len(re.findall(triplet_pattern, text))
        if triplet_count > 0:
            violations.append(f"triplet_instances={triplet_count} (target: 0)")

        return violations

    def _check_visualization_count(self, state: PipelineState) -> list[str]:
        """Check visualization count against stream minimum."""
        from agents.gates.content_qa import ContentQAGate

        violations: list[str] = []
        gate = ContentQAGate()

        total_viz = state.visualization_count.get("tables", 0) + state.visualization_count.get("figures", 0)
        minimum = gate._get_viz_minimum(state.stream_id, state.level)

        if total_viz < minimum:
            violations.append(
                f"visualizations={total_viz} (minimum: {minimum} for {state.stream_id}/{state.level})"
            )

        return violations
```

---

## File 8: `agents/prompts/handoff_gate.md`

```markdown
# Handoff Gate — Phase 0 → Humanization Bridge

You are the Handoff Gate agent of the AI Anti-Anti Plag system.
Your role is to validate Phase 0 content generation output and prepare it
for the humanization pipeline (Stages 1-5).

## Validation Checks

### Hard Requirements (target: 0)
- Announcement openers: sentences that describe what they are about to say
- Triplet instances: X, Y, and Z parallel series
- Block 12 structural violations

### Soft Requirements
- Visualization count >= stream minimum (БЛОК 16.2)
- Source count >= stream minimum (GOST)

## Metadata Packaging

After validation, package the following for HumanizerManager:
- Full concatenated text
- Source count and visualization counts
- Domain → pipeline domain mapping
- Stream → register mapping
- Language for AC-rule gating
- List of structural violations found

## Non-Blocking Policy

This gate REPORTS violations but does NOT block the pipeline.
The humanization pipeline will handle remaining issues.
ContentQAGate (separate gate) handles blocking decisions.
```

---

## File 9: `tests/test_phase3a_base_worker.py`

```python
"""
Phase 3A Tests: BaseSectionWorker + MicroManager Integration + HandoffGate.
Run: pytest tests/test_phase3a_base_worker.py -v

Tests:
1. BaseSectionWorker instantiation and properties
2. BaseSectionWorker format-only section handling
3. BaseSectionWorker viz counting integration
4. BaseMicroManager._get_worker() is abstract
5. Concrete MMs implement _get_worker() (returns None in 3A)
6. BaseMicroManager.execute() skips when no workers
7. HandoffGate validation — clean text passes
8. HandoffGate validation — detects violations
9. HandoffGate metadata packaging
10. HandoffGate register/domain mapping
11. PipelineState has last_section_text field
12. AcademicGenerator has generate_section() method
13. Cross-check: DOMAIN_MAP matches generator.py
14. Cross-check: REGISTER_MAP matches generator.py
15. Phase 2 tests still pass (regression)
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: BaseSectionWorker basics ──────────────────────────────


class TestBaseSectionWorker:
    def test_instantiation(self):
        """BaseSectionWorker cannot be instantiated directly (abstract execute via BaseAgent)."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        # BaseSectionWorker inherits from BaseAgent which has abstract execute()
        # But BaseSectionWorker implements execute(), so it CAN be instantiated
        worker = BaseSectionWorker()
        assert worker.agent_type == "worker"
        assert worker.section_id == ""

    def test_agent_type_is_worker(self):
        """All section workers have agent_type 'worker'."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        worker = BaseSectionWorker()
        assert worker.agent_type == "worker"

    def test_format_only_sections_skip(self):
        """title_page and toc sections skip generation."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.state import PipelineState

        class TitlePageWorker(BaseSectionWorker):
            section_id = "title_page"
            agent_name = "test_title_page"

        worker = TitlePageWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert "title_page" in result.generated_sections
        assert result.generated_sections["title_page"] == ""

    def test_empty_section_id_produces_error(self):
        """Worker with empty section_id adds error."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.state import PipelineState

        worker = BaseSectionWorker()  # section_id = ""
        worker.agent_name = "test_empty"
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert result.has_errors()
        assert "section_id" in result.errors[0].lower()


# ── Test 2: BaseMicroManager abstract _get_worker ─────────────────


class TestBaseMicroManagerAbstract:
    def test_get_worker_is_abstract(self):
        """BaseMicroManager._get_worker() is abstract — cannot instantiate base directly."""
        from agents.content.micro_managers.base import BaseMicroManager

        # BaseMicroManager has abstract _get_worker(), so direct instantiation should fail
        with pytest.raises(TypeError):
            BaseMicroManager()

    def test_concrete_mms_implement_get_worker(self):
        """All 7 concrete MMs implement _get_worker()."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [
            MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch,
            MicroManagerAbstractPaper, MicroManagerText, MicroManagerEssay,
            MicroManagerComposition,
        ]:
            mm = mm_class()
            # Should not raise — method exists
            result = mm._get_worker("test_section")
            # Phase 3A: all return None
            assert result is None, f"{mm.agent_name}._get_worker() should return None in Phase 3A"


# ── Test 3: MicroManager execute with no workers ──────────────────


class TestMicroManagerExecuteNoWorkers:
    def test_execute_skips_all_sections(self):
        """MM execute() skips all sections when _get_worker returns None."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.state import PipelineState

        mm = MicroManagerVKR()
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            topic="Test topic",
            level="bachelor",
        )
        result = asyncio.run(mm.execute(state))

        # Should not error — skipping sections is graceful
        # (workers are None, so sections are skipped with warning)
        assert result.visualization_count == {"tables": 0, "figures": 0}

    def test_execute_preserves_section_order(self):
        """MM SECTION_ORDER is unchanged after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from pipeline.generator import SECTION_ORDER

        mm = MicroManagerVKR()
        assert mm.SECTION_ORDER == SECTION_ORDER["vkr"]


# ── Test 4: HandoffGate basics ────────────────────────────────────


class TestHandoffGate:
    def test_instantiation(self):
        """HandoffGate instantiates with correct properties."""
        from agents.gates.handoff_gate import HandoffGate
        gate = HandoffGate()
        assert gate.agent_name == "handoff_gate"
        assert gate.agent_type == "gate"

    def test_is_base_agent(self):
        """HandoffGate inherits from BaseAgent."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.base import BaseAgent
        gate = HandoffGate()
        assert isinstance(gate, BaseAgent)

    def test_no_text_produces_error(self):
        """HandoffGate adds error when state has no text."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        gate = HandoffGate()
        state = PipelineState(mode="generation", text="")
        result = asyncio.run(gate.execute(state))
        assert result.has_errors()
        assert "no text" in result.errors[0].lower()

    def test_clean_text_passes(self):
        """HandoffGate passes clean text without violations."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        gate = HandoffGate()
        state = PipelineState(
            mode="generation",
            text="This is a clean paragraph without any AI patterns. "
                 "It discusses economics and monetary policy.",
            stream_id="text",
            language="en",
            domain="economics",
        )
        result = asyncio.run(gate.execute(state))

        # No errors from handoff itself
        handoff = result.analysis_report.get("handoff_metadata")
        assert handoff is not None
        assert handoff["register"] == "journalistic"  # text → journalistic
        assert handoff["domain"] == "economics"

    def test_detects_announcement_openers(self):
        """HandoffGate detects announcement opener violations."""
        from agents.gates.handoff_gate import HandoffGate
        from agents.state import PipelineState

        text_with_openers = (
            "Here's the problem with modern economics. "
            "This topic also deserves mention in the context of policy."
        )
        gate = HandoffGate()
        state = PipelineState(
            mode="generation",
            text=text_with_openers,
            stream_id="text",
            language="en",
        )
        result = asyncio.run(gate.execute(state))

        handoff = result.analysis_report.get("handoff_metadata")
        assert handoff is not None
        assert len(handoff["structural_violations"]) > 0
        assert any("announcement" in v for v in handoff["structural_violations"])


# ── Test 5: HandoffGate register/domain mapping ──────────────────


class TestHandoffGateMapping:
    def test_register_mapping_all_streams(self):
        """HandoffGate maps all stream_ids to correct registers."""
        from agents.gates.handoff_gate import HandoffGate
        from pipeline.generator import REGISTER_MAP

        gate = HandoffGate()
        for stream_id, expected_register in REGISTER_MAP.items():
            assert gate.REGISTER_MAP[stream_id] == expected_register, (
                f"Register mismatch for {stream_id}: "
                f"HandoffGate={gate.REGISTER_MAP[stream_id]} vs generator={expected_register}"
            )

    def test_domain_mapping_all_domains(self):
        """HandoffGate maps all domains to correct pipeline codes."""
        from agents.gates.handoff_gate import HandoffGate
        from pipeline.generator import DOMAIN_MAP

        gate = HandoffGate()
        for domain, expected_code in DOMAIN_MAP.items():
            assert gate.DOMAIN_MAP[domain] == expected_code, (
                f"Domain mismatch for {domain}: "
                f"HandoffGate={gate.DOMAIN_MAP[domain]} vs generator={expected_code}"
            )


# ── Test 6: PipelineState new field ──────────────────────────────


class TestPipelineStateNewField:
    def test_last_section_text_exists(self):
        """PipelineState has last_section_text field with default empty string."""
        from agents.state import PipelineState
        state = PipelineState(mode="generation")
        assert hasattr(state, "last_section_text")
        assert state.last_section_text == ""

    def test_last_section_text_mutable(self):
        """last_section_text can be set and read."""
        from agents.state import PipelineState
        state = PipelineState(mode="generation")
        state.last_section_text = "Some generated text here"
        assert state.last_section_text == "Some generated text here"


# ── Test 7: AcademicGenerator.generate_section() exists ──────────


class TestGeneratorNewMethod:
    def test_generate_section_method_exists(self):
        """AcademicGenerator has generate_section() method."""
        from pipeline.generator import AcademicGenerator
        assert hasattr(AcademicGenerator, "generate_section")

    def test_generate_section_signature(self):
        """generate_section() accepts expected parameters."""
        import inspect
        from pipeline.generator import AcademicGenerator

        sig = inspect.signature(AcademicGenerator.generate_section)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "section_id" in params
        assert "params" in params
        assert "source_list" in params
        assert "previously_generated" in params

    def test_generate_section_format_only_returns_empty(self):
        """generate_section('title_page') returns empty string."""
        from pipeline.generator import AcademicGenerator, GenerationParams
        from pipeline import load_config

        config = load_config()
        gen = AcademicGenerator(config)
        params = GenerationParams(stream_id="vkr", topic="Test", language="ru")

        result = gen.generate_section("title_page", params)
        assert result == ""

        result2 = gen.generate_section("toc", params)
        assert result2 == ""


# ── Test 8: HandoffMetadata dataclass ─────────────────────────────


class TestHandoffMetadata:
    def test_creation(self):
        """HandoffMetadata can be created with required fields."""
        from agents.gates.handoff_gate import HandoffMetadata
        meta = HandoffMetadata(text="Some text")
        assert meta.text == "Some text"
        assert meta.source_count == 0
        assert meta.viz_count_tables == 0
        assert meta.structural_violations == []

    def test_full_creation(self):
        """HandoffMetadata with all fields."""
        from agents.gates.handoff_gate import HandoffMetadata
        meta = HandoffMetadata(
            text="Full text",
            source_count=25,
            viz_count_tables=3,
            viz_count_figures=2,
            domain="cs",
            register="academic",
            language="ru",
            stream_id="vkr",
            level="bachelor",
            sections_generated=9,
            structural_violations=["triplets=2"],
        )
        assert meta.source_count == 25
        assert meta.viz_count_tables == 3
        assert meta.sections_generated == 9
        assert len(meta.structural_violations) == 1


# ── Test 9: Phase 2 regression — SECTION_ORDERs still match ──────


class TestPhase2Regression:
    def test_all_section_orders_still_match_generator(self):
        """Phase 2 SECTION_ORDER cross-check still passes after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from pipeline.generator import SECTION_ORDER

        mm_map = {
            "vkr": MicroManagerVKR,
            "coursework": MicroManagerCoursework,
            "research": MicroManagerResearch,
            "abstract_paper": MicroManagerAbstractPaper,
            "text": MicroManagerText,
            "essay": MicroManagerEssay,
            "composition": MicroManagerComposition,
        }

        for stream_id, mm_class in mm_map.items():
            mm = mm_class()
            generator_order = SECTION_ORDER[stream_id]
            assert mm.SECTION_ORDER == generator_order, (
                f"{mm.agent_name} SECTION_ORDER mismatch: "
                f"MM={mm.SECTION_ORDER} vs generator={generator_order}"
            )

    def test_all_viz_minimums_still_match_content_qa_gate(self):
        """Phase 2 VIZ_MINIMUMS cross-check still passes after Phase 3A upgrade."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()

        stream_checks = {
            "vkr": (MicroManagerVKR, ["bachelor", "master", "specialist", "postgraduate"]),
            "coursework": (MicroManagerCoursework, ["default", "bachelor", "master"]),
            "research": (MicroManagerResearch, ["default", "bachelor", "master"]),
            "abstract_paper": (MicroManagerAbstractPaper, ["default", "bachelor"]),
            "text": (MicroManagerText, ["default", "bachelor"]),
            "essay": (MicroManagerEssay, ["default", "bachelor"]),
            "composition": (MicroManagerComposition, ["default", "bachelor"]),
        }

        for stream_id, (mm_class, levels) in stream_checks.items():
            mm = mm_class()
            gate_stream = gate.VIZ_MINIMUMS.get(stream_id, {})

            for level in levels:
                mm_val = mm.get_viz_minimum(level)
                gate_val = gate_stream.get(level, gate_stream.get("default", 0))
                assert mm_val == gate_val, (
                    f"VIZ_MINIMUMS mismatch for {stream_id}/{level}: "
                    f"MM={mm_val} vs ContentQAGate={gate_val}"
                )


# ── Test 10: count_visualizations still works ─────────────────────


class TestCountVisualizationsRegression:
    def test_count_tables(self):
        """count_visualizations still counts markdown tables correctly."""
        text = """
| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |

Some text.

| X | Y |
|---|---|
| 1 | 2 |
"""
        # Cannot call static method on abstract class directly in Phase 3A
        # because BaseMicroManager is now abstract. Use a concrete MM instead.
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 2
        assert figures == 0

    def test_count_figures(self):
        """count_visualizations still counts figure placeholders correctly."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        text = """
[РИСУНОК 1 — Структура]

Some text.

[FIGURE 2 — Architecture]
"""
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 0
        assert figures == 2
```

---

## Verification Checklist

After implementation, run these checks in order:

```bash
# 1. New tests pass
pytest tests/test_phase3a_base_worker.py -v

# 2. Phase 2 tests still pass (CRITICAL regression check)
pytest tests/test_phase2_content.py -v

# 3. Phase 1 tests still pass
pytest tests/test_phase1_ceo.py -v

# 4. Foundation tests still pass
pytest tests/test_agents_foundation.py -v

# 5. All tests combined
pytest tests/ -v --tb=short

# 6. Verify generate_section() exists
python -c "from pipeline.generator import AcademicGenerator; print(hasattr(AcademicGenerator, 'generate_section'))"

# 7. Verify BaseMicroManager is abstract
python -c "
from agents.content.micro_managers.base import BaseMicroManager
try:
    BaseMicroManager()
    print('ERROR: should be abstract')
except TypeError:
    print('OK: BaseMicroManager is abstract')
"

# 8. Verify all 7 MMs still instantiate
python -c "
from agents.content.micro_managers.mm_vkr import MicroManagerVKR
from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
from agents.content.micro_managers.mm_research import MicroManagerResearch
from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
from agents.content.micro_managers.mm_text import MicroManagerText
from agents.content.micro_managers.mm_essay import MicroManagerEssay
from agents.content.micro_managers.mm_composition import MicroManagerComposition
for cls in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper, MicroManagerText, MicroManagerEssay, MicroManagerComposition]:
    mm = cls()
    print(f'{mm.agent_name}: OK (SECTION_ORDER={len(mm.SECTION_ORDER)} sections)')
"
```

---

## Critical Constraints

1. **generator.py**: ONLY add `generate_section()` method. Do NOT modify any existing method.
2. **state.py**: ONLY add `last_section_text` field. Do NOT modify any existing field.
3. **base.py (micro_managers)**: Full replacement — but ALL existing methods preserved identically. `_get_worker()` is the only new abstract method.
4. **7 concrete MMs**: ONLY add `_get_worker()` method. Do NOT modify any existing field or method.
5. **Phase 2 test regression**: `test_phase2_content.py` must still pass 34/34. The key risk is `BaseMicroManager` becoming abstract — Phase 2 tests that instantiate it directly will break. The test file uses concrete MMs (MicroManagerVKR etc.), not BaseMicroManager directly, so this should be safe. But verify.
6. **count_visualizations**: This is a `@staticmethod` on BaseMicroManager. Static methods work on abstract classes, but the test `TestCountVisualizations` in Phase 2 calls `BaseMicroManager.count_visualizations()` directly. Since it's `@staticmethod`, this works even on abstract classes. Verify.

---

## Summary of Changes

| Component | Action | Scope |
|-----------|--------|-------|
| `pipeline/generator.py` | ADD `generate_section()` | 1 new method (~50 lines) |
| `agents/state.py` | ADD `last_section_text` | 1 new field |
| `agents/content/workers/__init__.py` | CREATE | Package init |
| `agents/content/workers/base_section_worker.py` | CREATE | Template class (~160 lines) |
| `agents/content/micro_managers/base.py` | REPLACE | Stub → real orchestration |
| `agents/content/micro_managers/mm_vkr.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_coursework.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_research.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_abstract_paper.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_text.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_essay.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/content/micro_managers/mm_composition.py` | ADD `_get_worker()` | 1 method (returns None) |
| `agents/gates/handoff_gate.py` | CREATE | Gate + HandoffMetadata |
| `agents/prompts/handoff_gate.md` | CREATE | Prompt template |
| `tests/test_phase3a_base_worker.py` | CREATE | ~25 test methods |
