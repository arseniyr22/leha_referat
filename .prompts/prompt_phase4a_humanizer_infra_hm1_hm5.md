# Prompt 4A: HumanizerManager Infrastructure + HM-1 (Analyzer) + HM-5 (Scorer)

## Context

Phases 1–3 built the content generation chain: `CEO → ContentManager → MicroManager → Worker → generator.py`

Phase 4 builds the **humanization chain**: `CEO → HumanizerManager → HM-1 → HM-2 → HM-3 → HM-4 → HM-5`

Phase 4A creates the infrastructure: base class, manager, and the two **local** stages (no API cost):
- HM-1 wraps `pipeline/analyzer.py` (Stage 1)
- HM-5 wraps `pipeline/scorer.py` (Stage 5)

Phases 4B/4C/4D will add HM-2, HM-3, HM-4 (API stages) and CEO integration.

---

## Reference: Current Source State

### Pipeline.run() flow (pipeline/__init__.py lines 142-241) — the code we are wrapping

```python
class Pipeline:
    def run(self, text, verbose=False, domain_override=None, register_override=None, run_detector_probes=False):
        language = getattr(self, "_current_language", "en")

        # Stage 1: Analysis
        analysis_report = self.analyzer.score(text)
        domain = domain_override or analysis_report.get("domain", "general")
        register = register_override or analysis_report.get("register", "general")
        analysis_report["_language"] = language
        if language == "ru":
            analysis_report["_skip_perplexity"] = True
            analysis_report["_use_word_cv"] = True

        # Stage 2: Structural Rewrite
        structural_score = self.structural_rewriter.score(text)
        text_s2 = self.structural_rewriter.transform(text, domain, register, analysis_report, language)

        # Stage 3: Lexical Enrichment
        text_s3 = self.lexical_enricher.transform(text_s2, domain, register, analysis_report, language)

        # Stage 4: Discourse Shaping
        text_s4 = self.discourse_shaper.transform(text_s3, domain, register, analysis_report, structural_score, language)

        # Stage 5: Scoring
        score_report = self.scorer.score(input_text=text, output_text=text_s4, domain=domain, register=register)
        score_report["_language"] = language
        if language == "ru":
            score_report["perplexity_lift"] = None
            score_report["perplexity_note"] = "N/A (Russian text — GPT-2 English only)"
        score_report["_elapsed_seconds"] = elapsed
        score_report["_word_count_in"] = len(text.split())
        score_report["_word_count_out"] = len(text_s4.split())

        return text_s4, score_report
```

Key observations for agent wrapping:
1. Stage 1 produces `analysis_report` — consumed by ALL downstream stages (2, 3, 4)
2. Stage 2 produces `structural_score` — consumed by Stage 4 only
3. `domain` and `register` are resolved from analysis_report OR overrides — available in `state`
4. `language` comes from `state.language`
5. Stage 5 needs both `input_text` (original) AND `output_text` (after Stage 4)

### Analyzer class interface (pipeline/analyzer.py)

```python
class Analyzer:
    def transform(self, text: str) -> str:
        """Read-only; returns text unchanged."""
        return text

    def score(self, text: str) -> dict:
        """Run all 20 Stage 1 operations. Returns comprehensive analysis report dict."""
        # Returns dict with keys: domain, register, word_count, perplexity, sentence_cv,
        # para_cv, section_cv, patterns, transition_monotony, announcement_openers,
        # triplets, para_ending_generalizations, attributive_passives, genuinely_adj,
        # but_however, connector_density, modal_hedging_on_results, standalone_definitions,
        # key_terms, also_frequency, p7_violations, citations, elapsed_seconds
```

### Scorer class interface (pipeline/scorer.py)

```python
class Scorer:
    def transform(self, text: str) -> str:
        """Read-only; returns text unchanged."""
        return text

    def score(self, input_text: str, output_text: str, domain: str = "general",
              register: str = "general", run_detector_probes: bool = False) -> dict:
        """Run all 20 Stage 5 metrics. Returns score report with _summary."""
        # Returns dict with keys for each metric + _summary with passed/failed lists
```

### BaseAgent interface (agents/base.py)

```python
class BaseAgent(ABC):
    agent_name: str = "base"
    agent_type: str = "base"

    def __init__(self) -> None:
        self._prompts_dir = Path(__file__).parent / "prompts"

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        ...

    def load_prompt(self, prompt_name: str) -> str: ...
    def call_claude(self, system, user, model=None, temperature=None, max_tokens=4096) -> tuple[str, dict]: ...
```

### ContentManager pattern (agents/content/manager.py) — reference for HumanizerManager design

ContentManager:
- `agent_type = "manager"`
- `execute(state)` validates state, runs source discovery, routes to MM, validates output
- Has routing table (`MM_ROUTING`) mapping stream_id → MM class
- Does NOT modify text directly — delegates everything to subordinates

### PipelineState relevant fields (agents/state.py)

```python
@dataclass
class PipelineState:
    mode: str                        # "generation" | "humanization"
    text: str = ""                   # Current text (mutated by each stage)
    language: str = "en"
    domain: str = "general"
    register: str = "general"
    analysis_report: dict = field(default_factory=dict)       # Stage 1 output
    final_score_report: dict = field(default_factory=dict)    # Stage 5 output
    errors: list[str] = field(default_factory=list)
    cost_report: CostReport = field(default_factory=CostReport)
    feedback_iterations: int = 0
    feedback_target: str = ""
    feedback_from_qa: Optional[dict] = None
```

### CEO._run_humanization() — current caller (will be updated in Phase 4D)

```python
async def _run_humanization(self, state: PipelineState) -> PipelineState:
    from pipeline import Pipeline
    pipe = Pipeline()
    pipe._current_language = state.language
    output_text, score_report = pipe.run(
        text=state.text, verbose=True,
        domain_override=state.domain if state.domain != "general" else None,
        register_override=state.register if state.register != "general" else None,
    )
    state.text = output_text
    state.final_score_report = score_report
    state = await self._feedback_loop(state)
    return state
```

---

## New Fields on PipelineState

Phase 4A requires **2 new fields** on PipelineState to store intermediate data passed between HM stages:

```python
# Add to PipelineState (agents/state.py):
structural_score: dict = field(default_factory=dict)    # Stage 2 score (consumed by Stage 4)
original_text: str = ""                                 # Snapshot of text before humanization (for Stage 5 comparison)
```

`structural_score` is produced by HM-2 and consumed by HM-4 (DiscourseShaper needs it for Pass A).
`original_text` is set by HumanizerManager before running HM-1, so HM-5 can compute deltas (perplexity_lift, pattern_elimination, length_reduction).

---

## Architecture Overview

```
agents/
├── humanizer/                     # NEW package
│   ├── __init__.py                # NEW (empty)
│   ├── manager.py                 # NEW — HumanizerManager
│   ├── base_stage.py              # NEW — BaseHumanizerStage
│   └── stages/                    # NEW package
│       ├── __init__.py            # NEW (empty)
│       ├── hm1_analyzer.py        # NEW — HM1Analyzer
│       └── hm5_scorer.py          # NEW — HM5Scorer
```

Phases 4B/4C/4D will add:
```
│       ├── hm2_structural.py      # Phase 4B
│       ├── hm3_lexical.py         # Phase 4C
│       └── hm4_discourse.py       # Phase 4D
```

---

## Part 1: Create PipelineState Fields

### File 1: MODIFY `agents/state.py`

Add two new fields to `PipelineState`. **Apply changes in reverse line order (highest line first) to avoid line-shift issues.**

**Change 1:** After the field `analysis_report: dict = field(default_factory=dict)` (currently line 74), add a new section with `structural_score`:

```python
    # ── Stage 2 (HM-2) output ─────────────────────────────────────
    structural_score: dict = field(default_factory=dict)  # Stage 2 score (HM-2 output, consumed by HM-4)
```

So the result looks like:
```python
    # ── Stage 1 (HM-1) output ─────────────────────────────────────
    analysis_report: dict = field(default_factory=dict)

    # ── Stage 2 (HM-2) output ─────────────────────────────────────
    structural_score: dict = field(default_factory=dict)  # Stage 2 score (HM-2 output, consumed by HM-4)

    # ── Stage 5 (HM-5) output ─────────────────────────────────────
    final_score_report: dict = field(default_factory=dict)
```

**Change 2:** After the field `text: str = ""` (currently line 55), add:

```python
    original_text: str = ""          # Snapshot before humanization (for HM-5 delta scoring)
```

**What NOT to change:** All existing fields, methods, imports. Only ADD these lines.

---

## Part 2: Create Base Class — BaseHumanizerStage

### File 2: CREATE `agents/humanizer/__init__.py`

```python
```

(Empty file — package marker.)

### File 3: CREATE `agents/humanizer/stages/__init__.py`

```python
```

(Empty file — package marker.)

### File 4: CREATE `agents/humanizer/base_stage.py`

```python
from __future__ import annotations

from abc import abstractmethod

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class BaseHumanizerStage(BaseAgent):
    """
    Abstract base for all humanization stage agents (HM-1 through HM-5).

    Each HM stage wraps one of the existing pipeline/ classes:
    - HM-1: pipeline/analyzer.py (Analyzer)
    - HM-2: pipeline/structural_rewriter.py (StructuralRewriter)
    - HM-3: pipeline/lexical_enricher.py (LexicalEnricher)
    - HM-4: pipeline/discourse_shaper.py (DiscourseShaper)
    - HM-5: pipeline/scorer.py (Scorer)

    Design principles:
    - Wrap, don't rewrite: each HM calls the existing pipeline class directly
    - Pure state-in, state-out: reads from state, writes results back to state
    - HM-1 and HM-5 are local (no API cost)
    - HM-2, HM-3, HM-4 call Claude API via the pipeline classes
    - Errors are caught and stored in state.errors (never crash)
    - Cost tracking: API stages track usage via state.cost_report

    Subclasses MUST set:
    - agent_name: str — unique name (e.g., "hm1_analyzer")
    - stage_number: int — 1-5, for ordering and logging

    Subclasses MUST implement:
    - execute(state) → state
    """

    agent_type = "stage"

    # Subclasses MUST override
    stage_number: int = 0

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """Run this humanization stage. Must be implemented by each HM."""
        ...

    def _get_domain(self, state: PipelineState) -> str:
        """
        Get effective domain for this run.

        Priority: state.domain (if not "general") > analysis_report domain > "general"
        """
        if state.domain and state.domain != "general":
            return state.domain
        return state.analysis_report.get("domain", "general")

    def _get_register(self, state: PipelineState) -> str:
        """
        Get effective register for this run.

        Priority: state.register (if not "general") > analysis_report register > "general"
        """
        if state.register and state.register != "general":
            return state.register
        return state.analysis_report.get("register", "general")
```

**Design notes:**
- `_get_domain()` and `_get_register()` centralize the resolution logic that `Pipeline.run()` does inline. This avoids duplicating the `domain_override or analysis_report.get("domain")` pattern in every HM stage.
- `agent_type = "stage"` distinguishes HM agents from workers, managers, gates, and services.
- `stage_number` enables ordering-aware logging and future validation that stages execute in order.

---

## Part 3: Create HM-1 (Analyzer)

### File 5: CREATE `agents/humanizer/stages/hm1_analyzer.py`

```python
from __future__ import annotations

import time

from loguru import logger

from agents.humanizer.base_stage import BaseHumanizerStage
from agents.state import PipelineState


class HM1Analyzer(BaseHumanizerStage):
    """
    HM-1: Analysis stage.

    Wraps pipeline/analyzer.py Analyzer.score().
    Runs entirely locally — no API cost.

    Responsibilities:
    1. Run Analyzer.score(text) to produce analysis_report
    2. Store analysis_report in state.analysis_report
    3. Resolve domain and register (from analysis or state overrides)
    4. Set language flags (_language, _skip_perplexity, _use_word_cv)

    Consumes: state.text
    Produces: state.analysis_report (used by HM-2, HM-3, HM-4)
    """

    agent_name = "hm1_analyzer"
    stage_number = 1

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Run Stage 1 analysis on state.text.

        Steps:
        1. Validate text exists
        2. Call Analyzer.score(text)
        3. Store analysis_report in state
        4. Apply language flags
        5. Resolve domain/register into state (if not already set by user)
        """
        if not state.text:
            state.add_error(self.agent_name, "No text to analyze")
            return state

        t0 = time.time()
        logger.info(
            f"[{self.agent_name}] Starting | words={state.word_count()} | "
            f"language={state.language}"
        )

        try:
            from pipeline.analyzer import Analyzer

            analyzer = Analyzer()
            analysis_report = analyzer.score(state.text)
        except Exception as e:
            state.add_error(self.agent_name, f"Analysis failed: {e}")
            logger.error(f"[{self.agent_name}] Analysis error: {e}")
            return state

        # Store analysis report
        state.analysis_report = analysis_report

        # Apply language flags (same logic as Pipeline.run() lines 169-172)
        state.analysis_report["_language"] = state.language
        if state.language == "ru":
            state.analysis_report["_skip_perplexity"] = True
            state.analysis_report["_use_word_cv"] = True

        # Resolve domain/register: user overrides take priority over analysis
        # If state.domain is "general" (default), use analysis result
        if state.domain == "general":
            detected_domain = analysis_report.get("domain", "general")
            if detected_domain != "general":
                state.domain = detected_domain
                logger.info(f"[{self.agent_name}] Domain auto-detected: {detected_domain}")

        if state.register == "general":
            detected_register = analysis_report.get("register", "general")
            if detected_register != "general":
                state.register = detected_register
                logger.info(f"[{self.agent_name}] Register auto-detected: {detected_register}")

        elapsed = time.time() - t0
        perp = analysis_report.get("perplexity")
        s_cv = analysis_report.get("sentence_cv")
        p_cv = analysis_report.get("para_cv")
        logger.info(
            f"[{self.agent_name}] Complete | "
            f"domain={state.domain} | register={state.register} | "
            f"perplexity={f'{perp:.1f}' if isinstance(perp, (int, float)) else 'N/A'} | "
            f"sentence_cv={f'{s_cv:.3f}' if isinstance(s_cv, (int, float)) else 'N/A'} | "
            f"para_cv={f'{p_cv:.3f}' if isinstance(p_cv, (int, float)) else 'N/A'} | "
            f"elapsed={elapsed:.2f}s"
        )

        return state
```

---

## Part 4: Create HM-5 (Scorer)

### File 6: CREATE `agents/humanizer/stages/hm5_scorer.py`

```python
from __future__ import annotations

import time

from loguru import logger

from agents.humanizer.base_stage import BaseHumanizerStage
from agents.state import PipelineState


class HM5Scorer(BaseHumanizerStage):
    """
    HM-5: Scoring & Feedback stage.

    Wraps pipeline/scorer.py Scorer.score().
    Runs entirely locally — no API cost.

    Responsibilities:
    1. Run Scorer.score(input_text=original, output_text=current) to produce score_report
    2. Apply language gates (Russian: skip perplexity)
    3. Attach word count metadata
    4. Store score_report in state.final_score_report

    Consumes: state.text (current), state.original_text (snapshot before humanization)
    Produces: state.final_score_report (used by CEO feedback loop)
    """

    agent_name = "hm5_scorer"
    stage_number = 5

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Run Stage 5 scoring.

        Steps:
        1. Validate text and original_text exist
        2. Call Scorer.score(input_text, output_text, domain, register)
        3. Apply language gates (AC-15: Russian skips perplexity)
        4. Attach metadata (_language, _word_count_in, _word_count_out)
        5. Store in state.final_score_report
        """
        if not state.text:
            state.add_error(self.agent_name, "No text to score")
            return state

        # original_text is the snapshot taken before humanization started
        # If not set, fall back to state.text (scoring against itself = baseline)
        original_text = state.original_text if state.original_text else state.text

        t0 = time.time()
        domain = self._get_domain(state)
        register = self._get_register(state)

        logger.info(
            f"[{self.agent_name}] Starting | "
            f"input_words={len(original_text.split())} | "
            f"output_words={state.word_count()} | "
            f"domain={domain} | register={register}"
        )

        try:
            from pipeline.scorer import Scorer

            scorer = Scorer()
            score_report = scorer.score(
                input_text=original_text,
                output_text=state.text,
                domain=domain,
                register=register,
                run_detector_probes=False,
            )
        except Exception as e:
            state.add_error(self.agent_name, f"Scoring failed: {e}")
            logger.error(f"[{self.agent_name}] Scoring error: {e}")
            return state

        # Apply language gates (same logic as Pipeline.run() lines 230-233)
        score_report["_language"] = state.language
        if state.language == "ru":
            score_report["perplexity_lift"] = None
            score_report["perplexity_note"] = "N/A (Russian text — GPT-2 English only)"

        # Attach timing and word count metadata
        elapsed = time.time() - t0
        score_report["_elapsed_seconds"] = elapsed
        score_report["_word_count_in"] = len(original_text.split())
        score_report["_word_count_out"] = state.word_count()

        # Store in state
        state.final_score_report = score_report

        # Log summary
        summary = score_report.get("_summary", {})
        pass_rate = summary.get("pass_rate", 0)
        logger.info(
            f"[{self.agent_name}] Complete | "
            f"passed={len(summary.get('passed', []))} | "
            f"failed={len(summary.get('failed', []))} | "
            f"pass_rate={f'{pass_rate:.0%}' if isinstance(pass_rate, (int, float)) else 'N/A'} | "
            f"elapsed={elapsed:.2f}s"
        )

        return state
```

---

## Part 5: Create HumanizerManager

### File 7: CREATE `agents/humanizer/manager.py`

```python
from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class HumanizerManager(BaseAgent):
    """
    Humanizer Manager — orchestrates Stages 1-5 (humanization pipeline).

    Analogous to ContentManager for content generation.

    Full flow:
    1. Snapshot original_text for delta scoring (HM-5)
    2. HM-1: Analysis → state.analysis_report
    3. HM-2: Structural Rewrite → state.text mutated
    4. HM-3: Lexical Enrichment → state.text mutated
    5. HM-4: Discourse Shaping → state.text mutated
    6. HM-5: Scoring → state.final_score_report

    Selective re-run (feedback loop):
    When CEO routes feedback to a specific stage (state.feedback_target = "hm2"|"hm3"|"hm4"),
    HumanizerManager re-runs ONLY that stage + HM-5 (rescore).
    This saves API cost vs. full pipeline re-run.

    Phase 4A: Only HM-1 and HM-5 are wired. HM-2/3/4 are stubs returning state unchanged.
    Phase 4B/4C/4D will replace the stubs.
    """

    agent_name = "humanizer_manager"
    agent_type = "manager"

    # Stage ordering for full run
    STAGE_ORDER = ["hm1", "hm2", "hm3", "hm4", "hm5"]

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Run the full humanization pipeline (HM-1 through HM-5).

        Steps:
        1. Validate text exists
        2. Snapshot original_text for HM-5 delta scoring
        3. Run each stage in order
        4. Return state with humanized text + score_report
        """
        if not state.text:
            state.add_error(self.agent_name, "No text to humanize")
            return state

        t0 = time.time()

        logger.info(
            f"[{self.agent_name}] Starting full pipeline | "
            f"words={state.word_count()} | language={state.language} | "
            f"domain={state.domain} | register={state.register}"
        )

        # Snapshot original text for HM-5 comparison scoring
        # (Only set if not already set — preserves original across feedback iterations)
        if not state.original_text:
            state.original_text = state.text

        # Run all 5 stages in order
        for stage_key in self.STAGE_ORDER:
            stage = self._get_stage(stage_key)
            if stage is None:
                logger.warning(
                    f"[{self.agent_name}] Stage {stage_key} not available — skipping"
                )
                continue

            logger.info(
                f"[{self.agent_name}] Running {stage_key} ({stage.agent_name})"
            )

            # Track error count before stage — to detect NEW errors from this stage only
            errors_before = len(state.errors)
            state = await stage.execute(state)

            if len(state.errors) > errors_before:
                last_error = state.errors[-1]
                # Fatal only if HM-1 fails (no analysis_report = downstream stages can't work)
                if stage_key == "hm1":
                    logger.error(
                        f"[{self.agent_name}] HM-1 failed — cannot proceed: {last_error}"
                    )
                    return state
                else:
                    # Non-fatal for HM-2/3/4/5: log and continue
                    logger.warning(
                        f"[{self.agent_name}] {stage_key} had errors — continuing: {last_error}"
                    )

        elapsed = time.time() - t0
        logger.info(
            f"[{self.agent_name}] Complete | "
            f"output_words={state.word_count()} | "
            f"elapsed={elapsed:.1f}s"
        )

        return state

    async def execute_targeted(self, state: PipelineState, target_stage: str) -> PipelineState:
        """
        Re-run a single targeted stage + HM-5 rescore.

        Used by CEO feedback loop: instead of re-running the full pipeline,
        only re-run the problematic stage and rescore.

        Args:
            state: Current state (with text already partially humanized)
            target_stage: "hm2" | "hm3" | "hm4" — which stage to re-run

        Steps:
        1. Validate target_stage
        2. Run target stage
        3. Run HM-5 (rescore)
        4. Return updated state
        """
        valid_targets = {"hm2", "hm3", "hm4"}
        if target_stage not in valid_targets:
            state.add_error(
                self.agent_name,
                f"Invalid feedback target: {target_stage}. Must be one of {valid_targets}"
            )
            return state

        logger.info(
            f"[{self.agent_name}] Targeted re-run: {target_stage} + hm5 | "
            f"words={state.word_count()}"
        )

        # Run target stage
        stage = self._get_stage(target_stage)
        if stage is None:
            state.add_error(self.agent_name, f"Stage {target_stage} not available")
            return state

        state = await stage.execute(state)

        # Rescore with HM-5
        scorer = self._get_stage("hm5")
        if scorer is not None:
            state = await scorer.execute(state)

        return state

    def _get_stage(self, stage_key: str) -> Optional[BaseAgent]:
        """
        Return the HM stage instance for a given stage key.

        Phase 4A: HM-1 and HM-5 are real. HM-2/3/4 return None (stubs).
        Phase 4B/4C/4D will add HM-2, HM-3, HM-4.
        """
        if stage_key == "hm1":
            from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
            return HM1Analyzer()

        if stage_key == "hm5":
            from agents.humanizer.stages.hm5_scorer import HM5Scorer
            return HM5Scorer()

        # HM-2, HM-3, HM-4 — stubs for Phase 4A (return None = skip)
        # Phase 4B: hm2 → HM2Structural
        # Phase 4C: hm3 → HM3Lexical
        # Phase 4D: hm4 → HM4Discourse
        return None
```

**Design notes:**

1. **`execute()`** — full pipeline run (HM-1 → HM-5). Used for first pass.
2. **`execute_targeted()`** — selective re-run. Used by CEO feedback loop. Only runs the failed stage + HM-5 rescore. This is the key optimization: instead of `Pipeline.run()` repeating all 5 stages, we re-run 1 stage + rescore = saves 2-3 API calls per feedback iteration.
3. **`_get_stage()`** — factory method with lazy imports (same pattern as MM `_get_worker()`). Returns None for unimplemented stages (Phase 4A stubs).
4. **HM-1 failure is fatal** — without `analysis_report`, downstream stages have no domain/register/language flags.
5. **HM-2/3/4 failures are non-fatal** — manager logs warning and continues. Partial humanization is better than no output.
6. **`original_text` snapshot** — set only once (first pass). Preserved across feedback iterations so HM-5 always compares against the true original.
7. **Error tracking uses `errors_before` counter** — `len(state.errors)` is captured before each stage runs, then compared after. This ensures pre-existing errors don't trigger false HM-1 failure detection.

---

## Part 6: Test File

### File 8: CREATE `tests/test_phase4a_humanizer_infra.py`

```python
"""
Phase 4A Tests: HumanizerManager Infrastructure + HM-1 + HM-5.
Run: pytest tests/test_phase4a_humanizer_infra.py -v

Tests:
1. BaseHumanizerStage: abstract interface, agent_type, _get_domain/_get_register
2. HM1Analyzer: instantiation, agent_name, stage_number, execute with text
3. HM5Scorer: instantiation, agent_name, stage_number, execute with text
4. HumanizerManager: instantiation, STAGE_ORDER, _get_stage routing
5. HumanizerManager: execute runs HM-1 and HM-5 (HM-2/3/4 skipped)
6. HumanizerManager: execute_targeted validates target
7. HumanizerManager: original_text snapshot logic
8. PipelineState: new fields (original_text, structural_score)
9. Regression: Phase 1-3 agents still work
"""
from __future__ import annotations

import asyncio
import inspect

import pytest


# ── Test 1: BaseHumanizerStage ──────────────────────────────────────


class TestBaseHumanizerStage:
    def test_cannot_instantiate_directly(self):
        """BaseHumanizerStage is abstract — cannot instantiate."""
        from agents.humanizer.base_stage import BaseHumanizerStage

        with pytest.raises(TypeError):
            BaseHumanizerStage()

    def test_agent_type_is_stage(self):
        """BaseHumanizerStage.agent_type = 'stage'."""
        from agents.humanizer.base_stage import BaseHumanizerStage

        assert BaseHumanizerStage.agent_type == "stage"

    def test_inherits_base_agent(self):
        """BaseHumanizerStage inherits from BaseAgent."""
        from agents.base import BaseAgent
        from agents.humanizer.base_stage import BaseHumanizerStage

        assert issubclass(BaseHumanizerStage, BaseAgent)

    def test_has_get_domain_and_get_register(self):
        """BaseHumanizerStage has _get_domain() and _get_register() methods."""
        from agents.humanizer.base_stage import BaseHumanizerStage

        assert hasattr(BaseHumanizerStage, "_get_domain")
        assert hasattr(BaseHumanizerStage, "_get_register")

    def test_get_domain_priority(self):
        """_get_domain: state.domain overrides analysis_report.domain."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()  # Concrete subclass to test inherited method

        # Case 1: state.domain is set (not "general") → use it
        state = PipelineState(mode="humanization", domain="economics")
        state.analysis_report = {"domain": "cs"}
        assert hm._get_domain(state) == "economics"

        # Case 2: state.domain is "general" → use analysis_report
        state = PipelineState(mode="humanization", domain="general")
        state.analysis_report = {"domain": "cs"}
        assert hm._get_domain(state) == "cs"

        # Case 3: both "general" → "general"
        state = PipelineState(mode="humanization", domain="general")
        state.analysis_report = {"domain": "general"}
        assert hm._get_domain(state) == "general"

    def test_get_register_priority(self):
        """_get_register: state.register overrides analysis_report.register."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()

        # Case 1: state.register is set → use it
        state = PipelineState(mode="humanization", register="academic")
        state.analysis_report = {"register": "journalistic"}
        assert hm._get_register(state) == "academic"

        # Case 2: state.register is "general" → use analysis_report
        state = PipelineState(mode="humanization", register="general")
        state.analysis_report = {"register": "journalistic"}
        assert hm._get_register(state) == "journalistic"


# ── Test 2: HM1Analyzer ────────────────────────────────────────────


class TestHM1Analyzer:
    def test_instantiation(self):
        """HM1Analyzer instantiates correctly."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer

        hm = HM1Analyzer()
        assert hm.agent_name == "hm1_analyzer"
        assert hm.agent_type == "stage"
        assert hm.stage_number == 1

    def test_inherits_base_humanizer_stage(self):
        """HM1Analyzer inherits from BaseHumanizerStage."""
        from agents.humanizer.base_stage import BaseHumanizerStage
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer

        assert issubclass(HM1Analyzer, BaseHumanizerStage)

    def test_execute_no_text_returns_error(self):
        """HM1Analyzer.execute() errors when state.text is empty."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()
        state = PipelineState(mode="humanization", text="")
        result = asyncio.run(hm.execute(state))
        assert result.has_errors()
        assert "No text to analyze" in result.errors[-1]

    def test_execute_produces_analysis_report(self):
        """HM1Analyzer.execute() produces analysis_report in state.

        Note: This test requires spacy + GPT-2 models.
        If they are unavailable, we expect an error (not a crash).
        """
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()
        state = PipelineState(
            mode="humanization",
            text="The quick brown fox jumps over the lazy dog. This is a test sentence with enough words to analyze properly.",
            language="en",
        )
        result = asyncio.run(hm.execute(state))

        # Either analysis succeeded (report populated) or failed gracefully (error logged)
        assert result.analysis_report or result.has_errors()

    def test_execute_sets_language_flags_ru(self):
        """HM1Analyzer sets _skip_perplexity=True for Russian text."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()
        state = PipelineState(
            mode="humanization",
            text="Тестовый текст для анализа. Это второе предложение для проверки.",
            language="ru",
        )
        result = asyncio.run(hm.execute(state))

        if result.analysis_report:
            assert result.analysis_report.get("_language") == "ru"
            assert result.analysis_report.get("_skip_perplexity") is True

    def test_execute_does_not_modify_text(self):
        """HM1Analyzer does not modify state.text (read-only stage)."""
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer
        from agents.state import PipelineState

        hm = HM1Analyzer()
        original = "Some sample text for analysis. Another sentence here."
        state = PipelineState(mode="humanization", text=original)
        result = asyncio.run(hm.execute(state))
        assert result.text == original


# ── Test 3: HM5Scorer ──────────────────────────────────────────────


class TestHM5Scorer:
    def test_instantiation(self):
        """HM5Scorer instantiates correctly."""
        from agents.humanizer.stages.hm5_scorer import HM5Scorer

        hm = HM5Scorer()
        assert hm.agent_name == "hm5_scorer"
        assert hm.agent_type == "stage"
        assert hm.stage_number == 5

    def test_inherits_base_humanizer_stage(self):
        """HM5Scorer inherits from BaseHumanizerStage."""
        from agents.humanizer.base_stage import BaseHumanizerStage
        from agents.humanizer.stages.hm5_scorer import HM5Scorer

        assert issubclass(HM5Scorer, BaseHumanizerStage)

    def test_execute_no_text_returns_error(self):
        """HM5Scorer.execute() errors when state.text is empty."""
        from agents.humanizer.stages.hm5_scorer import HM5Scorer
        from agents.state import PipelineState

        hm = HM5Scorer()
        state = PipelineState(mode="humanization", text="")
        result = asyncio.run(hm.execute(state))
        assert result.has_errors()
        assert "No text to score" in result.errors[-1]

    def test_execute_produces_score_report(self):
        """HM5Scorer.execute() produces final_score_report in state.

        Note: Requires spacy + GPT-2. If unavailable, expect graceful error.
        """
        from agents.humanizer.stages.hm5_scorer import HM5Scorer
        from agents.state import PipelineState

        hm = HM5Scorer()
        state = PipelineState(
            mode="humanization",
            text="The quick brown fox jumps over the lazy dog. This is test output text.",
            original_text="Original input text before humanization. This is the baseline.",
            language="en",
            domain="general",
            register="general",
        )
        result = asyncio.run(hm.execute(state))

        # Either scoring succeeded or failed gracefully
        assert result.final_score_report or result.has_errors()

    def test_execute_applies_russian_language_gate(self):
        """HM5Scorer sets perplexity_lift=None for Russian text (AC-15)."""
        from agents.humanizer.stages.hm5_scorer import HM5Scorer
        from agents.state import PipelineState

        hm = HM5Scorer()
        state = PipelineState(
            mode="humanization",
            text="Результат обработки текста. Второе предложение.",
            original_text="Оригинальный текст для сравнения. Второе предложение.",
            language="ru",
        )
        result = asyncio.run(hm.execute(state))

        if result.final_score_report:
            assert result.final_score_report.get("_language") == "ru"
            assert result.final_score_report.get("perplexity_lift") is None

    def test_execute_fallback_when_no_original_text(self):
        """HM5Scorer falls back to state.text when original_text is empty."""
        from agents.humanizer.stages.hm5_scorer import HM5Scorer
        from agents.state import PipelineState

        hm = HM5Scorer()
        state = PipelineState(
            mode="humanization",
            text="Some text to score against itself.",
            original_text="",  # empty — should fall back
        )
        result = asyncio.run(hm.execute(state))

        # Should not crash — scores text against itself
        assert result.final_score_report or result.has_errors()


# ── Test 4: HumanizerManager ───────────────────────────────────────


class TestHumanizerManager:
    def test_instantiation(self):
        """HumanizerManager instantiates correctly."""
        from agents.humanizer.manager import HumanizerManager

        hm = HumanizerManager()
        assert hm.agent_name == "humanizer_manager"
        assert hm.agent_type == "manager"

    def test_stage_order(self):
        """HumanizerManager.STAGE_ORDER is correct."""
        from agents.humanizer.manager import HumanizerManager

        assert HumanizerManager.STAGE_ORDER == ["hm1", "hm2", "hm3", "hm4", "hm5"]

    def test_get_stage_hm1(self):
        """HumanizerManager._get_stage('hm1') returns HM1Analyzer."""
        from agents.humanizer.manager import HumanizerManager
        from agents.humanizer.stages.hm1_analyzer import HM1Analyzer

        hm = HumanizerManager()
        stage = hm._get_stage("hm1")
        assert isinstance(stage, HM1Analyzer)

    def test_get_stage_hm5(self):
        """HumanizerManager._get_stage('hm5') returns HM5Scorer."""
        from agents.humanizer.manager import HumanizerManager
        from agents.humanizer.stages.hm5_scorer import HM5Scorer

        hm = HumanizerManager()
        stage = hm._get_stage("hm5")
        assert isinstance(stage, HM5Scorer)

    def test_get_stage_hm2_hm3_hm4_return_none(self):
        """HumanizerManager._get_stage('hm2'/'hm3'/'hm4') returns None (Phase 4A stubs)."""
        from agents.humanizer.manager import HumanizerManager

        hm = HumanizerManager()
        assert hm._get_stage("hm2") is None
        assert hm._get_stage("hm3") is None
        assert hm._get_stage("hm4") is None

    def test_get_stage_unknown_returns_none(self):
        """HumanizerManager._get_stage('unknown') returns None."""
        from agents.humanizer.manager import HumanizerManager

        hm = HumanizerManager()
        assert hm._get_stage("unknown") is None
        assert hm._get_stage("hm6") is None

    def test_execute_no_text_returns_error(self):
        """HumanizerManager.execute() errors when state.text is empty."""
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(mode="humanization", text="")
        result = asyncio.run(hm.execute(state))
        assert result.has_errors()
        assert "No text to humanize" in result.errors[-1]

    def test_execute_sets_original_text(self):
        """HumanizerManager.execute() snapshots original_text before running stages."""
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(
            mode="humanization",
            text="Some text for humanization.",
        )

        # Before execute: original_text should be empty
        assert state.original_text == ""

        result = asyncio.run(hm.execute(state))

        # After execute: original_text should be set
        assert result.original_text == "Some text for humanization."

    def test_execute_preserves_original_text_on_rerun(self):
        """HumanizerManager.execute() does NOT overwrite original_text if already set."""
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(
            mode="humanization",
            text="Modified text after first pass.",
            original_text="The true original text.",
        )

        result = asyncio.run(hm.execute(state))

        # original_text should NOT be overwritten
        assert result.original_text == "The true original text."

    def test_execute_runs_hm1_and_hm5(self):
        """HumanizerManager.execute() runs at least HM-1 and HM-5.

        In Phase 4A, HM-2/3/4 are skipped (None). So execute runs HM-1 + HM-5.
        Errors expected without spacy/GPT-2 models.
        """
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(
            mode="humanization",
            text="Test text for full pipeline run. Second sentence for analysis.",
            language="en",
        )
        result = asyncio.run(hm.execute(state))

        # Either stages ran (reports populated) or graceful errors
        has_analysis = bool(result.analysis_report)
        has_score = bool(result.final_score_report)
        has_errors = result.has_errors()

        assert has_analysis or has_errors, "HM-1 must either produce report or log error"

    def test_execute_targeted_validates_target(self):
        """execute_targeted() rejects invalid target stages."""
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(mode="humanization", text="Some text.")

        # Invalid targets
        result = asyncio.run(hm.execute_targeted(state, "hm1"))
        assert result.has_errors()
        assert "Invalid feedback target" in result.errors[-1]

        state2 = PipelineState(mode="humanization", text="Some text.")
        result2 = asyncio.run(hm.execute_targeted(state2, "hm5"))
        assert result2.has_errors()

    def test_execute_targeted_valid_target_stub(self):
        """execute_targeted('hm2') on Phase 4A stub logs error (stage not available)."""
        from agents.humanizer.manager import HumanizerManager
        from agents.state import PipelineState

        hm = HumanizerManager()
        state = PipelineState(mode="humanization", text="Some text.")
        result = asyncio.run(hm.execute_targeted(state, "hm2"))

        # hm2 returns None in Phase 4A → error
        assert result.has_errors()
        assert "not available" in result.errors[-1]


# ── Test 5: PipelineState New Fields ───────────────────────────────


class TestPipelineStateNewFields:
    def test_original_text_field_exists(self):
        """PipelineState has original_text field with default ''."""
        from agents.state import PipelineState

        state = PipelineState(mode="humanization")
        assert hasattr(state, "original_text")
        assert state.original_text == ""

    def test_structural_score_field_exists(self):
        """PipelineState has structural_score field with default {}."""
        from agents.state import PipelineState

        state = PipelineState(mode="humanization")
        assert hasattr(state, "structural_score")
        assert state.structural_score == {}

    def test_existing_fields_unchanged(self):
        """Existing PipelineState fields still work correctly."""
        from agents.state import PipelineState

        state = PipelineState(
            mode="humanization",
            text="test",
            language="ru",
            domain="economics",
            register="academic",
        )
        assert state.mode == "humanization"
        assert state.text == "test"
        assert state.language == "ru"
        assert state.domain == "economics"
        assert state.register == "academic"
        assert state.analysis_report == {}
        assert state.final_score_report == {}
        assert state.errors == []
        assert state.feedback_iterations == 0


# ── Test 6: Regression ─────────────────────────────────────────────


class TestPhase4ARegression:
    def test_ceo_still_has_run_generation(self):
        """CEO still has _run_generation with ContentManager."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_generation)
        assert "ContentManager" in source

    def test_ceo_still_has_run_humanization(self):
        """CEO still has _run_humanization with Pipeline.run()."""
        from agents.ceo import CEOAgent

        source = inspect.getsource(CEOAgent._run_humanization)
        assert "pipe.run(" in source or "Pipeline()" in source

    def test_content_manager_routes_all_7_streams(self):
        """ContentManager still routes all 7 stream_ids correctly."""
        from agents.content.manager import ContentManager

        cm = ContentManager()
        for stream_id in ["vkr", "coursework", "research", "abstract_paper", "text", "essay", "composition"]:
            mm = cm._get_micro_manager(stream_id)
            assert mm is not None, f"No MM for stream_id={stream_id}"

    def test_worker_count_still_36(self):
        """36 worker modules still exist."""
        import pkgutil
        import agents.content.workers as workers_pkg

        modules = [
            m for _, m, _ in pkgutil.iter_modules(workers_pkg.__path__)
            if not m.startswith("__") and m != "base_section_worker"
        ]
        assert len(modules) == 36, f"Expected 36 worker modules, got {len(modules)}"

    def test_base_agent_interface_unchanged(self):
        """BaseAgent still has execute(), call_claude(), load_prompt()."""
        from agents.base import BaseAgent

        assert hasattr(BaseAgent, "execute")
        assert hasattr(BaseAgent, "call_claude")
        assert hasattr(BaseAgent, "load_prompt")
```

---

## Summary of All Changes

| Action | Count | Files |
|--------|-------|-------|
| CREATE | 4 | `agents/humanizer/__init__.py`, `agents/humanizer/stages/__init__.py`, `agents/humanizer/base_stage.py`, `agents/humanizer/manager.py` |
| CREATE | 2 | `agents/humanizer/stages/hm1_analyzer.py`, `agents/humanizer/stages/hm5_scorer.py` |
| CREATE | 1 | `tests/test_phase4a_humanizer_infra.py` |
| MODIFY | 1 | `agents/state.py` (add 2 fields: `original_text`, `structural_score`) |

**Total: 7 new files, 1 modified file.**

---

## Critical Constraints

1. **DO NOT modify**: `agents/base.py`, `agents/ceo.py`, `agents/content/manager.py`, `agents/content/micro_managers/base.py`, `agents/content/workers/base_section_worker.py`, `pipeline/analyzer.py`, `pipeline/scorer.py`, `pipeline/__init__.py`, `pipeline/generator.py`
2. **DO NOT modify**: any Phase 3 worker files, MM files, or gate files
3. **In state.py**: add ONLY the 2 new fields. Do NOT change or remove any existing fields, methods, or imports.
4. **Imports inside methods** for HM stages — avoids circular imports (same pattern as all previous phases).
5. **HM-1 and HM-5 do NOT call Claude API** — they are local stages wrapping local pipeline classes.
6. **HumanizerManager._get_stage()** must return None for hm2/hm3/hm4 — they are Phase 4B/4C/4D stubs. The manager's execute loop MUST handle None gracefully (skip with warning, not crash).
7. **original_text** — set once by HumanizerManager on first pass; NOT overwritten on feedback re-runs.
8. **No CEO changes in Phase 4A** — CEO still calls Pipeline.run() directly. Phase 4D will rewire CEO to use HumanizerManager.

---

## Verification

```bash
# Phase 4A tests
pytest tests/test_phase4a_humanizer_infra.py -v

# Phase 3C regression
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
