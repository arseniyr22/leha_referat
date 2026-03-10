# Phase 2: Content Manager + 7 Micro Managers — Implementation Prompt

## Overview

Phase 2 builds the content generation orchestration layer. **ContentManager** is the top-level agent for generation mode: it calls SourceFinder, routes to the correct **Micro Manager** by `stream_id`, and the MM orchestrates section-by-section generation.

**Principle**: wrap, not rewrite. ContentManager and MMs call existing `pipeline/generator.py` and `pipeline/source_finder.py` — they do NOT re-implement generation logic.

**Phase 2 scope**: ContentManager + BaseMicroManager + 7 concrete MMs + tests. Workers come in Phase 3. In Phase 2, MMs define their SECTION_ORDER and VIZ_MINIMUMS but do not actually generate text — they are structural stubs ready for Phase 3 worker integration.

**ContentManager is NOT wired into CEOAgent yet** — that integration happens in Phase 3. ContentManager is a standalone agent that can be tested independently.

---

## Files to Create (13 total)

```
agents/content/__init__.py                      # Package init
agents/content/manager.py                       # ContentManager
agents/content/micro_managers/__init__.py        # MM package init
agents/content/micro_managers/base.py            # BaseMicroManager (ABC)
agents/content/micro_managers/mm_vkr.py          # 9 sections
agents/content/micro_managers/mm_coursework.py   # 7 sections
agents/content/micro_managers/mm_research.py     # 8 sections
agents/content/micro_managers/mm_abstract_paper.py  # 6 sections
agents/content/micro_managers/mm_text.py         # 4 subtypes, SECTION_ORDER = ["full"]
agents/content/micro_managers/mm_essay.py        # SECTION_ORDER = ["full"]
agents/content/micro_managers/mm_composition.py  # SECTION_ORDER = ["full"]
agents/prompts/content_manager.md                # ContentManager prompt
tests/test_phase2_content.py                     # 12+ tests
```

**Files to modify**: NONE. Zero modifications to any existing file.

**Deferred to Phase 3**: `agents/prompts/mm_*.md` (7 MM prompts) — MMs are stubs in Phase 2 and don't use prompts. MM prompts will be created alongside workers in Phase 3.

**Note**: `SourceFinder.find()` is synchronous. ContentManager calls it from an async method — this blocks the event loop but is acceptable because the pipeline is sequential. No concurrency optimization needed now.

---

## File 1: `agents/content/__init__.py`

```python
"""
Content generation agents package.

ContentManager orchestrates Phase 0 content generation:
- Calls SourceFinder (Phase 0A)
- Routes to the correct MicroManager by stream_id (Phase 0B)
- MicroManager generates sections via workers (Phase 3)

Hierarchy: CEO → ContentManager → MicroManager → Worker (Phase 3)
"""
```

---

## File 2: `agents/content/manager.py`

```python
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
```

### Key design decisions for `manager.py`:

1. **Import all 7 MM classes at module level** — simple routing table, no dynamic imports
2. **Source discovery first** — SourceFinder called before any MM, result stored in `state.source_list`
3. **Source minimum validation** — checked AFTER MM completes, not blocking generation
4. **Streams with 0 minimum** (text, essay, composition) — skip source discovery entirely
5. **VKR level-specific minimums** — `vkr_bachelor` = 50, `vkr_master` = 60
6. **Error handling** — errors stored in state, never crash pipeline
7. **No text generation** — ContentManager delegates 100% to MMs

---

## File 3: `agents/content/micro_managers/__init__.py`

```python
"""
Micro Manager agents for content generation.

Each MicroManager handles one stream_id type and knows:
- SECTION_ORDER: exact sequence of sections to generate
- VIZ_MINIMUMS: minimum visualization count by level (БЛОК 16.2)
- DATA_HEAVY_SECTIONS: sections to re-generate if viz count is below minimum

Hierarchy: ContentManager → MicroManager → Worker (Phase 3)

7 concrete MMs:
- MicroManagerVKR (9 sections)
- MicroManagerCoursework (7 sections)
- MicroManagerResearch (8 sections)
- MicroManagerAbstractPaper (6 sections)
- MicroManagerText (4 subtypes, 1 section each)
- MicroManagerEssay (1 section)
- MicroManagerComposition (1 section)
"""
```

---

## File 4: `agents/content/micro_managers/base.py`

```python
from __future__ import annotations

import re
from abc import abstractmethod  # Unused in Phase 2 (stubs); kept for Phase 3 when abstract methods may be needed

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

    Phase 2: structural stubs. execute() validates SECTION_ORDER
    and VIZ_MINIMUMS but does not actually generate text. Workers
    (Phase 3) will plug into _execute_section().

    Phase 3: execute() iterates SECTION_ORDER, calls worker per section,
    tracks viz count, re-gens data-heavy sections if needed.
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

        Phase 2 implementation: stub that validates configuration
        and prepares state for Phase 3 worker integration.

        Phase 3 will add actual generation via workers.

        Steps (Phase 2 — structural validation only):
        1. Validate SECTION_ORDER is defined and non-empty
        2. Log section plan
        3. Initialize viz tracking in state
        4. Return state (no actual generation yet)

        Steps (Phase 3 — full implementation):
        1. For each section_id in SECTION_ORDER:
           a. Get worker for section_id
           b. state = await worker.execute(state)
           c. Count tables + figures in generated section
           d. Accumulate viz count
        2. If total_viz < minimum: re-gen DATA_HEAVY_SECTIONS (max 1 retry)
        3. TOC 2-pass: if "toc" in SECTION_ORDER, run toc_worker.execute_pass_2()
        4. Store viz_count in state.visualization_count
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

        # Phase 2: structural stub — log plan, don't generate
        # Phase 3 will replace this with actual worker orchestration
        for i, section_id in enumerate(self.SECTION_ORDER):
            logger.info(
                f"[{self.agent_name}] Section {i + 1}/{len(self.SECTION_ORDER)}: "
                f"{section_id} (Phase 2 stub — no generation)"
            )

        # Log viz minimum requirement
        viz_min = self.get_viz_minimum(state.level)
        if viz_min > 0:
            logger.info(
                f"[{self.agent_name}] Viz minimum for {self.STREAM_ID}/{state.level}: "
                f"{viz_min} | data-heavy sections: {self.DATA_HEAVY_SECTIONS}"
            )

        logger.info(f"[{self.agent_name}] Complete (Phase 2 stub)")
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

### Key design decisions for `base.py`:

1. **Phase 2 = structural stub** — execute() logs plan but doesn't generate. Phase 3 adds workers.
2. **count_visualizations()** is a static utility — works on raw text, counts markdown tables and figure placeholders
3. **VIZ_MINIMUMS uses level keys** — `"bachelor": 5, "master": 8` etc., with `"default"` fallback
4. **DATA_HEAVY_SECTIONS** — defined per MM, used in Phase 3 for viz re-gen
5. **has_toc() / is_single_generation()** — utility methods for Phase 3 orchestration logic

---

## File 5: `agents/content/micro_managers/mm_vkr.py`

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerVKR(BaseMicroManager):
    """
    Micro Manager for VKR (Выпускная квалификационная работа).

    9 sections in GOST order (from CLAUDE.md / GAP 4.4):
    title_page → annotation → toc → introduction → chapter_1 →
    chapter_2 → chapter_3 → conclusion → references

    Visualization minimums from БЛОК 16.2:
    - bachelor: 5 tables/figures
    - master: 8 tables/figures
    - specialist: 5 tables/figures
    - postgraduate: 10 tables/figures

    Data-heavy sections for viz re-gen:
    - chapter_2 (empirical results, data analysis)
    - chapter_3 (practical application, recommendations)
    """

    agent_name = "mm_vkr"
    STREAM_ID = "vkr"

    SECTION_ORDER = [
        "title_page",
        "annotation",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "chapter_3",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "bachelor": 5,
        "master": 8,
        "specialist": 5,
        "postgraduate": 10,
    }

    DATA_HEAVY_SECTIONS = ["chapter_2", "chapter_3"]
```

---

## File 6: `agents/content/micro_managers/mm_coursework.py`

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerCoursework(BaseMicroManager):
    """
    Micro Manager for Coursework (Курсовая работа).

    7 sections in GOST order (from CLAUDE.md / GAP 4.4):
    title_page → toc → introduction → chapter_1 → chapter_2 →
    conclusion → references

    Visualization minimums from БЛОК 16.2:
    - default: 3 tables/figures

    Data-heavy sections for viz re-gen:
    - chapter_2 (practical/empirical part)
    """

    agent_name = "mm_coursework"
    STREAM_ID = "coursework"

    SECTION_ORDER = [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "default": 3,
    }

    DATA_HEAVY_SECTIONS = ["chapter_2"]
```

---

## File 7: `agents/content/micro_managers/mm_research.py`

```python
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
```

---

## File 8: `agents/content/micro_managers/mm_abstract_paper.py`

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerAbstractPaper(BaseMicroManager):
    """
    Micro Manager for Abstract Paper (Реферат).

    6 sections (from CLAUDE.md / GAP 4.4):
    title_page → toc → introduction → chapter_1 → conclusion → references

    Visualization minimums from БЛОК 16.2:
    - default: 1 table/figure (desirable, not mandatory)

    Data-heavy sections for viz re-gen:
    - chapter_1 (main content section)
    """

    agent_name = "mm_abstract_paper"
    STREAM_ID = "abstract_paper"

    SECTION_ORDER = [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "conclusion",
        "references",
    ]

    VIZ_MINIMUMS = {
        "default": 1,
    }

    DATA_HEAVY_SECTIONS = ["chapter_1"]
```

---

## File 9: `agents/content/micro_managers/mm_text.py`

```python
from __future__ import annotations

from loguru import logger

from agents.content.micro_managers.base import BaseMicroManager
from agents.state import PipelineState


class MicroManagerText(BaseMicroManager):
    """
    Micro Manager for Text (Текст).

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker that calls generator.generate(params) for full text.

    4 subtypes (determined by domain/topic context):
    - analytical: data-driven analysis, opinion with evidence
    - journalistic: news/feature article style
    - review: literature/product/topic review
    - descriptive: factual description, informational

    Subtype selection:
    - domain "media" or "journalistic" → journalistic
    - domain "it_cs" or "economics" → analytical
    - domain "humanities" → descriptive
    - default → analytical

    Note: state does not currently have a text_subtype field.
    In Phase 3, subtype will be used to select the correct worker
    (text_analytical.py, text_journalistic.py, etc.).
    In Phase 2, subtype is computed and logged but not acted upon.

    Visualization minimums from БЛОК 16.2:
    - default: 0 (context-dependent — if data/statistics present)
    """

    agent_name = "mm_text"
    STREAM_ID = "text"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []

    # Subtype routing: domain → text_subtype
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

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Execute text generation (Phase 2 stub).

        Additional logic vs base:
        - Determines text subtype from domain
        - Logs subtype for Phase 3 worker routing
        """
        # Determine subtype
        subtype = self._determine_subtype(state.domain)
        logger.info(
            f"[{self.agent_name}] Text subtype determined: {subtype} "
            f"(domain={state.domain})"
        )

        # Call base execute (Phase 2 stub)
        state = await super().execute(state)

        return state

    def _determine_subtype(self, domain: str) -> str:
        """
        Determine text subtype from domain.

        Returns one of: analytical, journalistic, review, descriptive
        """
        return self.SUBTYPE_ROUTING.get(domain, "analytical")
```

---

## File 10: `agents/content/micro_managers/mm_essay.py`

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerEssay(BaseMicroManager):
    """
    Micro Manager for Essay (Эссе).

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker (essay_full.py in Phase 3) that calls
    generator.generate(params) for the full essay in one API call.

    Visualization minimums from БЛОК 16.2:
    - default: 0 (optional — only if it strengthens the argument)
    """

    agent_name = "mm_essay"
    STREAM_ID = "essay"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []
```

---

## File 11: `agents/content/micro_managers/mm_composition.py`

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerComposition(BaseMicroManager):
    """
    Micro Manager for Composition (Сочинение).

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker (comp_full.py in Phase 3) that calls
    generator.generate(params) for the full composition in one API call.

    Visualization minimums from БЛОК 16.2:
    - default: 0 (none required)
    """

    agent_name = "mm_composition"
    STREAM_ID = "composition"

    SECTION_ORDER = ["full"]

    VIZ_MINIMUMS = {
        "default": 0,
    }

    DATA_HEAVY_SECTIONS = []
```

---

## File 12: `agents/prompts/content_manager.md`

```markdown
# Content Manager — Generation Orchestration

You are the Content Manager agent of the AI Anti-Anti Plag system.
Your role is to orchestrate Phase 0 content generation.

## Responsibilities

1. Call SourceFinder (Phase 0A) to discover bibliography
2. Route to correct MicroManager by stream_id
3. Validate source counts meet GOST minimums
4. Track visualization counts vs. БЛОК 16.2 minimums

## Routing Rules

### Stream → MicroManager

| stream_id       | MicroManager           | Sections |
|-----------------|------------------------|----------|
| vkr             | MicroManagerVKR        | 9        |
| coursework      | MicroManagerCoursework | 7        |
| research        | MicroManagerResearch   | 8        |
| abstract_paper  | MicroManagerAbstractPaper | 6     |
| text            | MicroManagerText       | 1 (full) |
| essay           | MicroManagerEssay      | 1 (full) |
| composition     | MicroManagerComposition | 1 (full) |

### Source Minimums

| stream_id          | Minimum Sources |
|--------------------|-----------------|
| vkr (bachelor)     | 50              |
| vkr (master)       | 60              |
| vkr (specialist)   | 50              |
| vkr (postgraduate) | 60              |
| coursework         | 20              |
| research           | 30              |
| abstract_paper     | 10              |
| text/essay/composition | 0           |

## Execution Flow

1. Validate: mode == "generation", topic present, stream_id valid
2. Phase 0A: SourceFinder.find() — discover bibliography
3. Phase 0B: Route to MM → MM generates all sections
4. Validate: source count >= minimum for stream_id/level
5. Return state with generated_sections + source_list
```

---

## File 13: `tests/test_phase2_content.py`

```python
"""
Phase 2 Content Manager + MicroManager Tests.
Run: pytest tests/test_phase2_content.py -v

Tests:
1. ContentManager instantiation + BaseAgent inheritance
2. ContentManager routing — all 7 stream_ids
3. ContentManager routing — unknown stream_id
4. ContentManager requires generation mode
5. ContentManager requires topic
6. ContentManager requires stream_id
7. ContentManager source minimum lookup (VKR level-specific)
8. ContentManager source minimum lookup (flat streams)
9. BaseMicroManager — MicroManagerVKR section order
10. BaseMicroManager — all 7 MMs have correct SECTION_ORDER
11. BaseMicroManager — VIZ_MINIMUMS correctness
12. BaseMicroManager — count_visualizations utility
13. BaseMicroManager — single-generation detection
14. BaseMicroManager — has_toc detection
15. MicroManagerText — subtype routing
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: ContentManager instantiation ─────────────────────────────


class TestContentManagerBasics:
    def test_instantiation(self):
        """ContentManager can be instantiated."""
        from agents.content.manager import ContentManager
        cm = ContentManager()
        assert cm.agent_name == "content_manager"
        assert cm.agent_type == "manager"

    def test_is_base_agent(self):
        """ContentManager inherits from BaseAgent."""
        from agents.content.manager import ContentManager
        from agents.base import BaseAgent
        cm = ContentManager()
        assert isinstance(cm, BaseAgent)


# ── Test 2: ContentManager routing ───────────────────────────────────


class TestContentManagerRouting:
    def test_routing_all_stream_ids(self):
        """ContentManager routes to correct MM for all 7 stream_ids."""
        from agents.content.manager import ContentManager
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        cm = ContentManager()

        expected = {
            "vkr": MicroManagerVKR,
            "coursework": MicroManagerCoursework,
            "research": MicroManagerResearch,
            "abstract_paper": MicroManagerAbstractPaper,
            "text": MicroManagerText,
            "essay": MicroManagerEssay,
            "composition": MicroManagerComposition,
        }

        for stream_id, expected_class in expected.items():
            mm = cm._get_micro_manager(stream_id)
            assert mm is not None, f"No MM for {stream_id}"
            assert isinstance(mm, expected_class), (
                f"Wrong MM for {stream_id}: expected {expected_class.__name__}, "
                f"got {type(mm).__name__}"
            )

    def test_routing_unknown_stream_id(self):
        """Unknown stream_id returns None."""
        from agents.content.manager import ContentManager
        cm = ContentManager()
        mm = cm._get_micro_manager("invalid_stream")
        assert mm is None


# ── Test 3: ContentManager validation ────────────────────────────────


class TestContentManagerValidation:
    def test_requires_generation_mode(self):
        """ContentManager adds error for non-generation mode."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="humanization", stream_id="vkr", topic="Test topic")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "generation mode" in result.errors[0].lower()

    def test_requires_topic(self):
        """ContentManager adds error if topic is empty."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="generation", stream_id="vkr", topic="")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "topic" in result.errors[0].lower()

    def test_requires_stream_id(self):
        """ContentManager adds error if stream_id is empty."""
        from agents.content.manager import ContentManager
        from agents.state import PipelineState

        cm = ContentManager()
        state = PipelineState(mode="generation", stream_id="", topic="Test topic")
        result = asyncio.run(cm.execute(state))
        assert result.has_errors()
        assert "stream_id" in result.errors[0].lower()


# ── Test 4: Source minimum lookup ────────────────────────────────────


class TestSourceMinimums:
    def test_vkr_level_specific_minimums(self):
        """VKR source minimums are level-specific."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("vkr", "bachelor") == 50
        assert cm._get_source_minimum("vkr", "master") == 60
        assert cm._get_source_minimum("vkr", "specialist") == 50
        assert cm._get_source_minimum("vkr", "postgraduate") == 60

    def test_flat_stream_minimums(self):
        """Non-VKR streams have flat minimums."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("coursework", "bachelor") == 20
        assert cm._get_source_minimum("research", "master") == 30
        assert cm._get_source_minimum("abstract_paper", "bachelor") == 10

    def test_zero_minimum_streams(self):
        """Text, essay, composition have 0 source minimum."""
        from agents.content.manager import ContentManager
        cm = ContentManager()

        assert cm._get_source_minimum("text", "") == 0
        assert cm._get_source_minimum("essay", "") == 0
        assert cm._get_source_minimum("composition", "") == 0


# ── Test 5: MicroManager section orders ──────────────────────────────


class TestMicroManagerSectionOrders:
    def test_vkr_section_order(self):
        """VKR has 9 sections in correct GOST order."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        mm = MicroManagerVKR()
        expected = [
            "title_page", "annotation", "toc", "introduction",
            "chapter_1", "chapter_2", "chapter_3",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 9

    def test_coursework_section_order(self):
        """Coursework has 7 sections in correct order."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        mm = MicroManagerCoursework()
        expected = [
            "title_page", "toc", "introduction",
            "chapter_1", "chapter_2",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 7

    def test_research_section_order(self):
        """Research has 8 sections in correct order."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        expected = [
            "annotation", "introduction", "literature_review",
            "methodology", "results", "discussion",
            "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 8

    def test_abstract_paper_section_order(self):
        """Abstract paper has 6 sections in correct order."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        mm = MicroManagerAbstractPaper()
        expected = [
            "title_page", "toc", "introduction",
            "chapter_1", "conclusion", "references",
        ]
        assert mm.SECTION_ORDER == expected
        assert len(mm.SECTION_ORDER) == 6

    def test_single_generation_streams(self):
        """Text, essay, composition have SECTION_ORDER = ['full']."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [MicroManagerText, MicroManagerEssay, MicroManagerComposition]:
            mm = mm_class()
            assert mm.SECTION_ORDER == ["full"], f"{mm.agent_name} should have ['full']"
            assert mm.is_single_generation(), f"{mm.agent_name} should be single-generation"

    def test_all_section_orders_match_generator(self):
        """All MM SECTION_ORDERs match pipeline/generator.py SECTION_ORDER exactly."""
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
                f"{mm.agent_name} SECTION_ORDER mismatch with generator: "
                f"MM={mm.SECTION_ORDER} vs generator={generator_order}"
            )


# ── Test 6: VIZ_MINIMUMS ────────────────────────────────────────────


class TestVizMinimums:
    def test_vkr_viz_minimums(self):
        """VKR has level-specific viz minimums from БЛОК 16.2."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        mm = MicroManagerVKR()
        assert mm.get_viz_minimum("bachelor") == 5
        assert mm.get_viz_minimum("master") == 8
        assert mm.get_viz_minimum("specialist") == 5
        assert mm.get_viz_minimum("postgraduate") == 10

    def test_coursework_viz_minimum(self):
        """Coursework has default viz minimum of 3."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        mm = MicroManagerCoursework()
        assert mm.get_viz_minimum("bachelor") == 3
        assert mm.get_viz_minimum("master") == 3

    def test_research_viz_minimum(self):
        """Research has default viz minimum of 3."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        assert mm.get_viz_minimum("bachelor") == 3

    def test_abstract_paper_viz_minimum(self):
        """Abstract paper has default viz minimum of 1."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        mm = MicroManagerAbstractPaper()
        assert mm.get_viz_minimum("bachelor") == 1

    def test_zero_viz_streams(self):
        """Text, essay, composition have 0 viz minimum."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        for mm_class in [MicroManagerText, MicroManagerEssay, MicroManagerComposition]:
            mm = mm_class()
            assert mm.get_viz_minimum("bachelor") == 0
            assert mm.get_viz_minimum("master") == 0

    def test_viz_minimums_match_content_qa_gate_all_streams(self):
        """All 7 MM VIZ_MINIMUMS match ContentQAGate.VIZ_MINIMUMS."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()

        # Map: stream_id → (MM class, levels to check)
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
                # ContentQAGate uses nested dict: stream_id → level → int
                # with "default" fallback
                gate_val = gate_stream.get(level, gate_stream.get("default", 0))
                assert mm_val == gate_val, (
                    f"VIZ_MINIMUMS mismatch for {stream_id}/{level}: "
                    f"MM={mm_val} vs ContentQAGate={gate_val}"
                )


# ── Test 7: count_visualizations utility ─────────────────────────────


class TestCountVisualizations:
    def test_count_tables(self):
        """Counts markdown tables correctly."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
Some text before.

| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |

Some text between.

| X | Y | Z |
|---|---|---|
| 1 | 2 | 3 |

Some text after.
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 2
        assert figures == 0

    def test_count_figures(self):
        """Counts figure placeholders correctly (both RU and EN)."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
Some text.

[РИСУНОК 1 — Структура системы]

More text.

[FIGURE 2 — System Architecture]

Even more text.

[Рисунок 3 — Диаграмма]
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 0
        assert figures == 3

    def test_count_mixed(self):
        """Counts tables and figures together."""
        from agents.content.micro_managers.base import BaseMicroManager

        text = """
| A | B |
|---|---|
| 1 | 2 |

[РИСУНОК 1 — Название]

| C | D |
|---|---|
| 3 | 4 |
"""
        tables, figures = BaseMicroManager.count_visualizations(text)
        assert tables == 2
        assert figures == 1

    def test_count_empty_text(self):
        """Empty text returns 0,0."""
        from agents.content.micro_managers.base import BaseMicroManager
        tables, figures = BaseMicroManager.count_visualizations("")
        assert tables == 0
        assert figures == 0


# ── Test 8: has_toc and is_single_generation ─────────────────────────


class TestMicroManagerUtilities:
    def test_has_toc_multi_section(self):
        """VKR, coursework, abstract_paper have TOC."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        assert MicroManagerVKR().has_toc()
        assert MicroManagerCoursework().has_toc()
        assert MicroManagerAbstractPaper().has_toc()

    def test_no_toc_streams(self):
        """Research, text, essay, composition do NOT have TOC."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        assert not MicroManagerResearch().has_toc()
        assert not MicroManagerText().has_toc()
        assert not MicroManagerEssay().has_toc()
        assert not MicroManagerComposition().has_toc()


# ── Test 9: MicroManagerText subtype routing ─────────────────────────


class TestMicroManagerTextSubtype:
    def test_subtype_routing(self):
        """Text MM routes domains to correct subtypes."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        mm = MicroManagerText()

        assert mm._determine_subtype("media") == "journalistic"
        assert mm._determine_subtype("it_cs") == "analytical"
        assert mm._determine_subtype("economics") == "analytical"
        assert mm._determine_subtype("humanities") == "descriptive"
        assert mm._determine_subtype("general") == "analytical"
        assert mm._determine_subtype("unknown") == "analytical"  # fallback


# ── Test 10: MicroManager execute (Phase 2 stub) ────────────────────


class TestMicroManagerExecute:
    def test_vkr_execute_stub(self):
        """VKR MM executes without error (Phase 2 stub)."""
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
        assert not result.has_errors()
        assert result.visualization_count == {"tables": 0, "figures": 0}

    def test_text_execute_stub(self):
        """Text MM executes without error (Phase 2 stub)."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.state import PipelineState

        mm = MicroManagerText()
        state = PipelineState(
            mode="generation",
            stream_id="text",
            topic="Test topic",
            domain="media",
        )
        result = asyncio.run(mm.execute(state))
        assert not result.has_errors()

    def test_all_mms_inherit_base(self):
        """All 7 MMs inherit from BaseMicroManager."""
        from agents.content.micro_managers.base import BaseMicroManager
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
            assert isinstance(mm, BaseMicroManager), (
                f"{mm.agent_name} does not inherit BaseMicroManager"
            )

    def test_all_mms_have_stream_id(self):
        """All 7 MMs have non-empty STREAM_ID."""
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
            assert mm.STREAM_ID != "", f"{mm.agent_name} has empty STREAM_ID"
            assert mm.agent_name != "", f"MM has empty agent_name"

    def test_all_mms_have_nonempty_section_order(self):
        """All 7 MMs have at least 1 section in SECTION_ORDER."""
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
            assert len(mm.SECTION_ORDER) > 0, f"{mm.agent_name} has empty SECTION_ORDER"
```

---

## Verification Checklist

After implementation, verify:

1. **All 150+ existing tests pass**: `pytest tests/test_pipeline.py -v` — zero regressions
2. **All 13 Phase 0 tests pass**: `pytest tests/test_phase0_foundation.py -v`
3. **All 14 Phase 1 tests pass**: `pytest tests/test_phase1_ceo.py -v`
4. **All Phase 2 tests pass**: `pytest tests/test_phase2_content.py -v`
5. **No existing files modified**: check with `git diff --name-only` — Phase 2 only CREATES files
6. **Import chain works**: `python -c "from agents.content.manager import ContentManager; print('OK')"`
7. **All 7 MMs importable**: `python -c "from agents.content.micro_managers.mm_vkr import MicroManagerVKR; from agents.content.micro_managers.mm_coursework import MicroManagerCoursework; from agents.content.micro_managers.mm_research import MicroManagerResearch; from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper; from agents.content.micro_managers.mm_text import MicroManagerText; from agents.content.micro_managers.mm_essay import MicroManagerEssay; from agents.content.micro_managers.mm_composition import MicroManagerComposition; print('All 7 MMs OK')"`

## Critical Constraints

1. **DO NOT modify any existing files** — only create new files
2. **DO NOT wire ContentManager into CEOAgent** — that's Phase 3
3. **DO NOT implement actual text generation in MMs** — Phase 2 MMs are stubs
4. **SECTION_ORDERs must EXACTLY match `pipeline/generator.py` SECTION_ORDER** — this is cross-referenced in tests
5. **VIZ_MINIMUMS must match `agents/gates/content_qa.py` ContentQAGate.VIZ_MINIMUMS** — cross-referenced in tests
6. **All agents inherit from BaseAgent** (from `agents/base.py`)
7. **All MMs inherit from BaseMicroManager** (from `agents/content/micro_managers/base.py`)
8. **Error handling: use `state.add_error(self.agent_name, msg)`** — never raise exceptions

## API Signatures Reference (existing code — DO NOT modify)

### PipelineState (from `agents/state.py`)
```python
@dataclass
class PipelineState:
    mode: str                        # "generation" | "humanization"
    text: str = ""
    stream_id: str = ""
    topic: str = ""
    language: str = "en"
    domain: str = "general"
    register: str = "general"
    level: str = ""
    research_type: str = ""
    university: str = ""
    source_list: Any = None          # SourceList from Phase 0A
    generated_sections: dict = field(default_factory=dict)
    visualization_count: dict = field(default_factory=lambda: {"tables": 0, "figures": 0})
    # ... other fields unchanged
```

### BaseAgent (from `agents/base.py`)
```python
class BaseAgent(ABC):
    agent_name: str = "base"
    agent_type: str = "base"

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState: ...
    def load_prompt(self, prompt_name: str) -> str: ...
    def call_claude(self, system, user, model=None, temperature=None, max_tokens=4096) -> tuple[str, dict]: ...
```

### SourceFinder.find() (from `pipeline/source_finder.py`)
```python
class SourceFinder:
    def __init__(self, config: dict): ...
    def find(
        self,
        topic: str,
        domain: str,
        language: str = "ru",
        stream_id: str = "",
        min_sources: int = 20,
        additional_sources: list[str] | None = None,
    ) -> SourceList: ...
```

### SECTION_ORDER (from `pipeline/generator.py`)
```python
SECTION_ORDER = {
    "vkr": ["title_page", "annotation", "toc", "introduction", "chapter_1", "chapter_2", "chapter_3", "conclusion", "references"],
    "coursework": ["title_page", "toc", "introduction", "chapter_1", "chapter_2", "conclusion", "references"],
    "research": ["annotation", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion", "references"],
    "abstract_paper": ["title_page", "toc", "introduction", "chapter_1", "conclusion", "references"],
    "text": ["full"],
    "essay": ["full"],
    "composition": ["full"],
}
```

### ContentQAGate.VIZ_MINIMUMS (from `agents/gates/content_qa.py`)
```python
VIZ_MINIMUMS: dict[str, dict[str, int]] = {
    "vkr": {"bachelor": 5, "master": 8, "specialist": 5, "postgraduate": 10},
    "coursework": {"default": 3},
    "research": {"default": 3},
    "abstract_paper": {"default": 1},
    "text": {"default": 0},
    "essay": {"default": 0},
    "composition": {"default": 0},
}
```
