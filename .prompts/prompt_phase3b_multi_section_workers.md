# Phase 3B: Multi-Section Workers (VKR, Coursework, Research, Abstract Paper)

## Overview

Phase 3B creates 30 concrete workers for the 4 multi-section streams and wires them into their MicroManagers. After this phase, all multi-section generation flows have real workers that call `AcademicGenerator.generate_section()`.

**What this prompt does:**
1. Creates 9 VKR workers (including TOC worker with `execute_pass_2()`)
2. Creates 7 Coursework workers (shares TOC worker pattern from VKR)
3. Creates 8 Research workers (no TOC — research has no `toc` in SECTION_ORDER)
4. Creates 6 Abstract Paper workers (shares TOC worker pattern from VKR)
5. **Replaces** `_get_worker()` in 4 concrete MMs to return real workers
6. Creates comprehensive tests

**Principle**: Workers are thin. Every worker inherits `BaseSectionWorker` and sets exactly two class attributes: `section_id` and `agent_name`. The base class handles ALL logic: calling generator, storing results, counting visualizations, updating state.

**Only 3 worker types have custom behavior:**
- **TOC workers** — override `execute()` to store placeholder + implement `execute_pass_2()` for real TOC
- **Title page workers** — standard (BaseSectionWorker.execute() already returns "" for title_page)
- **References workers** — standard (AcademicGenerator.generate_section("references") already formats source list)

**NO modifications to any existing files except the 4 MM `_get_worker()` methods.**

---

## Files to Create (30 new worker files + 1 test file)

```
# VKR workers (9 files)
agents/content/workers/vkr_title_page.py
agents/content/workers/vkr_annotation.py
agents/content/workers/vkr_toc.py              # Has execute_pass_2()
agents/content/workers/vkr_introduction.py
agents/content/workers/vkr_chapter_1.py
agents/content/workers/vkr_chapter_2.py
agents/content/workers/vkr_chapter_3.py
agents/content/workers/vkr_conclusion.py
agents/content/workers/vkr_references.py

# Coursework workers (7 files)
agents/content/workers/cw_title_page.py
agents/content/workers/cw_toc.py                # Has execute_pass_2()
agents/content/workers/cw_introduction.py
agents/content/workers/cw_chapter_1.py
agents/content/workers/cw_chapter_2.py
agents/content/workers/cw_conclusion.py
agents/content/workers/cw_references.py

# Research workers (8 files)
agents/content/workers/res_annotation.py
agents/content/workers/res_introduction.py
agents/content/workers/res_literature_review.py
agents/content/workers/res_methodology.py
agents/content/workers/res_results.py
agents/content/workers/res_discussion.py
agents/content/workers/res_conclusion.py
agents/content/workers/res_references.py

# Abstract Paper workers (6 files)
agents/content/workers/ap_title_page.py
agents/content/workers/ap_toc.py                # Has execute_pass_2()
agents/content/workers/ap_introduction.py
agents/content/workers/ap_chapter_1.py
agents/content/workers/ap_conclusion.py
agents/content/workers/ap_references.py

# Tests (1 file)
tests/test_phase3b_multi_section_workers.py
```

## Files to Modify (4 existing MM files)

```
agents/content/micro_managers/mm_vkr.py              # Replace _get_worker() stub
agents/content/micro_managers/mm_coursework.py        # Replace _get_worker() stub
agents/content/micro_managers/mm_research.py          # Replace _get_worker() stub
agents/content/micro_managers/mm_abstract_paper.py    # Replace _get_worker() stub
```

---

## SECTION_ORDER Reference (from `pipeline/generator.py` — DO NOT deviate)

These are the authoritative section lists. Every MM's `_get_worker()` must return a worker for each section_id in its SECTION_ORDER.

```python
# VKR: 9 sections
["title_page", "annotation", "toc", "introduction", "chapter_1", "chapter_2", "chapter_3", "conclusion", "references"]

# Coursework: 7 sections
["title_page", "toc", "introduction", "chapter_1", "chapter_2", "conclusion", "references"]

# Research: 8 sections
["annotation", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion", "references"]

# Abstract Paper: 6 sections
["title_page", "toc", "introduction", "chapter_1", "conclusion", "references"]
```

---

## Worker Naming Convention

Every worker follows this naming pattern:

| Stream | Prefix | Example file | Example class | agent_name |
|---|---|---|---|---|
| VKR | `vkr_` | `vkr_introduction.py` | `VKRIntroductionWorker` | `"vkr_introduction"` |
| Coursework | `cw_` | `cw_introduction.py` | `CWIntroductionWorker` | `"cw_introduction"` |
| Research | `res_` | `res_methodology.py` | `ResMethodologyWorker` | `"res_methodology"` |
| Abstract Paper | `ap_` | `ap_introduction.py` | `APIntroductionWorker` | `"ap_introduction"` |

---

## Standard Worker Template

ALL workers except TOC workers follow this exact pattern. Copy it precisely, only changing the class name, `section_id`, and `agent_name`.

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRIntroductionWorker(BaseSectionWorker):
    """
    VKR Introduction section worker.

    Generates the introduction by calling AcademicGenerator.generate_section("introduction").
    All generation logic lives in BaseSectionWorker.execute().
    """

    section_id = "introduction"
    agent_name = "vkr_introduction"
```

That is the ENTIRE file. No additional methods, no imports beyond `BaseSectionWorker`, no custom logic. The base class does everything.

---

## TOC Worker Template (3 files: `vkr_toc.py`, `cw_toc.py`, `ap_toc.py`)

TOC workers are the ONLY workers with custom behavior. They:
1. In `execute()` (Pass 1): store empty string placeholder (BaseSectionWorker already handles this — `section_id="toc"` is format-only)
2. Add `execute_pass_2()`: build real TOC from `state.generated_sections` after all sections are generated

The `execute_pass_2()` method is called by `BaseMicroManager.execute()` after the worker loop completes (see `base.py` lines 97-100).

### TOC Worker — VKR version (`vkr_toc.py`)

```python
from __future__ import annotations

from loguru import logger

from agents.content.workers.base_section_worker import BaseSectionWorker
from agents.state import PipelineState


class VKRTOCWorker(BaseSectionWorker):
    """
    VKR Table of Contents worker (2-pass).

    Pass 1 (execute): BaseSectionWorker stores empty string for "toc" (format-only).
    Pass 2 (execute_pass_2): Builds TOC from state.generated_sections headings.

    The TOC is a text representation for the generated document.
    The actual formatted TOC in .docx is handled by formatter.py.
    This text TOC serves as:
    - A structural reference for the humanization pipeline
    - Content for state.text so the full document is readable as plain text
    """

    section_id = "toc"
    agent_name = "vkr_toc"

    # Section IDs that appear in TOC (exclude title_page, toc itself, references)
    # Must match the VKR SECTION_ORDER minus non-TOC items
    TOC_SECTIONS = [
        "annotation",
        "introduction",
        "chapter_1",
        "chapter_2",
        "chapter_3",
        "conclusion",
    ]

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        """
        Build TOC from generated section headings (called after all sections generated).

        Extracts the first ## heading from each generated section to build a
        plain-text table of contents. Stores result in state.generated_sections["toc"]
        and prepends to state.text at the correct position.

        Uses SECTION_NAMES from pipeline/generator.py for fallback names.
        """
        from pipeline.generator import SECTION_NAMES_RU, SECTION_NAMES_EN

        section_names = SECTION_NAMES_RU if state.language == "ru" else SECTION_NAMES_EN
        toc_title = "Оглавление" if state.language == "ru" else "Table of Contents"

        toc_lines: list[str] = [f"## {toc_title}", ""]

        for section_id in self.TOC_SECTIONS:
            section_text = state.generated_sections.get(section_id, "")
            heading = self._extract_heading(section_text)

            if not heading:
                # Fallback to standard section name
                heading = section_names.get(section_id, section_id.replace("_", " ").title())

            toc_lines.append(f"- {heading}")

        # Always add references at the end
        ref_name = section_names.get("references", "References")
        toc_lines.append(f"- {ref_name}")

        toc_text = "\n".join(toc_lines)

        # Update state
        state.generated_sections["toc"] = toc_text

        # Insert TOC into state.text after title_page placeholder (if exists) or at beginning
        # The TOC was originally stored as "" — replace it
        old_toc = ""
        if old_toc in state.text and state.text.startswith(old_toc):
            # TOC placeholder is at the start or after title_page
            # Simply prepend TOC text
            pass

        # Safer approach: append TOC text to state.text
        # (formatter.py will handle actual document ordering based on generated_sections)
        if toc_text:
            state.text = toc_text + "\n\n" + state.text

        logger.info(
            f"[{self.agent_name}] TOC Pass 2 complete | "
            f"{len(self.TOC_SECTIONS) + 1} entries"
        )

        return state

    @staticmethod
    def _extract_heading(section_text: str) -> str:
        """
        Extract the first markdown heading from section text.

        Looks for ## or ### at the start of a line.
        Returns the heading text without the ## prefix, or empty string if not found.
        """
        if not section_text:
            return ""

        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()

        return ""
```

### TOC Worker — Coursework version (`cw_toc.py`)

```python
from __future__ import annotations

from loguru import logger

from agents.content.workers.base_section_worker import BaseSectionWorker
from agents.state import PipelineState


class CWTOCWorker(BaseSectionWorker):
    """
    Coursework Table of Contents worker (2-pass).

    Same pattern as VKRTOCWorker but with coursework-specific TOC_SECTIONS.
    """

    section_id = "toc"
    agent_name = "cw_toc"

    # Coursework TOC: no annotation, no chapter_3
    TOC_SECTIONS = [
        "introduction",
        "chapter_1",
        "chapter_2",
        "conclusion",
    ]

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        """Build TOC from generated section headings."""
        from pipeline.generator import SECTION_NAMES_RU, SECTION_NAMES_EN

        section_names = SECTION_NAMES_RU if state.language == "ru" else SECTION_NAMES_EN
        toc_title = "Оглавление" if state.language == "ru" else "Table of Contents"

        toc_lines: list[str] = [f"## {toc_title}", ""]

        for section_id in self.TOC_SECTIONS:
            section_text = state.generated_sections.get(section_id, "")
            heading = self._extract_heading(section_text)
            if not heading:
                heading = section_names.get(section_id, section_id.replace("_", " ").title())
            toc_lines.append(f"- {heading}")

        ref_name = section_names.get("references", "References")
        toc_lines.append(f"- {ref_name}")

        toc_text = "\n".join(toc_lines)
        state.generated_sections["toc"] = toc_text

        if toc_text:
            state.text = toc_text + "\n\n" + state.text

        logger.info(
            f"[{self.agent_name}] TOC Pass 2 complete | "
            f"{len(self.TOC_SECTIONS) + 1} entries"
        )
        return state

    @staticmethod
    def _extract_heading(section_text: str) -> str:
        """Extract the first markdown heading from section text."""
        if not section_text:
            return ""
        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()
        return ""
```

### TOC Worker — Abstract Paper version (`ap_toc.py`)

```python
from __future__ import annotations

from loguru import logger

from agents.content.workers.base_section_worker import BaseSectionWorker
from agents.state import PipelineState


class APTOCWorker(BaseSectionWorker):
    """
    Abstract Paper Table of Contents worker (2-pass).

    Same pattern as VKRTOCWorker but with abstract_paper-specific TOC_SECTIONS.
    """

    section_id = "toc"
    agent_name = "ap_toc"

    # Abstract Paper TOC: intro, chapter_1, conclusion
    TOC_SECTIONS = [
        "introduction",
        "chapter_1",
        "conclusion",
    ]

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        """Build TOC from generated section headings."""
        from pipeline.generator import SECTION_NAMES_RU, SECTION_NAMES_EN

        section_names = SECTION_NAMES_RU if state.language == "ru" else SECTION_NAMES_EN
        toc_title = "Оглавление" if state.language == "ru" else "Table of Contents"

        toc_lines: list[str] = [f"## {toc_title}", ""]

        for section_id in self.TOC_SECTIONS:
            section_text = state.generated_sections.get(section_id, "")
            heading = self._extract_heading(section_text)
            if not heading:
                heading = section_names.get(section_id, section_id.replace("_", " ").title())
            toc_lines.append(f"- {heading}")

        ref_name = section_names.get("references", "References")
        toc_lines.append(f"- {ref_name}")

        toc_text = "\n".join(toc_lines)
        state.generated_sections["toc"] = toc_text

        if toc_text:
            state.text = toc_text + "\n\n" + state.text

        logger.info(
            f"[{self.agent_name}] TOC Pass 2 complete | "
            f"{len(self.TOC_SECTIONS) + 1} entries"
        )
        return state

    @staticmethod
    def _extract_heading(section_text: str) -> str:
        """Extract the first markdown heading from section text."""
        if not section_text:
            return ""
        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()
        return ""
```

---

## All 30 Workers — Complete Specification

### VKR Workers (9 files)

**File: `agents/content/workers/vkr_title_page.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRTitlePageWorker(BaseSectionWorker):
    """
    VKR Title Page worker.

    Format-only section: BaseSectionWorker.execute() returns empty string
    for section_id="title_page". Actual title page is built by formatter.py.
    """

    section_id = "title_page"
    agent_name = "vkr_title_page"
```

**File: `agents/content/workers/vkr_annotation.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRAnnotationWorker(BaseSectionWorker):
    """
    VKR Annotation (Abstract) section worker.

    Generates annotation by calling AcademicGenerator.generate_section("annotation").
    """

    section_id = "annotation"
    agent_name = "vkr_annotation"
```

**File: `agents/content/workers/vkr_toc.py`** — see TOC Worker Template above

**File: `agents/content/workers/vkr_introduction.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRIntroductionWorker(BaseSectionWorker):
    """
    VKR Introduction section worker.

    Generates introduction by calling AcademicGenerator.generate_section("introduction").
    """

    section_id = "introduction"
    agent_name = "vkr_introduction"
```

**File: `agents/content/workers/vkr_chapter_1.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter1Worker(BaseSectionWorker):
    """
    VKR Chapter 1 (theoretical framework / literature review) worker.

    Generates chapter_1 by calling AcademicGenerator.generate_section("chapter_1").
    """

    section_id = "chapter_1"
    agent_name = "vkr_chapter_1"
```

**File: `agents/content/workers/vkr_chapter_2.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter2Worker(BaseSectionWorker):
    """
    VKR Chapter 2 (empirical results / data analysis) worker.

    Generates chapter_2 by calling AcademicGenerator.generate_section("chapter_2").
    This is a DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_2"
    agent_name = "vkr_chapter_2"
```

**File: `agents/content/workers/vkr_chapter_3.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRChapter3Worker(BaseSectionWorker):
    """
    VKR Chapter 3 (practical application / recommendations) worker.

    Generates chapter_3 by calling AcademicGenerator.generate_section("chapter_3").
    This is a DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_3"
    agent_name = "vkr_chapter_3"
```

**File: `agents/content/workers/vkr_conclusion.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRConclusionWorker(BaseSectionWorker):
    """
    VKR Conclusion section worker.

    Generates conclusion by calling AcademicGenerator.generate_section("conclusion").
    """

    section_id = "conclusion"
    agent_name = "vkr_conclusion"
```

**File: `agents/content/workers/vkr_references.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class VKRReferencesWorker(BaseSectionWorker):
    """
    VKR References (Bibliography) section worker.

    AcademicGenerator.generate_section("references") formats the source_list
    from Phase 0A into GOST-compliant bibliography. If no source_list, falls
    back to LLM generation.
    """

    section_id = "references"
    agent_name = "vkr_references"
```

---

### Coursework Workers (7 files)

**File: `agents/content/workers/cw_title_page.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWTitlePageWorker(BaseSectionWorker):
    """Coursework Title Page worker. Format-only — handled by formatter.py."""

    section_id = "title_page"
    agent_name = "cw_title_page"
```

**File: `agents/content/workers/cw_toc.py`** — see TOC Worker Template above

**File: `agents/content/workers/cw_introduction.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWIntroductionWorker(BaseSectionWorker):
    """Coursework Introduction section worker."""

    section_id = "introduction"
    agent_name = "cw_introduction"
```

**File: `agents/content/workers/cw_chapter_1.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWChapter1Worker(BaseSectionWorker):
    """Coursework Chapter 1 (theoretical framework) worker."""

    section_id = "chapter_1"
    agent_name = "cw_chapter_1"
```

**File: `agents/content/workers/cw_chapter_2.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWChapter2Worker(BaseSectionWorker):
    """
    Coursework Chapter 2 (practical/empirical) worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_2"
    agent_name = "cw_chapter_2"
```

**File: `agents/content/workers/cw_conclusion.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWConclusionWorker(BaseSectionWorker):
    """Coursework Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "cw_conclusion"
```

**File: `agents/content/workers/cw_references.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class CWReferencesWorker(BaseSectionWorker):
    """Coursework References worker. Formats GOST bibliography from Phase 0A sources."""

    section_id = "references"
    agent_name = "cw_references"
```

---

### Research Workers (8 files)

**File: `agents/content/workers/res_annotation.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResAnnotationWorker(BaseSectionWorker):
    """Research Annotation (Abstract) section worker."""

    section_id = "annotation"
    agent_name = "res_annotation"
```

**File: `agents/content/workers/res_introduction.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResIntroductionWorker(BaseSectionWorker):
    """Research Introduction section worker."""

    section_id = "introduction"
    agent_name = "res_introduction"
```

**File: `agents/content/workers/res_literature_review.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResLiteratureReviewWorker(BaseSectionWorker):
    """Research Literature Review section worker."""

    section_id = "literature_review"
    agent_name = "res_literature_review"
```

**File: `agents/content/workers/res_methodology.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResMethodologyWorker(BaseSectionWorker):
    """Research Methodology section worker."""

    section_id = "methodology"
    agent_name = "res_methodology"
```

**File: `agents/content/workers/res_results.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResResultsWorker(BaseSectionWorker):
    """
    Research Results section worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "results"
    agent_name = "res_results"
```

**File: `agents/content/workers/res_discussion.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResDiscussionWorker(BaseSectionWorker):
    """
    Research Discussion section worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "discussion"
    agent_name = "res_discussion"
```

**File: `agents/content/workers/res_conclusion.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResConclusionWorker(BaseSectionWorker):
    """Research Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "res_conclusion"
```

**File: `agents/content/workers/res_references.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class ResReferencesWorker(BaseSectionWorker):
    """Research References worker. Formats GOST bibliography from Phase 0A sources."""

    section_id = "references"
    agent_name = "res_references"
```

---

### Abstract Paper Workers (6 files)

**File: `agents/content/workers/ap_title_page.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APTitlePageWorker(BaseSectionWorker):
    """Abstract Paper Title Page worker. Format-only — handled by formatter.py."""

    section_id = "title_page"
    agent_name = "ap_title_page"
```

**File: `agents/content/workers/ap_toc.py`** — see TOC Worker Template above

**File: `agents/content/workers/ap_introduction.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APIntroductionWorker(BaseSectionWorker):
    """Abstract Paper Introduction section worker."""

    section_id = "introduction"
    agent_name = "ap_introduction"
```

**File: `agents/content/workers/ap_chapter_1.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APChapter1Worker(BaseSectionWorker):
    """
    Abstract Paper Chapter 1 (main content) worker.

    DATA_HEAVY section — may be re-generated if viz deficit occurs.
    """

    section_id = "chapter_1"
    agent_name = "ap_chapter_1"
```

**File: `agents/content/workers/ap_conclusion.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APConclusionWorker(BaseSectionWorker):
    """Abstract Paper Conclusion section worker."""

    section_id = "conclusion"
    agent_name = "ap_conclusion"
```

**File: `agents/content/workers/ap_references.py`**

```python
from __future__ import annotations

from agents.content.workers.base_section_worker import BaseSectionWorker


class APReferencesWorker(BaseSectionWorker):
    """Abstract Paper References worker. Formats GOST bibliography from Phase 0A sources."""

    section_id = "references"
    agent_name = "ap_references"
```

---

## MicroManager `_get_worker()` Updates (4 files)

### File: `agents/content/micro_managers/mm_vkr.py` — REPLACE `_get_worker()` method

Replace the ENTIRE `_get_worker()` method (lines 49-70 in current file) with:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        WORKERS = {
            "title_page": VKRTitlePageWorker,
            "annotation": VKRAnnotationWorker,
            "toc": VKRTOCWorker,
            "introduction": VKRIntroductionWorker,
            "chapter_1": VKRChapter1Worker,
            "chapter_2": VKRChapter2Worker,
            "chapter_3": VKRChapter3Worker,
            "conclusion": VKRConclusionWorker,
            "references": VKRReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
```

**IMPORTANT**: Imports are inside the method to avoid circular imports at module level. This is the same pattern shown in the `BaseMicroManager._get_worker()` docstring example.

### File: `agents/content/micro_managers/mm_coursework.py` — REPLACE `_get_worker()` method

Replace the ENTIRE `_get_worker()` method (lines 40-42 in current file) with:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        WORKERS = {
            "title_page": CWTitlePageWorker,
            "toc": CWTOCWorker,
            "introduction": CWIntroductionWorker,
            "chapter_1": CWChapter1Worker,
            "chapter_2": CWChapter2Worker,
            "conclusion": CWConclusionWorker,
            "references": CWReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
```

### File: `agents/content/micro_managers/mm_research.py` — REPLACE `_get_worker()` method

Replace the ENTIRE `_get_worker()` method (lines 45-47 in current file) with:

```python
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
```

### File: `agents/content/micro_managers/mm_abstract_paper.py` — REPLACE `_get_worker()` method

Replace the ENTIRE `_get_worker()` method (lines 38-40 in current file) with:

```python
    def _get_worker(self, section_id: str):
        """Return worker for section_id."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        WORKERS = {
            "title_page": APTitlePageWorker,
            "toc": APTOCWorker,
            "introduction": APIntroductionWorker,
            "chapter_1": APChapter1Worker,
            "conclusion": APConclusionWorker,
            "references": APReferencesWorker,
        }
        cls = WORKERS.get(section_id)
        return cls() if cls else None
```

---

## Tests: `tests/test_phase3b_multi_section_workers.py`

```python
"""
Phase 3B Tests: Multi-Section Workers for VKR, Coursework, Research, Abstract Paper.
Run: pytest tests/test_phase3b_multi_section_workers.py -v

Tests:
1. All 30 workers instantiate correctly
2. All workers have correct section_id
3. All workers have correct agent_name
4. All workers inherit from BaseSectionWorker
5. All workers have agent_type == "worker"
6. MM _get_worker() returns correct worker class for each section_id
7. MM _get_worker() returns None for unknown section_id
8. TOC workers have execute_pass_2() method
9. TOC workers build correct TOC entries
10. WORKERS dict keys match SECTION_ORDER exactly
11. Phase 3A regression: BaseMicroManager is still abstract
12. Phase 2 regression: SECTION_ORDERs still match generator.py
"""
from __future__ import annotations

import asyncio
import pytest


# ── Test 1: VKR Workers ─────────────────────────────────────────


class TestVKRWorkers:
    def test_all_vkr_workers_instantiate(self):
        """All 9 VKR workers instantiate without error."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        workers = [
            VKRTitlePageWorker(),
            VKRAnnotationWorker(),
            VKRTOCWorker(),
            VKRIntroductionWorker(),
            VKRChapter1Worker(),
            VKRChapter2Worker(),
            VKRChapter3Worker(),
            VKRConclusionWorker(),
            VKRReferencesWorker(),
        ]
        assert len(workers) == 9
        for w in workers:
            assert w.agent_type == "worker"

    def test_vkr_worker_section_ids(self):
        """Each VKR worker has the correct section_id."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        expected = {
            VKRTitlePageWorker: "title_page",
            VKRAnnotationWorker: "annotation",
            VKRTOCWorker: "toc",
            VKRIntroductionWorker: "introduction",
            VKRChapter1Worker: "chapter_1",
            VKRChapter2Worker: "chapter_2",
            VKRChapter3Worker: "chapter_3",
            VKRConclusionWorker: "conclusion",
            VKRReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id, f"{cls.__name__}.section_id should be '{expected_id}'"

    def test_vkr_worker_agent_names(self):
        """Each VKR worker has agent_name matching 'vkr_{section_id}'."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_annotation import VKRAnnotationWorker
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.content.workers.vkr_introduction import VKRIntroductionWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_chapter_2 import VKRChapter2Worker
        from agents.content.workers.vkr_chapter_3 import VKRChapter3Worker
        from agents.content.workers.vkr_conclusion import VKRConclusionWorker
        from agents.content.workers.vkr_references import VKRReferencesWorker

        workers = [
            VKRTitlePageWorker(), VKRAnnotationWorker(), VKRTOCWorker(),
            VKRIntroductionWorker(), VKRChapter1Worker(), VKRChapter2Worker(),
            VKRChapter3Worker(), VKRConclusionWorker(), VKRReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"vkr_{w.section_id}", (
                f"{w.__class__.__name__}.agent_name should be 'vkr_{w.section_id}', got '{w.agent_name}'"
            )

    def test_vkr_workers_inherit_base(self):
        """All VKR workers inherit from BaseSectionWorker."""
        from agents.content.workers.base_section_worker import BaseSectionWorker
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.content.workers.vkr_chapter_1 import VKRChapter1Worker
        from agents.content.workers.vkr_toc import VKRTOCWorker

        assert isinstance(VKRTitlePageWorker(), BaseSectionWorker)
        assert isinstance(VKRChapter1Worker(), BaseSectionWorker)
        assert isinstance(VKRTOCWorker(), BaseSectionWorker)


# ── Test 2: Coursework Workers ──────────────────────────────────


class TestCourseworkWorkers:
    def test_all_cw_workers_instantiate(self):
        """All 7 Coursework workers instantiate without error."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        workers = [
            CWTitlePageWorker(), CWTOCWorker(), CWIntroductionWorker(),
            CWChapter1Worker(), CWChapter2Worker(),
            CWConclusionWorker(), CWReferencesWorker(),
        ]
        assert len(workers) == 7
        for w in workers:
            assert w.agent_type == "worker"

    def test_cw_worker_section_ids(self):
        """Each CW worker has the correct section_id."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        expected = {
            CWTitlePageWorker: "title_page",
            CWTOCWorker: "toc",
            CWIntroductionWorker: "introduction",
            CWChapter1Worker: "chapter_1",
            CWChapter2Worker: "chapter_2",
            CWConclusionWorker: "conclusion",
            CWReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_cw_worker_agent_names(self):
        """Each CW worker has agent_name matching 'cw_{section_id}'."""
        from agents.content.workers.cw_title_page import CWTitlePageWorker
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.content.workers.cw_introduction import CWIntroductionWorker
        from agents.content.workers.cw_chapter_1 import CWChapter1Worker
        from agents.content.workers.cw_chapter_2 import CWChapter2Worker
        from agents.content.workers.cw_conclusion import CWConclusionWorker
        from agents.content.workers.cw_references import CWReferencesWorker

        workers = [
            CWTitlePageWorker(), CWTOCWorker(), CWIntroductionWorker(),
            CWChapter1Worker(), CWChapter2Worker(),
            CWConclusionWorker(), CWReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"cw_{w.section_id}"


# ── Test 3: Research Workers ────────────────────────────────────


class TestResearchWorkers:
    def test_all_res_workers_instantiate(self):
        """All 8 Research workers instantiate without error."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        workers = [
            ResAnnotationWorker(), ResIntroductionWorker(),
            ResLiteratureReviewWorker(), ResMethodologyWorker(),
            ResResultsWorker(), ResDiscussionWorker(),
            ResConclusionWorker(), ResReferencesWorker(),
        ]
        assert len(workers) == 8
        for w in workers:
            assert w.agent_type == "worker"

    def test_res_worker_section_ids(self):
        """Each Research worker has the correct section_id."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        expected = {
            ResAnnotationWorker: "annotation",
            ResIntroductionWorker: "introduction",
            ResLiteratureReviewWorker: "literature_review",
            ResMethodologyWorker: "methodology",
            ResResultsWorker: "results",
            ResDiscussionWorker: "discussion",
            ResConclusionWorker: "conclusion",
            ResReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_res_worker_agent_names(self):
        """Each Research worker has agent_name matching 'res_{section_id}'."""
        from agents.content.workers.res_annotation import ResAnnotationWorker
        from agents.content.workers.res_introduction import ResIntroductionWorker
        from agents.content.workers.res_literature_review import ResLiteratureReviewWorker
        from agents.content.workers.res_methodology import ResMethodologyWorker
        from agents.content.workers.res_results import ResResultsWorker
        from agents.content.workers.res_discussion import ResDiscussionWorker
        from agents.content.workers.res_conclusion import ResConclusionWorker
        from agents.content.workers.res_references import ResReferencesWorker

        workers = [
            ResAnnotationWorker(), ResIntroductionWorker(),
            ResLiteratureReviewWorker(), ResMethodologyWorker(),
            ResResultsWorker(), ResDiscussionWorker(),
            ResConclusionWorker(), ResReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"res_{w.section_id}"


# ── Test 4: Abstract Paper Workers ──────────────────────────────


class TestAbstractPaperWorkers:
    def test_all_ap_workers_instantiate(self):
        """All 6 Abstract Paper workers instantiate without error."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        workers = [
            APTitlePageWorker(), APTOCWorker(), APIntroductionWorker(),
            APChapter1Worker(), APConclusionWorker(), APReferencesWorker(),
        ]
        assert len(workers) == 6
        for w in workers:
            assert w.agent_type == "worker"

    def test_ap_worker_section_ids(self):
        """Each AP worker has the correct section_id."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        expected = {
            APTitlePageWorker: "title_page",
            APTOCWorker: "toc",
            APIntroductionWorker: "introduction",
            APChapter1Worker: "chapter_1",
            APConclusionWorker: "conclusion",
            APReferencesWorker: "references",
        }
        for cls, expected_id in expected.items():
            assert cls().section_id == expected_id

    def test_ap_worker_agent_names(self):
        """Each AP worker has agent_name matching 'ap_{section_id}'."""
        from agents.content.workers.ap_title_page import APTitlePageWorker
        from agents.content.workers.ap_toc import APTOCWorker
        from agents.content.workers.ap_introduction import APIntroductionWorker
        from agents.content.workers.ap_chapter_1 import APChapter1Worker
        from agents.content.workers.ap_conclusion import APConclusionWorker
        from agents.content.workers.ap_references import APReferencesWorker

        workers = [
            APTitlePageWorker(), APTOCWorker(), APIntroductionWorker(),
            APChapter1Worker(), APConclusionWorker(), APReferencesWorker(),
        ]
        for w in workers:
            assert w.agent_name == f"ap_{w.section_id}"


# ── Test 5: MM _get_worker() routing ────────────────────────────


class TestMMWorkerRouting:
    def test_vkr_get_worker_returns_correct_classes(self):
        """VKR MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        mm = MicroManagerVKR()
        expected_names = {
            "title_page": "vkr_title_page",
            "annotation": "vkr_annotation",
            "toc": "vkr_toc",
            "introduction": "vkr_introduction",
            "chapter_1": "vkr_chapter_1",
            "chapter_2": "vkr_chapter_2",
            "chapter_3": "vkr_chapter_3",
            "conclusion": "vkr_conclusion",
            "references": "vkr_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"VKR _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_cw_get_worker_returns_correct_classes(self):
        """Coursework MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework

        mm = MicroManagerCoursework()
        expected_names = {
            "title_page": "cw_title_page",
            "toc": "cw_toc",
            "introduction": "cw_introduction",
            "chapter_1": "cw_chapter_1",
            "chapter_2": "cw_chapter_2",
            "conclusion": "cw_conclusion",
            "references": "cw_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"CW _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_res_get_worker_returns_correct_classes(self):
        """Research MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch

        mm = MicroManagerResearch()
        expected_names = {
            "annotation": "res_annotation",
            "introduction": "res_introduction",
            "literature_review": "res_literature_review",
            "methodology": "res_methodology",
            "results": "res_results",
            "discussion": "res_discussion",
            "conclusion": "res_conclusion",
            "references": "res_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"RES _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_ap_get_worker_returns_correct_classes(self):
        """Abstract Paper MM returns correct worker class for each section."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        mm = MicroManagerAbstractPaper()
        expected_names = {
            "title_page": "ap_title_page",
            "toc": "ap_toc",
            "introduction": "ap_introduction",
            "chapter_1": "ap_chapter_1",
            "conclusion": "ap_conclusion",
            "references": "ap_references",
        }
        for section_id, expected_name in expected_names.items():
            worker = mm._get_worker(section_id)
            assert worker is not None, f"AP _get_worker('{section_id}') returned None"
            assert worker.agent_name == expected_name
            assert worker.section_id == section_id

    def test_all_mms_return_none_for_unknown_section(self):
        """All 4 MMs return None for unknown section_id."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        for mm_class in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_class()
            assert mm._get_worker("nonexistent_section") is None


# ── Test 6: WORKERS dict keys match SECTION_ORDER ───────────────


class TestWorkersMatchSectionOrder:
    def test_vkr_workers_cover_all_sections(self):
        """VKR WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        mm = MicroManagerVKR()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"VKR missing worker for '{section_id}'"

    def test_cw_workers_cover_all_sections(self):
        """CW WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework

        mm = MicroManagerCoursework()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"CW missing worker for '{section_id}'"

    def test_res_workers_cover_all_sections(self):
        """Research WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch

        mm = MicroManagerResearch()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"RES missing worker for '{section_id}'"

    def test_ap_workers_cover_all_sections(self):
        """AP WORKERS dict keys match SECTION_ORDER exactly."""
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        mm = MicroManagerAbstractPaper()
        for section_id in mm.SECTION_ORDER:
            worker = mm._get_worker(section_id)
            assert worker is not None, f"AP missing worker for '{section_id}'"


# ── Test 7: TOC workers ─────────────────────────────────────────


class TestTOCWorkers:
    def test_vkr_toc_has_execute_pass_2(self):
        """VKR TOC worker has execute_pass_2() method."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        worker = VKRTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_cw_toc_has_execute_pass_2(self):
        """CW TOC worker has execute_pass_2() method."""
        from agents.content.workers.cw_toc import CWTOCWorker
        worker = CWTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_ap_toc_has_execute_pass_2(self):
        """AP TOC worker has execute_pass_2() method."""
        from agents.content.workers.ap_toc import APTOCWorker
        worker = APTOCWorker()
        assert hasattr(worker, 'execute_pass_2')

    def test_vkr_toc_sections_correct(self):
        """VKR TOC_SECTIONS lists correct sections."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        worker = VKRTOCWorker()
        assert "annotation" in worker.TOC_SECTIONS
        assert "introduction" in worker.TOC_SECTIONS
        assert "chapter_1" in worker.TOC_SECTIONS
        assert "chapter_2" in worker.TOC_SECTIONS
        assert "chapter_3" in worker.TOC_SECTIONS
        assert "conclusion" in worker.TOC_SECTIONS
        # Should NOT include title_page, toc, references
        assert "title_page" not in worker.TOC_SECTIONS
        assert "toc" not in worker.TOC_SECTIONS
        assert "references" not in worker.TOC_SECTIONS

    def test_cw_toc_sections_correct(self):
        """CW TOC_SECTIONS lists correct sections (no annotation, no chapter_3)."""
        from agents.content.workers.cw_toc import CWTOCWorker
        worker = CWTOCWorker()
        assert worker.TOC_SECTIONS == ["introduction", "chapter_1", "chapter_2", "conclusion"]

    def test_ap_toc_sections_correct(self):
        """AP TOC_SECTIONS lists correct sections (intro, chapter_1, conclusion)."""
        from agents.content.workers.ap_toc import APTOCWorker
        worker = APTOCWorker()
        assert worker.TOC_SECTIONS == ["introduction", "chapter_1", "conclusion"]

    def test_vkr_toc_pass_2_builds_toc(self):
        """VKR TOC pass 2 builds TOC from generated_sections."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.state import PipelineState

        worker = VKRTOCWorker()
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            language="ru",
            text="Some existing text",
            generated_sections={
                "annotation": "## Аннотация\n\nТекст аннотации.",
                "introduction": "## Введение\n\nТекст введения.",
                "chapter_1": "## Глава 1. Теоретические основы\n\nТекст главы.",
                "chapter_2": "## Глава 2. Анализ данных\n\nТекст главы.",
                "chapter_3": "## Глава 3. Рекомендации\n\nТекст главы.",
                "conclusion": "## Заключение\n\nТекст заключения.",
                "references": "## Список литературы\n\n1. Источник.",
            },
        )

        result = asyncio.run(worker.execute_pass_2(state))

        toc = result.generated_sections["toc"]
        assert "Оглавление" in toc
        assert "Аннотация" in toc
        assert "Введение" in toc
        assert "Глава 1. Теоретические основы" in toc
        assert "Глава 2. Анализ данных" in toc
        assert "Глава 3. Рекомендации" in toc
        assert "Заключение" in toc
        assert "Список литературы" in toc

    def test_toc_pass_2_uses_fallback_names(self):
        """TOC pass 2 uses SECTION_NAMES fallback when no heading found."""
        from agents.content.workers.cw_toc import CWTOCWorker
        from agents.state import PipelineState

        worker = CWTOCWorker()
        state = PipelineState(
            mode="generation",
            stream_id="coursework",
            language="en",
            text="Some text",
            generated_sections={
                "introduction": "Some text without heading.",
                "chapter_1": "Also no heading here.",
                "chapter_2": "No heading either.",
                "conclusion": "Still no heading.",
            },
        )

        result = asyncio.run(worker.execute_pass_2(state))
        toc = result.generated_sections["toc"]
        assert "Introduction" in toc
        assert "Chapter 1" in toc
        assert "Chapter 2" in toc
        assert "Conclusion" in toc
        assert "References" in toc

    def test_toc_extract_heading(self):
        """_extract_heading finds ## headings correctly."""
        from agents.content.workers.vkr_toc import VKRTOCWorker

        assert VKRTOCWorker._extract_heading("## Введение\n\nТекст") == "Введение"
        assert VKRTOCWorker._extract_heading("### Подраздел\n\nТекст") == "Подраздел"
        assert VKRTOCWorker._extract_heading("No heading here") == ""
        assert VKRTOCWorker._extract_heading("") == ""

    def test_research_has_no_toc_worker(self):
        """Research MM has no toc in SECTION_ORDER — no TOC worker needed."""
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        mm = MicroManagerResearch()
        assert "toc" not in mm.SECTION_ORDER
        assert not mm.has_toc()


# ── Test 8: Format-only workers execute correctly ────────────────


class TestFormatOnlyWorkers:
    def test_title_page_worker_returns_empty(self):
        """Title page worker stores empty string (format-only)."""
        from agents.content.workers.vkr_title_page import VKRTitlePageWorker
        from agents.state import PipelineState

        worker = VKRTitlePageWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert result.generated_sections["title_page"] == ""

    def test_toc_worker_pass_1_returns_empty(self):
        """TOC worker pass 1 (execute) stores empty string."""
        from agents.content.workers.vkr_toc import VKRTOCWorker
        from agents.state import PipelineState

        worker = VKRTOCWorker()
        state = PipelineState(mode="generation", stream_id="vkr", topic="Test")
        result = asyncio.run(worker.execute(state))

        assert not result.has_errors()
        assert result.generated_sections["toc"] == ""


# ── Test 9: Phase 3A regression ─────────────────────────────────


class TestPhase3ARegression:
    def test_base_micro_manager_still_abstract(self):
        """BaseMicroManager still cannot be instantiated (abstract _get_worker)."""
        from agents.content.micro_managers.base import BaseMicroManager
        with pytest.raises(TypeError):
            BaseMicroManager()

    def test_section_orders_still_match_generator(self):
        """All SECTION_ORDERs still match pipeline/generator.py constants."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper
        from pipeline.generator import SECTION_ORDER

        assert MicroManagerVKR().SECTION_ORDER == SECTION_ORDER["vkr"]
        assert MicroManagerCoursework().SECTION_ORDER == SECTION_ORDER["coursework"]
        assert MicroManagerResearch().SECTION_ORDER == SECTION_ORDER["research"]
        assert MicroManagerAbstractPaper().SECTION_ORDER == SECTION_ORDER["abstract_paper"]

    def test_viz_minimums_still_match(self):
        """VIZ_MINIMUMS cross-check with ContentQAGate still passes."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.gates.content_qa import ContentQAGate

        mm = MicroManagerVKR()
        gate = ContentQAGate()
        gate_vkr = gate.VIZ_MINIMUMS["vkr"]

        for level in ["bachelor", "master", "specialist", "postgraduate"]:
            assert mm.get_viz_minimum(level) == gate_vkr[level]

    def test_count_visualizations_still_works(self):
        """count_visualizations still counts correctly after Phase 3B changes."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR

        text = "| A | B |\n|---|---|\n| 1 | 2 |\n\n[РИСУНОК 1 — Test]"
        tables, figures = MicroManagerVKR.count_visualizations(text)
        assert tables == 1
        assert figures == 1

    def test_total_worker_count_is_30(self):
        """Phase 3B creates exactly 30 workers across 4 streams."""
        from agents.content.micro_managers.mm_vkr import MicroManagerVKR
        from agents.content.micro_managers.mm_coursework import MicroManagerCoursework
        from agents.content.micro_managers.mm_research import MicroManagerResearch
        from agents.content.micro_managers.mm_abstract_paper import MicroManagerAbstractPaper

        total = 0
        for mm_class in [MicroManagerVKR, MicroManagerCoursework, MicroManagerResearch, MicroManagerAbstractPaper]:
            mm = mm_class()
            for section_id in mm.SECTION_ORDER:
                worker = mm._get_worker(section_id)
                assert worker is not None, f"{mm.agent_name} missing worker for '{section_id}'"
                total += 1

        assert total == 30, f"Expected 30 workers, got {total}"
```

---

## Changes Summary

| # | File | Action | Lines |
|---|---|---|---|
| 1-9 | `agents/content/workers/vkr_*.py` | CREATE 9 files | ~15 each (TOC: ~100) |
| 10-16 | `agents/content/workers/cw_*.py` | CREATE 7 files | ~15 each (TOC: ~70) |
| 17-24 | `agents/content/workers/res_*.py` | CREATE 8 files | ~15 each |
| 25-30 | `agents/content/workers/ap_*.py` | CREATE 6 files | ~15 each (TOC: ~70) |
| 31 | `mm_vkr.py` | REPLACE `_get_worker()` | ~25 |
| 32 | `mm_coursework.py` | REPLACE `_get_worker()` | ~20 |
| 33 | `mm_research.py` | REPLACE `_get_worker()` | ~20 |
| 34 | `mm_abstract_paper.py` | REPLACE `_get_worker()` | ~18 |
| 35 | `tests/test_phase3b_multi_section_workers.py` | CREATE tests | ~450 |

**Total: 30 new worker files + 4 MM modifications + 1 test file = 35 file operations**

## Verification

```bash
pytest tests/test_phase3b_multi_section_workers.py -v    # New tests
pytest tests/test_phase3a_base_worker.py -v               # Phase 3A regression
pytest tests/test_phase2_content.py -v                     # Phase 2 regression
pytest tests/test_phase1_ceo.py -v                         # Phase 1 regression
pytest tests/test_agents_foundation.py -v                  # Phase 0 regression
pytest tests/ -v --tb=short                                # All tests
```

## Critical Constraints

1. **NO modifications to `base_section_worker.py`** — all logic already there from Phase 3A
2. **NO modifications to `base.py` (BaseMicroManager)** — orchestration logic already there from Phase 3A
3. **NO modifications to `generator.py`** — `generate_section()` already there from Phase 3A
4. **NO modifications to `state.py`** — `last_section_text` already there from Phase 3A
5. **Standard workers are 15 lines each** — do not add extra logic
6. **TOC workers are the ONLY workers with custom methods** — `execute_pass_2()` + `_extract_heading()` + `TOC_SECTIONS`
7. **Imports inside `_get_worker()`** — to avoid circular imports at module level
8. **WORKERS dict keys MUST match SECTION_ORDER exactly** — test verifies this
9. **Research has NO TOC** — `mm_research.py` has no `toc` in SECTION_ORDER, no TOC worker needed
10. **All worker `agent_name` follows pattern `{prefix}_{section_id}`** — vkr_introduction, cw_chapter_1, res_results, ap_conclusion
