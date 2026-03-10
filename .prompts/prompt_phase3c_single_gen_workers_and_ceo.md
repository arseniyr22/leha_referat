# Prompt 3C: Single-Generation Workers + CEO Integration

## Context

Phase 3A created `BaseSectionWorker` + MM orchestration upgrade.
Phase 3B created 30 multi-section workers for VKR/Coursework/Research/Abstract Paper.
Phase 3C is the **final part of Phase 3**: 6 single-generation workers for Text/Essay/Composition streams + CEO integration with ContentManager.

After Phase 3C, the entire content generation chain is complete:
`CEO → ContentManager → MicroManager → Worker → generator.py`

---

## Reference: Current Source State

### generator.py constants (DO NOT modify — reference only)

```python
# SECTION_ORDER for single-gen streams (lines 104-106):
"text": ["full"],
"essay": ["full"],
"composition": ["full"],

# REGISTER_MAP (lines 121-129):
"text": "journalistic",
"essay": "academic-essay",
"composition": "general",
```

`AcademicGenerator.generate_section("full", ...)` calls `self._generate_full(params, source_list)` internally. This is already implemented and works.

### BaseSectionWorker.execute() flow for section_id="full"

1. `section_id` is NOT in `("title_page", "toc")` → does NOT skip generation
2. Calls `self._call_generator(state)` → `generator.generate_section("full", ...)` → `_generate_full()`
3. Stores in `state.generated_sections["full"]`
4. Counts visualizations, appends to `state.text`

**This means standard workers with `section_id = "full"` work out of the box.** No execute() override needed.

### MicroManagerText (mm_text.py) — current state

```python
class MicroManagerText(BaseMicroManager):
    agent_name = "mm_text"
    STREAM_ID = "text"
    SECTION_ORDER = ["full"]
    VIZ_MINIMUMS = {"default": 0}
    DATA_HEAVY_SECTIONS = []

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

    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None

    async def execute(self, state: PipelineState) -> PipelineState:
        subtype = self._determine_subtype(state.domain)
        logger.info(...)
        state = await super().execute(state)
        return state

    def _determine_subtype(self, domain: str) -> str:
        return self.SUBTYPE_ROUTING.get(domain, "analytical")
```

Key: `execute()` calls `_determine_subtype()` THEN `super().execute()`. Inside `super().execute()`, `_get_worker("full")` is called. The subtype is computed but **not passed to `_get_worker()`**. This needs to change.

### MicroManagerEssay (mm_essay.py) — current state

```python
class MicroManagerEssay(BaseMicroManager):
    agent_name = "mm_essay"
    STREAM_ID = "essay"
    SECTION_ORDER = ["full"]
    VIZ_MINIMUMS = {"default": 0}
    DATA_HEAVY_SECTIONS = []

    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None
```

No custom execute(). No subtypes. Simple routing.

### MicroManagerComposition (mm_composition.py) — current state

```python
class MicroManagerComposition(BaseMicroManager):
    agent_name = "mm_composition"
    STREAM_ID = "composition"
    SECTION_ORDER = ["full"]
    VIZ_MINIMUMS = {"default": 0}
    DATA_HEAVY_SECTIONS = []

    def _get_worker(self, section_id: str):
        """Return worker for section_id. Phase 3A stub — workers in Prompt 3C."""
        return None
```

No custom execute(). No subtypes. Simple routing.

### ContentManager (manager.py) — current state

Already fully implemented. Routes to all 7 MMs via `MM_ROUTING`. Handles source discovery. **No modification needed in Phase 3C.**

### CEO._run_generation() — current state (NEEDS REWRITE)

```python
async def _run_generation(self, state: PipelineState) -> PipelineState:
    from pipeline import Pipeline
    from pipeline.generator import GenerationParams

    # Build GenerationParams from PipelineState
    params = GenerationParams(
        stream_id=state.stream_id,
        topic=state.topic,
        language=state.language,
        domain=state.domain,
        level=state.level,
        research_type=state.research_type,
        university=state.university,
    )

    pipe = Pipeline()
    output_text, score_report = pipe.run_from_params(
        params=params,
        verbose=True,
    )

    state.text = output_text
    state.final_score_report = score_report

    # Content QA gate
    state = await self._content_qa_check(state)

    # Feedback loop on humanization quality
    state = await self._feedback_loop(state)

    return state
```

Problem: calls `Pipeline.run_from_params()` directly — bypasses ContentManager → MM → Worker chain. Phase 3C replaces this with `ContentManager.execute()` for Phase 0, then `Pipeline.run()` for Stages 1-5.

### PipelineState — current fields (reference only, DO NOT modify)

```python
text_subtype: DOES NOT EXIST  # mm_text needs to store subtype somewhere
```

`PipelineState` does NOT have a `text_subtype` field. MicroManagerText must store the subtype internally (instance variable) rather than on state, to avoid modifying PipelineState.

---

## Part 1: Create 6 Single-Generation Workers

All 6 workers go in `agents/content/workers/`. All inherit `BaseSectionWorker`. All have `section_id = "full"`. None override `execute()` — the base flow handles everything.

### Naming convention

| Stream | Subtype | File | Class | agent_name |
|--------|---------|------|-------|------------|
| text | analytical | `text_analytical.py` | `TextAnalyticalWorker` | `text_analytical` |
| text | journalistic | `text_journalistic.py` | `TextJournalisticWorker` | `text_journalistic` |
| text | review | `text_review.py` | `TextReviewWorker` | `text_review` |
| text | descriptive | `text_descriptive.py` | `TextDescriptiveWorker` | `text_descriptive` |
| essay | — | `essay_full.py` | `EssayFullWorker` | `essay_full` |
| composition | — | `comp_full.py` | `CompositionFullWorker` | `comp_full` |

### File 1: `agents/content/workers/text_analytical.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextAnalyticalWorker(BaseSectionWorker):
    """
    Text stream worker — analytical subtype.

    Generates data-driven analytical text in one API call.
    Used when domain is it_cs, economics, law, psychology, or general.
    """

    section_id = "full"
    agent_name = "text_analytical"
```

### File 2: `agents/content/workers/text_journalistic.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextJournalisticWorker(BaseSectionWorker):
    """
    Text stream worker — journalistic subtype.

    Generates news/feature article style text in one API call.
    Used when domain is media or journalistic.
    """

    section_id = "full"
    agent_name = "text_journalistic"
```

### File 3: `agents/content/workers/text_review.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextReviewWorker(BaseSectionWorker):
    """
    Text stream worker — review subtype.

    Generates literature/product/topic review text in one API call.
    Used when explicitly requested (not auto-routed by domain).
    """

    section_id = "full"
    agent_name = "text_review"
```

### File 4: `agents/content/workers/text_descriptive.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class TextDescriptiveWorker(BaseSectionWorker):
    """
    Text stream worker — descriptive subtype.

    Generates factual descriptive/informational text in one API call.
    Used when domain is humanities.
    """

    section_id = "full"
    agent_name = "text_descriptive"
```

### File 5: `agents/content/workers/essay_full.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class EssayFullWorker(BaseSectionWorker):
    """
    Essay stream worker.

    Generates the full essay in one API call.
    Register: academic-essay (from REGISTER_MAP).
    """

    section_id = "full"
    agent_name = "essay_full"
```

### File 6: `agents/content/workers/comp_full.py`

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CompositionFullWorker(BaseSectionWorker):
    """
    Composition (Сочинение) stream worker.

    Generates the full composition in one API call.
    Register: general (from REGISTER_MAP).
    """

    section_id = "full"
    agent_name = "comp_full"
```

---

## Part 2: Update 3 MicroManagers

### File 7: MODIFY `agents/content/micro_managers/mm_text.py`

This is the most complex MM update because of subtype routing.

**Design decision**: `_get_worker()` is called by `BaseMicroManager.execute()` with only `section_id` as argument. We cannot change the `_get_worker(section_id)` signature because it's defined in `BaseMicroManager` base class and used by all 7 MMs. Instead, `MicroManagerText.execute()` stores the determined subtype as `self._current_subtype` before calling `super().execute()`, and `_get_worker()` reads `self._current_subtype`.

**Full replacement** of `agents/content/micro_managers/mm_text.py`:

```python
from __future__ import annotations

from loguru import logger

from agents.content.micro_managers.base import BaseMicroManager
from agents.state import PipelineState


class MicroManagerText(BaseMicroManager):
    """
    Micro Manager for Text (Текст).

    Single-generation stream: SECTION_ORDER = ["full"]
    Routes to subtype-specific worker based on domain.

    4 subtypes (determined by domain):
    - analytical: data-driven analysis, opinion with evidence
    - journalistic: news/feature article style
    - review: literature/product/topic review
    - descriptive: factual description, informational

    Subtype selection (from SUBTYPE_ROUTING):
    - domain "media" or "journalistic" → journalistic
    - domain "it_cs", "economics", "law", "psychology" → analytical
    - domain "humanities" → descriptive
    - default → analytical

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

        # Base execute handles: _get_worker("full") → worker.execute(state)
        state = await super().execute(state)

        return state

    def _determine_subtype(self, domain: str) -> str:
        """
        Determine text subtype from domain.

        Returns one of: analytical, journalistic, review, descriptive
        """
        return self.SUBTYPE_ROUTING.get(domain, "analytical")
```

**Changes vs current mm_text.py:**
1. Added `__init__` with `self._current_subtype: str = "analytical"`
2. Replaced `_get_worker()` stub → real routing by `self._current_subtype`
3. `execute()`: stores subtype in `self._current_subtype` before `super().execute()`
4. All class constants (SECTION_ORDER, VIZ_MINIMUMS, DATA_HEAVY_SECTIONS, SUBTYPE_ROUTING) unchanged
5. `_determine_subtype()` unchanged

### File 8: MODIFY `agents/content/micro_managers/mm_essay.py`

**Full replacement** of `agents/content/micro_managers/mm_essay.py`:

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerEssay(BaseMicroManager):
    """
    Micro Manager for Essay (Эссе).

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker that calls generator.generate_section("full", ...)
    for the full essay in one API call.

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

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        if section_id != "full":
            return None

        from agents.content.workers.essay_full import EssayFullWorker

        return EssayFullWorker()
```

**Changes vs current mm_essay.py:**
1. Replaced `_get_worker()` stub → real routing to `EssayFullWorker`
2. Guard: returns None for any section_id other than "full"
3. Import inside method (same pattern as Phase 3B MMs)
4. All class constants unchanged

### File 9: MODIFY `agents/content/micro_managers/mm_composition.py`

**Full replacement** of `agents/content/micro_managers/mm_composition.py`:

```python
from __future__ import annotations

from agents.content.micro_managers.base import BaseMicroManager


class MicroManagerComposition(BaseMicroManager):
    """
    Micro Manager for Composition (Сочинение).

    Single-generation stream: SECTION_ORDER = ["full"]
    Uses one worker that calls generator.generate_section("full", ...)
    for the full composition in one API call.

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

    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        if section_id != "full":
            return None

        from agents.content.workers.comp_full import CompositionFullWorker

        return CompositionFullWorker()
```

**Changes vs current mm_composition.py:**
1. Replaced `_get_worker()` stub → real routing to `CompositionFullWorker`
2. Guard: returns None for any section_id other than "full"
3. Import inside method
4. All class constants unchanged

---

## Part 3: CEO Integration

### File 10: MODIFY `agents/ceo.py`

**Replace ONLY the `_run_generation()` method.** All other methods (`execute()`, `_run_humanization()`, `_feedback_loop()`, `_determine_feedback_route()`, `_get_failed_metrics()`, `_content_qa_check()`) remain UNCHANGED.

**Old `_run_generation()` (lines 78-118 of ceo.py):**

```python
async def _run_generation(self, state: PipelineState) -> PipelineState:
    from pipeline import Pipeline
    from pipeline.generator import GenerationParams

    logger.info("[CEO] Generation mode: Phase 0 → Stages 1-5")

    params = GenerationParams(
        stream_id=state.stream_id,
        topic=state.topic,
        language=state.language,
        domain=state.domain,
        level=state.level,
        research_type=state.research_type,
        university=state.university,
    )

    pipe = Pipeline()
    output_text, score_report = pipe.run_from_params(
        params=params,
        verbose=True,
    )

    state.text = output_text
    state.final_score_report = score_report

    state = await self._content_qa_check(state)
    state = await self._feedback_loop(state)

    return state
```

**New `_run_generation()`:**

```python
async def _run_generation(self, state: PipelineState) -> PipelineState:
    """
    Generation mode: Phase 0 (ContentManager) → Stages 1-5 (Pipeline).

    Steps:
    1. ContentManager.execute(state) — runs Phase 0A (sources) + Phase 0B (generation)
       via MicroManager → Worker → generator.py chain
    2. Content QA gate — validates Phase 0 output
    3. Pipeline.run(state.text) — runs Stages 1-5 (humanization)
    4. Feedback loop — re-run if score fails
    """
    from pipeline import Pipeline
    from agents.content.manager import ContentManager

    logger.info("[CEO] Generation mode: ContentManager → Stages 1-5")

    # Step 1: Phase 0 via ContentManager → MM → Worker
    content_manager = ContentManager()
    state = await content_manager.execute(state)

    if not state.text:
        state.add_error(self.agent_name, "ContentManager produced no text")
        return state

    logger.info(
        f"[CEO] Phase 0 complete | words={state.word_count()} | "
        f"sections={len(state.generated_sections)} | "
        f"sources={len(state.source_list.sources) if state.source_list and hasattr(state.source_list, 'sources') else 0}"
    )

    # Step 2: Content QA gate
    state = await self._content_qa_check(state)

    # Step 3: Stages 1-5 (humanization) via Pipeline
    pipe = Pipeline()
    pipe._current_language = state.language

    output_text, score_report = pipe.run(
        text=state.text,
        verbose=True,
        domain_override=state.domain if state.domain != "general" else None,
        register_override=state.register if state.register != "general" else None,
    )

    state.text = output_text
    state.final_score_report = score_report

    # Step 4: Feedback loop
    state = await self._feedback_loop(state)

    return state
```

**Changes vs current ceo.py `_run_generation()`:**
1. Removed `GenerationParams` import — no longer needed (ContentManager builds it internally via workers)
2. Added `ContentManager` import
3. Phase 0: `content_manager.execute(state)` replaces `pipe.run_from_params(params)`
4. Added null check: `if not state.text` after ContentManager
5. Added logging of Phase 0 results
6. Content QA gate moved BEFORE Pipeline.run() (was after `run_from_params` which included stages 1-5; now correctly placed between Phase 0 and Stages 1-5)
7. Stages 1-5: uses `pipe.run(text=state.text)` — same pattern as existing `_run_humanization()`
8. Feedback loop remains last step

**What NOT to change in ceo.py:**
- `execute()` method — unchanged
- `_run_humanization()` method — unchanged
- `_feedback_loop()` method — unchanged
- `_determine_feedback_route()` method — unchanged
- `_get_failed_metrics()` method — unchanged
- `_content_qa_check()` method — unchanged
- `MAX_FEEDBACK_ITERATIONS` constant — unchanged
- All imports at top of file — unchanged (add no new top-level imports)

---

## Part 4: Test File

### File 11: CREATE `tests/test_phase3c_single_gen_and_ceo.py`

```python
"""
Phase 3C Tests: Single-Generation Workers + CEO Integration.
Run: pytest tests/test_phase3c_single_gen_and_ceo.py -v

Tests:
1. All 6 single-gen workers instantiate correctly
2. All workers have section_id = "full"
3. All workers have correct agent_name
4. All workers inherit from BaseSectionWorker
5. MM routing: mm_text subtype → correct worker class
6. MM routing: mm_essay → EssayFullWorker
7. MM routing: mm_composition → CompositionFullWorker
8. MM routing: all 3 MMs return None for unknown section_id
9. MicroManagerText subtype routing by domain
10. MicroManagerText._current_subtype set before worker dispatch
11. CEO._run_generation uses ContentManager (not Pipeline.run_from_params)
12. CEO._run_humanization unchanged (still uses Pipeline.run)
13. Phase 3A regression: BaseSectionWorker still works
14. Phase 3B regression: multi-section worker count = 30
15. Phase 2 regression: ContentManager routing still works for all 7 streams
"""
from __future__ import annotations

import asyncio
import inspect

import pytest


# ── Test 1: Single-Gen Worker Instantiation ─────────────────────────


class TestSingleGenWorkers:
    def test_all_workers_instantiate(self):
        """All 6 single-gen workers instantiate without error."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        workers = [
            TextAnalyticalWorker(),
            TextJournalisticWorker(),
            TextReviewWorker(),
            TextDescriptiveWorker(),
            EssayFullWorker(),
            CompositionFullWorker(),
        ]
        assert len(workers) == 6
        for w in workers:
            assert w.agent_type == "worker"

    def test_all_section_ids_are_full(self):
        """All single-gen workers have section_id = 'full'."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        for cls in [
            TextAnalyticalWorker,
            TextJournalisticWorker,
            TextReviewWorker,
            TextDescriptiveWorker,
            EssayFullWorker,
            CompositionFullWorker,
        ]:
            w = cls()
            assert w.section_id == "full", f"{cls.__name__}.section_id = {w.section_id!r}, expected 'full'"

    def test_agent_names(self):
        """All single-gen workers have correct agent_name."""
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        expected = {
            TextAnalyticalWorker: "text_analytical",
            TextJournalisticWorker: "text_journalistic",
            TextReviewWorker: "text_review",
            TextDescriptiveWorker: "text_descriptive",
            EssayFullWorker: "essay_full",
            CompositionFullWorker: "comp_full",
        }
        for cls, name in expected.items():
            w = cls()
            assert w.agent_name == name, f"{cls.__name__}.agent_name = {w.agent_name!r}, expected {name!r}"

    def test_all_inherit_base_section_worker(self):
        """All single-gen workers inherit from BaseSectionWorker."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_review import TextReviewWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker
        from agents.content.workers.essay_full import EssayFullWorker
        from agents.content.workers.comp_full import CompositionFullWorker

        for cls in [
            TextAnalyticalWorker,
            TextJournalisticWorker,
            TextReviewWorker,
            TextDescriptiveWorker,
            EssayFullWorker,
            CompositionFullWorker,
        ]:
            w = cls()
            assert isinstance(w, BaseSectionWorker), f"{cls.__name__} does not inherit BaseSectionWorker"


# ── Test 2: MM Routing ──────────────────────────────────────────────


class TestMMRouting:
    def test_text_mm_subtype_analytical(self):
        """MicroManagerText routes analytical subtype to TextAnalyticalWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker

        mm = MicroManagerText()
        mm._current_subtype = "analytical"
        w = mm._get_worker("full")
        assert isinstance(w, TextAnalyticalWorker)

    def test_text_mm_subtype_journalistic(self):
        """MicroManagerText routes journalistic subtype to TextJournalisticWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_journalistic import TextJournalisticWorker

        mm = MicroManagerText()
        mm._current_subtype = "journalistic"
        w = mm._get_worker("full")
        assert isinstance(w, TextJournalisticWorker)

    def test_text_mm_subtype_review(self):
        """MicroManagerText routes review subtype to TextReviewWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_review import TextReviewWorker

        mm = MicroManagerText()
        mm._current_subtype = "review"
        w = mm._get_worker("full")
        assert isinstance(w, TextReviewWorker)

    def test_text_mm_subtype_descriptive(self):
        """MicroManagerText routes descriptive subtype to TextDescriptiveWorker."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_descriptive import TextDescriptiveWorker

        mm = MicroManagerText()
        mm._current_subtype = "descriptive"
        w = mm._get_worker("full")
        assert isinstance(w, TextDescriptiveWorker)

    def test_text_mm_unknown_subtype_falls_back(self):
        """MicroManagerText falls back to TextAnalyticalWorker for unknown subtype."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker

        mm = MicroManagerText()
        mm._current_subtype = "nonexistent"
        w = mm._get_worker("full")
        assert isinstance(w, TextAnalyticalWorker)

    def test_text_mm_returns_none_for_unknown_section(self):
        """MicroManagerText returns None for unknown section_id."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("introduction") is None
        assert mm._get_worker("nonexistent") is None

    def test_essay_mm_returns_correct_worker(self):
        """MicroManagerEssay routes 'full' to EssayFullWorker."""
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.workers.essay_full import EssayFullWorker

        mm = MicroManagerEssay()
        w = mm._get_worker("full")
        assert isinstance(w, EssayFullWorker)

    def test_essay_mm_returns_none_for_unknown_section(self):
        """MicroManagerEssay returns None for unknown section_id."""
        from agents.content.micro_managers.mm_essay import MicroManagerEssay

        mm = MicroManagerEssay()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("nonexistent") is None

    def test_composition_mm_returns_correct_worker(self):
        """MicroManagerComposition routes 'full' to CompositionFullWorker."""
        from agents.content.micro_managers.mm_composition import MicroManagerComposition
        from agents.content.workers.comp_full import CompositionFullWorker

        mm = MicroManagerComposition()
        w = mm._get_worker("full")
        assert isinstance(w, CompositionFullWorker)

    def test_composition_mm_returns_none_for_unknown_section(self):
        """MicroManagerComposition returns None for unknown section_id."""
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        mm = MicroManagerComposition()
        assert mm._get_worker("chapter_1") is None
        assert mm._get_worker("nonexistent") is None


# ── Test 3: Text Subtype Determination ──────────────────────────────


class TestTextSubtypeRouting:
    def test_domain_to_subtype_mapping(self):
        """MicroManagerText._determine_subtype returns correct subtype for each domain."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        expected = {
            "media": "journalistic",
            "journalistic": "journalistic",
            "it_cs": "analytical",
            "economics": "analytical",
            "law": "analytical",
            "psychology": "analytical",
            "humanities": "descriptive",
            "general": "analytical",
        }
        for domain, subtype in expected.items():
            assert mm._determine_subtype(domain) == subtype, (
                f"domain={domain!r}: expected {subtype!r}, got {mm._determine_subtype(domain)!r}"
            )

    def test_unknown_domain_defaults_to_analytical(self):
        """Unknown domain defaults to analytical subtype."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._determine_subtype("unknown_domain") == "analytical"
        assert mm._determine_subtype("") == "analytical"

    def test_current_subtype_initialized(self):
        """MicroManagerText._current_subtype is 'analytical' on init."""
        from agents.content.micro_managers.mm_text import MicroManagerText

        mm = MicroManagerText()
        assert mm._current_subtype == "analytical"

    def test_subtype_routing_all_domains_to_workers(self):
        """Full chain: domain → subtype → worker class (integration)."""
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.workers.text_analytical import TextAnalyticalWorker
        from agents.content.workers.text_journalistic import TextJournalisticWorker
        from agents.content.workers.text_descriptive import TextDescriptiveWorker

        mm = MicroManagerText()

        domain_to_worker = {
            "media": TextJournalisticWorker,
            "journalistic": TextJournalisticWorker,
            "it_cs": TextAnalyticalWorker,
            "economics": TextAnalyticalWorker,
            "law": TextAnalyticalWorker,
            "psychology": TextAnalyticalWorker,
            "humanities": TextDescriptiveWorker,
            "general": TextAnalyticalWorker,
        }

        for domain, expected_cls in domain_to_worker.items():
            mm._current_subtype = mm._determine_subtype(domain)
            w = mm._get_worker("full")
            assert isinstance(w, expected_cls), (
                f"domain={domain!r}: expected {expected_cls.__name__}, got {type(w).__name__}"
            )


# ── Test 4: CEO Integration ─────────────────────────────────────────


class TestCEOIntegration:
    def test_run_generation_uses_content_manager(self):
        """CEO._run_generation() calls ContentManager (not Pipeline.run_from_params)."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)

        # Must use ContentManager
        assert "ContentManager" in source, (
            "_run_generation must use ContentManager"
        )
        assert "content_manager" in source.lower() or "ContentManager()" in source, (
            "_run_generation must instantiate ContentManager"
        )

        # Must NOT use Pipeline.run_from_params
        assert "run_from_params" not in source, (
            "_run_generation must NOT call Pipeline.run_from_params (use ContentManager instead)"
        )

    def test_run_generation_still_calls_pipeline_run(self):
        """CEO._run_generation() still calls Pipeline.run() for Stages 1-5."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "pipe.run(" in source or "Pipeline()" in source, (
            "_run_generation must still use Pipeline.run() for Stages 1-5"
        )

    def test_run_generation_calls_content_qa(self):
        """CEO._run_generation() still calls _content_qa_check."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "_content_qa_check" in source, (
            "_run_generation must call _content_qa_check"
        )

    def test_run_generation_calls_feedback_loop(self):
        """CEO._run_generation() still calls _feedback_loop."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "_feedback_loop" in source, (
            "_run_generation must call _feedback_loop"
        )

    def test_run_humanization_unchanged(self):
        """CEO._run_humanization() still uses Pipeline.run() directly (no ContentManager)."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_humanization)
        assert "ContentManager" not in source, (
            "_run_humanization must NOT use ContentManager (humanization mode has no Phase 0)"
        )
        assert "pipe.run(" in source or "Pipeline()" in source, (
            "_run_humanization must use Pipeline.run()"
        )

    def test_ceo_feedback_loop_unchanged(self):
        """CEO._feedback_loop still has MAX_FEEDBACK_ITERATIONS = 2."""
        from agents.ceo import CEOAgent

        ceo = CEOAgent()
        assert ceo.MAX_FEEDBACK_ITERATIONS == 2

    def test_ceo_determine_feedback_route_unchanged(self):
        """CEO._determine_feedback_route still returns None for empty report."""
        from agents.ceo import CEOAgent

        ceo = CEOAgent()
        assert ceo._determine_feedback_route({}) is None
        assert ceo._determine_feedback_route(None) is None


# ── Test 5: Regression ──────────────────────────────────────────────


class TestPhase3CRegression:
    def test_base_section_worker_still_has_execute(self):
        """BaseSectionWorker still has execute() method."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        assert hasattr(BaseSectionWorker, "execute")

    def test_multi_section_worker_count_still_30(self):
        """Phase 3B: 30 multi-section workers still exist."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        total = 0
        for mm_cls in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_cls.__new__(mm_cls)
            for sid in mm_cls.SECTION_ORDER:
                w = mm._get_worker(sid)
                if w is not None:
                    total += 1
        assert total == 30, f"Expected 30 multi-section workers, got {total}"

    def test_content_manager_routes_all_7_streams(self):
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
        for stream_id, mm_cls in expected.items():
            mm = cm._get_micro_manager(stream_id)
            assert isinstance(mm, mm_cls), (
                f"stream_id={stream_id!r}: expected {mm_cls.__name__}, got {type(mm).__name__}"
            )

    def test_total_worker_count_is_36(self):
        """Total worker count across all 7 MMs = 36 (30 multi + 6 single)."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        total = 0

        # Multi-section MMs
        for mm_cls in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_cls.__new__(mm_cls)
            for sid in mm_cls.SECTION_ORDER:
                w = mm._get_worker(sid)
                if w is not None:
                    total += 1

        # Single-gen MMs: each returns 1 worker for "full"
        # mm_text: 1 worker (depends on subtype, but always 1)
        mm_text = MicroManagerText()
        w = mm_text._get_worker("full")
        if w is not None:
            total += 1

        mm_essay = MicroManagerEssay()
        w = mm_essay._get_worker("full")
        if w is not None:
            total += 1

        mm_comp = MicroManagerComposition()
        w = mm_comp._get_worker("full")
        if w is not None:
            total += 1

        # 30 multi + 3 single-gen MM slots = 33
        # But mm_text has 4 subtypes that route to 4 different workers.
        # At runtime only 1 is used per invocation. The count is "active slots" not "unique classes".
        # 30 + 1 (text, any subtype) + 1 (essay) + 1 (composition) = 33 active slots
        # However from unique worker FILE perspective: 30 + 6 = 36 files.
        # This test counts active routing slots (33).
        assert total == 33, f"Expected 33 active worker slots, got {total}"

    def test_unique_worker_file_count_is_36(self):
        """36 unique worker files exist (30 multi-section + 6 single-gen)."""
        import importlib
        import pkgutil

        import agents.content.workers as workers_pkg

        worker_modules = []
        for importer, modname, ispkg in pkgutil.iter_modules(workers_pkg.__path__):
            if modname.startswith("__") or modname == "base_section_worker":
                continue
            worker_modules.append(modname)

        assert len(worker_modules) == 36, (
            f"Expected 36 worker modules (30 multi + 6 single), "
            f"got {len(worker_modules)}: {sorted(worker_modules)}"
        )

    def test_section_orders_still_match_generator(self):
        """All MM SECTION_ORDERs still match pipeline/generator.py."""
        from pipeline.generator import SECTION_ORDER as GEN_ORDER
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from agents.content.micro_managers.mm_text import MicroManagerText
        from agents.content.micro_managers.mm_essay import MicroManagerEssay
        from agents.content.micro_managers.mm_composition import MicroManagerComposition

        assert MicroManagerVKR.SECTION_ORDER == GEN_ORDER["vkr"]
        assert MicroManagerCoursework.SECTION_ORDER == GEN_ORDER["coursework"]
        assert MicroManagerResearch.SECTION_ORDER == GEN_ORDER["research"]
        assert MicroManagerAbstractPaper.SECTION_ORDER == GEN_ORDER["abstract_paper"]
        assert MicroManagerText.SECTION_ORDER == GEN_ORDER["text"]
        assert MicroManagerEssay.SECTION_ORDER == GEN_ORDER["essay"]
        assert MicroManagerComposition.SECTION_ORDER == GEN_ORDER["composition"]
```

---

## Part 5: Update Existing Test (Phase 2 Regression Fix)

### File 12: MODIFY `tests/test_phase2_content.py`

**Problem**: `test_text_execute_stub` (line ~480) asserts `assert not result.has_errors()`. In Phase 2, `_get_worker("full")` returned `None` → worker skipped → no API call → no error. After Phase 3C, `_get_worker("full")` returns a real worker → worker calls `generator.generate_section()` → API call fails without API key → `state.add_error(...)`.

The VKR equivalent (`test_vkr_execute_runs_workers`, line ~459) was already updated in Phase 3B to expect API errors. Apply the same pattern to the text test.

**Old test (lines ~480-493):**

```python
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
```

**New test:**

```python
def test_text_execute_runs_workers(self):
    """Text MM executes worker (errors expected without API key)."""
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
    # Worker tries to call Claude API — error expected in test env (no API key)
    # Verify: "full" section was attempted (key exists even if generation failed)
    assert "full" in result.generated_sections or result.has_errors()
```

**Changes:**
1. Renamed: `test_text_execute_stub` → `test_text_execute_runs_workers`
2. Docstring updated to match Phase 3C reality
3. Assertion: no longer expects zero errors; instead verifies the worker was dispatched (either section exists or error was logged)

---

## Summary of All Changes

| Action | Count | Files |
|--------|-------|-------|
| CREATE | 6 | `agents/content/workers/{text_analytical,text_journalistic,text_review,text_descriptive,essay_full,comp_full}.py` |
| CREATE | 1 | `tests/test_phase3c_single_gen_and_ceo.py` |
| MODIFY | 3 | `agents/content/micro_managers/{mm_text,mm_essay,mm_composition}.py` |
| MODIFY | 1 | `agents/ceo.py` (only `_run_generation()` method) |
| MODIFY | 1 | `tests/test_phase2_content.py` (only `test_text_execute_stub` → `test_text_execute_runs_workers`) |

**Total: 7 new files, 5 modified files.**

---

## Critical Constraints

1. **DO NOT modify**: `base_section_worker.py`, `base.py` (BaseMicroManager), `generator.py`, `state.py`, `manager.py`, `handoff_gate.py`, `content_qa.py`
2. **DO NOT modify**: any Phase 3B worker files (vkr_*, cw_*, res_*, ap_*)
3. **DO NOT modify**: mm_vkr.py, mm_coursework.py, mm_research.py, mm_abstract_paper.py
4. **In ceo.py**: modify ONLY `_run_generation()`. All other methods unchanged.
5. **In mm_text.py**: preserve all class constants (SECTION_ORDER, VIZ_MINIMUMS, DATA_HEAVY_SECTIONS, SUBTYPE_ROUTING). Only change `__init__`, `_get_worker()`, and `execute()`.
6. **Imports inside methods** to avoid circular imports (same pattern as Phase 3B).
7. **No new fields on PipelineState** — subtype stored as `self._current_subtype` on MicroManagerText instance.
8. **In test_phase2_content.py**: modify ONLY the `test_text_execute_stub` test method (rename + update assertion). All other tests unchanged.

---

## Verification

```bash
# Phase 3C tests
pytest tests/test_phase3c_single_gen_and_ceo.py -v

# Phase 3B regression
pytest tests/test_phase3b_multi_section_workers.py -v

# Phase 3A regression
pytest tests/test_phase3a_base_worker.py -v

# Phase 2 regression
pytest tests/test_phase2_content.py -v

# Phase 1 regression
pytest tests/test_phase1_ceo.py -v

# Full agent test suite
pytest tests/ -v --tb=short
```

All tests must pass with 0 failures (excluding pre-existing spacy-related failures in test_pipeline.py).
