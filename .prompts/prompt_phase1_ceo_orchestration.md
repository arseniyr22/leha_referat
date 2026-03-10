# Phase 1: CEO Agent + Оркестрация

## Контекст

Проект AI Anti-Anti Plag. Phase 0 завершена: `agents/base.py` (BaseAgent ABC), `agents/state.py` (PipelineState, CostReport), `agents/config.py` (AgentConfig, load_agent_config). 13 foundation тестов проходят.

Существующий pipeline (`pipeline/__init__.py`) содержит:
- `Pipeline.run(text, domain_override, register_override, language)` → (output_text, score_report) — humanization mode
- `Pipeline.run_from_params(params)` → (output_text, score_report) — generation mode (Phase 0A/B → Stages 1-5)
- 5 стадий: Analyzer → StructuralRewriter → LexicalEnricher → DiscourseShaper → Scorer

**Принцип**: wrap, не rewrite. CEO Agent вызывает `Pipeline.run()` и `Pipeline.run_from_params()` как есть. 0 изменений в `pipeline/`.

---

## Что создать

### Файловая структура

```
agents/
├── ceo.py                     # CEOAgent: routing + feedback escalation
├── gates/
│   ├── __init__.py            # Gates package
│   └── content_qa.py          # ContentQAGate: post-Phase-0 validation
└── prompts/
    └── ceo.md                 # CEO system prompt (routing logic description)

tests/
└── test_phase1_ceo.py         # 8+ tests
```

---

## Файл 1: `agents/ceo.py`

### Требования

CEO Agent — главный маршрутизатор системы. Принимает PipelineState, решает маршрут, выполняет pipeline, управляет feedback loop.

```python
from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState
from agents.config import load_agent_config


class CEOAgent(BaseAgent):
    """
    CEO Agent — top-level orchestrator of the multi-agent system.

    Responsibilities:
    1. Route request based on state.mode: generation → Content + Humanize + Export
                                          humanization → Humanize + Export
    2. Execute pipeline stages via existing Pipeline class (wrap, not rewrite)
    3. Manage feedback loop: if HM-5 fails → route to HM-2/3/4 (max 2 iterations)
    4. Escalation: after 2 failed iterations → partial accept with full score_report
    5. Track costs via state.cost_report

    This agent does NOT implement Stages 1-5 itself. It delegates to Pipeline.run()
    and Pipeline.run_from_params() from the existing pipeline/ package.
    """

    agent_name = "ceo"
    agent_type = "ceo"

    MAX_FEEDBACK_ITERATIONS = 2  # From IMPLEMENTATION_PLAN GAP 3

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Main entry point.

        Routes:
        - mode == "generation": Phase 0 (sources + generate) → Stages 1-5 → Export
        - mode == "humanization": Stages 1-5 → Export

        Feedback loop:
        - After Stages 1-5, check score_report for failures
        - If failures found AND iterations < MAX_FEEDBACK_ITERATIONS:
            → determine_feedback_route() → re-run Pipeline.run() with state.text
        - If iterations >= MAX_FEEDBACK_ITERATIONS → escalate (partial accept)
        """
        t0 = time.time()
        config = load_agent_config()

        logger.info(
            f"[CEO] Starting | mode={state.mode} | language={state.language} | "
            f"domain={state.domain} | stream_id={state.stream_id}"
        )

        try:
            if state.mode == "generation":
                state = await self._run_generation(state)
            elif state.mode == "humanization":
                state = await self._run_humanization(state)
            else:
                state.add_error(self.agent_name, f"Unknown mode: {state.mode}")
                return state

        except Exception as e:
            state.add_error(self.agent_name, f"Pipeline execution failed: {e}")
            logger.error(f"[CEO] Fatal error: {e}")

        elapsed = time.time() - t0
        logger.info(
            f"[CEO] Complete | elapsed={elapsed:.1f}s | "
            f"errors={len(state.errors)} | "
            f"feedback_iterations={state.feedback_iterations}"
        )

        return state

    async def _run_generation(self, state: PipelineState) -> PipelineState:
        """
        Generation mode: Phase 0 (sources + generate) → Stages 1-5.

        Uses Pipeline.run_from_params() which internally:
        1. Calls SourceFinder (Phase 0A)
        2. Calls AcademicGenerator (Phase 0B)
        3. Runs Stages 1-5 on generated text
        """
        from pipeline import Pipeline
        from pipeline.generator import GenerationParams

        logger.info("[CEO] Generation mode: Phase 0 → Stages 1-5")

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

        # Content QA gate: check Phase 0 structural requirements
        state = await self._content_qa_check(state)

        # Feedback loop on humanization quality
        state = await self._feedback_loop(state)

        return state

    async def _run_humanization(self, state: PipelineState) -> PipelineState:
        """
        Humanization mode: Stages 1-5 on existing text.

        Uses Pipeline.run() which internally runs all 5 stages.
        """
        from pipeline import Pipeline

        if not state.text:
            state.add_error(self.agent_name, "Humanization mode requires text input")
            return state

        logger.info(f"[CEO] Humanization mode: {state.word_count()} words input")

        pipe = Pipeline()

        # Set language for pipeline (it reads _current_language)
        pipe._current_language = state.language

        output_text, score_report = pipe.run(
            text=state.text,
            verbose=True,
            domain_override=state.domain if state.domain != "general" else None,
            register_override=state.register if state.register != "general" else None,
        )

        state.text = output_text
        state.final_score_report = score_report

        # Feedback loop
        state = await self._feedback_loop(state)

        return state

    async def _feedback_loop(self, state: PipelineState) -> PipelineState:
        """
        Feedback loop: check score_report, re-run if needed.

        Algorithm (from IMPLEMENTATION_PLAN GAP 3):
        1. Check score_report for hard/soft failures
        2. If all pass → return
        3. If failures AND iterations < MAX → determine route → re-run pipeline
        4. If iterations >= MAX → escalate (log warning, partial accept)
        """
        from pipeline import Pipeline

        while state.feedback_iterations < self.MAX_FEEDBACK_ITERATIONS:
            route = self._determine_feedback_route(state.final_score_report)

            if route is None:
                logger.info("[CEO] Feedback loop: all metrics pass")
                return state

            state.feedback_iterations += 1
            state.feedback_target = route
            state.feedback_from_qa = {
                "iteration": state.feedback_iterations,
                "route": route,
                "failed_metrics": self._get_failed_metrics(state.final_score_report),
            }

            logger.warning(
                f"[CEO] Feedback iteration {state.feedback_iterations}: "
                f"routing to {route} | failed metrics: "
                f"{state.feedback_from_qa['failed_metrics']}"
            )

            # Re-run full pipeline on current text
            # In future phases, this will route to specific HM stages (HM-2/3/4)
            # For Phase 1, we re-run the full pipeline as a simple feedback mechanism
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

        # Max iterations reached — escalate
        if self._determine_feedback_route(state.final_score_report) is not None:
            logger.warning(
                f"[CEO] Escalation: max {self.MAX_FEEDBACK_ITERATIONS} iterations reached. "
                f"Partial accept with remaining failures."
            )
            state.add_error(
                self.agent_name,
                f"Feedback loop exhausted after {self.MAX_FEEDBACK_ITERATIONS} iterations. "
                f"Remaining failures: {self._get_failed_metrics(state.final_score_report)}"
            )

        return state

    def _determine_feedback_route(self, score_report: dict) -> Optional[str]:
        """
        Determine which HM stage to route feedback to.

        Uses priority-weighted routing from IMPLEMENTATION_PLAN GAP 3:
        - Collect all failed metrics with priorities
        - Group by route (hm2/hm3/hm4)
        - Return route with highest weighted score
        - Return None if all pass

        Route mapping:
        - hm2: structural issues (triplets, scaffold, connectors, paragraph CV)
        - hm3: lexical issues (P7 vocab, hedging, attribution, pattern elimination)
        - hm4: voice issues (burstiness, coherence, perplexity, generalization endings)
        """
        if not score_report:
            return None

        # Routing table: metric → (route, priority)
        # Priority: P1=highest(5), P2=4, P3=3, P4=2, P5=1
        ROUTING_TABLE = {
            "triplet_count":                    ("hm2", 5),
            "announcement_opener_count":        ("hm2", 5),
            "para_ending_generalization_count":  ("hm4", 4),
            "paragraph_cv":                     ("hm2", 3),
            "section_cv":                       ("hm2", 3),
            "sentence_cv":                      ("hm4", 2),
            "p7_violation_count":               ("hm3", 3),
            "modal_hedging_on_results":         ("hm3", 3),
            "but_however_ratio":                ("hm2", 2),
            "no_odnako_ratio":                  ("hm2", 2),   # RU equivalent of but_however (AC-12)
            "connector_density_per_page":       ("hm2", 2),
            "pattern_elimination_rate":         ("hm3", 3),
            "perplexity_lift":                  ("hm4", 1),
            "coherence_score":                  ("hm4", 4),
            "length_reduction_ratio":           ("hm3", 1),
            "scaffold_signals_count":           ("hm2", 4),
            "attributive_passive_count":        ("hm3", 3),
        }

        # Threshold checks: metric_name → pass condition
        THRESHOLDS = {
            "triplet_count":                    lambda v: v is None or v == 0,
            "announcement_opener_count":        lambda v: v is None or v == 0,
            "para_ending_generalization_count":  lambda v: v is None or v == 0,
            "attributive_passive_count":        lambda v: v is None or v == 0,
            "scaffold_signals_count":           lambda v: v is None or v == 0,
            "p7_violation_count":               lambda v: v is None or v == 0,
            "modal_hedging_on_results":         lambda v: v is None or v == 0,
            "paragraph_cv":                     lambda v: v is not None and v >= 0.50,
            "section_cv":                       lambda v: v is not None and v >= 0.30,
            "sentence_cv":                      lambda v: v is not None and v >= 0.45,
            "but_however_ratio":                lambda v: v is None or v >= 2.0,  # None = RU, skip
            "no_odnako_ratio":                  lambda v: v is None or v >= 2.0,  # RU equivalent (AC-12)
            "connector_density_per_page":       lambda v: v is None or v <= 1.2,
            "pattern_elimination_rate":         lambda v: v is None or v >= 0.85,
            "perplexity_lift":                  lambda v: v is None or v >= 1.5,  # None = RU, skip
            "coherence_score":                  lambda v: v is None or v >= 0.80,
            "length_reduction_ratio":           lambda v: v is None or v <= 0.90,
        }

        # Collect failures
        route_scores: dict[str, int] = {"hm2": 0, "hm3": 0, "hm4": 0}

        for metric, (route, priority) in ROUTING_TABLE.items():
            value = score_report.get(metric)
            threshold_fn = THRESHOLDS.get(metric)

            if threshold_fn and not threshold_fn(value):
                route_scores[route] += priority

        # If no failures, return None
        if all(v == 0 for v in route_scores.values()):
            return None

        return max(route_scores, key=route_scores.get)

    def _get_failed_metrics(self, score_report: dict) -> list[str]:
        """Return list of metric names that failed their thresholds."""
        if not score_report:
            return []

        # Thresholds identical to _determine_feedback_route — extracted here
        # because _get_failed_metrics is a reporting utility, not a routing method.
        # In Phase 4+, both will use a shared class-level THRESHOLDS constant.
        THRESHOLDS = {
            "triplet_count":                    lambda v: v is None or v == 0,
            "announcement_opener_count":        lambda v: v is None or v == 0,
            "para_ending_generalization_count":  lambda v: v is None or v == 0,
            "attributive_passive_count":        lambda v: v is None or v == 0,
            "scaffold_signals_count":           lambda v: v is None or v == 0,
            "p7_violation_count":               lambda v: v is None or v == 0,
            "modal_hedging_on_results":         lambda v: v is None or v == 0,
            "paragraph_cv":                     lambda v: v is not None and v >= 0.50,
            "section_cv":                       lambda v: v is not None and v >= 0.30,
            "sentence_cv":                      lambda v: v is not None and v >= 0.45,
            "but_however_ratio":                lambda v: v is None or v >= 2.0,
            "no_odnako_ratio":                  lambda v: v is None or v >= 2.0,  # RU equivalent (AC-12)
            "connector_density_per_page":       lambda v: v is None or v <= 1.2,
            "pattern_elimination_rate":         lambda v: v is None or v >= 0.85,
            "perplexity_lift":                  lambda v: v is None or v >= 1.5,
            "coherence_score":                  lambda v: v is None or v >= 0.80,
            "length_reduction_ratio":           lambda v: v is None or v <= 0.90,
        }

        failed = []
        for metric, threshold_fn in THRESHOLDS.items():
            value = score_report.get(metric)
            if not threshold_fn(value):
                failed.append(f"{metric}={value}")
        return failed

    async def _content_qa_check(self, state: PipelineState) -> PipelineState:
        """
        Run ContentQAGate on Phase 0 output (generation mode only).
        Checks: announcement openers=0, triplets=0, Block 12=0, viz count >= minimum.
        """
        from agents.gates.content_qa import ContentQAGate

        gate = ContentQAGate()
        state = await gate.execute(state)
        return state
```

### Ключевые решения

1. **CEO вызывает Pipeline напрямую** — `Pipeline.run()` и `Pipeline.run_from_params()` используются как есть. CEO = thin orchestration wrapper.
2. **Feedback loop в Phase 1 = полный re-run** — в будущих фазах (Phase 4-5) feedback будет маршрутизироваться к конкретным HM stages. Сейчас: re-run всего pipeline (простой, но работающий механизм).
3. **ROUTING_TABLE и THRESHOLDS из GAP 3** — полная таблица маршрутизации из IMPLEMENTATION_PLAN, включая все 17 метрик (16 из GAP 3 + no_odnako_ratio для AC-12) с приоритетами P1-P5.
4. **None-safe threshold checks** — для русского языка метрики perplexity/but_however_ratio могут быть None; threshold_fn возвращает True для None (= skip check).
5. **Pipeline._current_language** — существующий механизм передачи языка в Pipeline (строка 159 pipeline/__init__.py).

---

## Файл 2: `agents/gates/__init__.py`

```python
"""
Gate agents for the multi-agent pipeline.

Gates validate state at critical transitions:
- ContentQAGate: validates Phase 0 output before humanization
- QA gates (Phase 5): validate after each HM stage
"""
```

---

## Файл 3: `agents/gates/content_qa.py`

### Требования

ContentQAGate проверяет output Phase 0 (генерация) перед передачей в humanization pipeline.

```python
from __future__ import annotations

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


class ContentQAGate(BaseAgent):
    """
    Content QA Gate — validates Phase 0 generation output.

    Checks (from IMPLEMENTATION_PLAN Phase 1):
    1. Announcement openers = 0
    2. Triplet instances = 0
    3. Block 12 violations = 0
    4. Visualization count >= stream minimum (БЛОК 16.2)

    If hard failures detected → adds warnings to state.errors
    (actual re-generation is handled by Content Manager in Phase 2).
    In Phase 1, this gate only REPORTS — it does not trigger re-generation.
    """

    agent_name = "content_qa_gate"
    agent_type = "gate"

    # БЛОК 16.2 visualization minimums
    VIZ_MINIMUMS = {
        "vkr": {"bachelor": 5, "master": 8, "specialist": 5, "postgraduate": 10},
        "coursework": {"default": 3},
        "research": {"default": 3},
        "abstract_paper": {"default": 1},
        "text": {"default": 0},
        "essay": {"default": 0},
        "composition": {"default": 0},
    }

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Validate Phase 0 output quality.

        Reads metrics from state.final_score_report (populated by Pipeline.run_from_params).
        Reports violations as warnings — does not block pipeline.
        """
        if state.mode != "generation":
            return state

        report = state.final_score_report
        if not report:
            logger.warning("[ContentQA] No score report available — skipping QA")
            return state

        violations = []

        # Check 1: Announcement openers
        opener_count = report.get("announcement_opener_count", 0)
        if opener_count and opener_count > 0:
            violations.append(f"announcement_openers={opener_count} (target: 0)")

        # Check 2: Triplet instances
        triplet_count = report.get("triplet_count", 0)
        if triplet_count and triplet_count > 0:
            violations.append(f"triplets={triplet_count} (target: 0)")

        # Check 3: Block 12 violations (structural patterns)
        block12 = report.get("block12_violations", 0)
        if block12 and block12 > 0:
            violations.append(f"block12_violations={block12} (target: 0)")

        # Check 4: Visualization count
        viz_count = report.get("generation", {}).get("viz_count", None)
        if viz_count is not None:
            total_viz = viz_count if isinstance(viz_count, int) else viz_count.get("total", 0)
            minimum = self._get_viz_minimum(state.stream_id, state.level)
            if total_viz < minimum:
                violations.append(
                    f"visualizations={total_viz} (minimum: {minimum} for {state.stream_id}/{state.level})"
                )

        if violations:
            logger.warning(f"[ContentQA] {len(violations)} violations found: {violations}")
            for v in violations:
                state.add_error(self.agent_name, f"Content QA violation: {v}")
        else:
            logger.info("[ContentQA] All checks passed")

        return state

    def _get_viz_minimum(self, stream_id: str, level: str) -> int:
        """Get visualization minimum from БЛОК 16.2 table."""
        stream_mins = self.VIZ_MINIMUMS.get(stream_id, {"default": 0})
        return stream_mins.get(level, stream_mins.get("default", 0))
```

### Ключевые решения

1. **Gate только REPORTING в Phase 1** — ContentQAGate отмечает нарушения через `state.add_error()`, но не блокирует pipeline. Полная re-generation будет в Phase 2-3 когда появится ContentManager.
2. **VIZ_MINIMUMS из БЛОК 16.2** — VKR bachelor: 5, master: 8; coursework: 3; etc.
3. **Гибкий чтение viz_count** — из `score_report["generation"]["viz_count"]` (может быть int или dict с total/tables/figures).

---

## Файл 4: `agents/prompts/ceo.md`

```markdown
# CEO Agent — Routing & Orchestration

You are the CEO agent of the AI Anti-Anti Plag system.
Your role is to route requests and manage quality feedback.

## Routing Rules

### Generation Mode (topic → text → humanized output)
1. Receive topic, stream_id, language, domain, level
2. Execute Phase 0: SourceFinder → AcademicGenerator
3. Run Content QA Gate
4. Execute Stages 1-5: Humanization pipeline
5. Check score report → feedback loop if needed
6. Export: .txt + .docx + score_report.json

### Humanization Mode (existing text → humanized output)
1. Receive text, language, domain, register
2. Execute Stages 1-5: Humanization pipeline
3. Check score report → feedback loop if needed
4. Export: .txt + .docx + score_report.json

## Feedback Loop Rules

- Maximum 2 iterations
- Route to HM-2 for: structural issues (triplets, scaffold, connectors, paragraph CV)
- Route to HM-3 for: lexical issues (P7 vocab, hedging, attribution)
- Route to HM-4 for: voice issues (burstiness, coherence, generalization endings)
- After 2 failed iterations: partial accept with full score report
```

---

## Файл 5: `tests/test_phase1_ceo.py`

### Требования

Минимум 8 тестов. НЕ мокать Pipeline целиком — тесты проверяют routing, feedback logic, ContentQA gate.

```python
"""
Phase 1 CEO Agent Tests.
Run: pytest tests/test_phase1_ceo.py -v
"""
from __future__ import annotations

import pytest


# ── Test 1: CEO routing ─────────────────────────────────────────────────

class TestCEORouting:
    def test_ceo_instantiation(self):
        """CEOAgent can be instantiated."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()
        assert ceo.agent_name == "ceo"
        assert ceo.agent_type == "ceo"

    def test_ceo_is_base_agent(self):
        """CEOAgent inherits from BaseAgent."""
        from agents.ceo import CEOAgent
        from agents.base import BaseAgent
        ceo = CEOAgent()
        assert isinstance(ceo, BaseAgent)

    def test_unknown_mode_produces_error(self):
        """Unknown mode adds error to state."""
        import asyncio
        from agents.ceo import CEOAgent
        from agents.state import PipelineState

        ceo = CEOAgent()
        state = PipelineState(mode="invalid_mode")
        result = asyncio.run(ceo.execute(state))
        assert result.has_errors()
        assert "Unknown mode" in result.errors[0]

    def test_humanization_without_text_produces_error(self):
        """Humanization mode with empty text adds error."""
        import asyncio
        from agents.ceo import CEOAgent
        from agents.state import PipelineState

        ceo = CEOAgent()
        state = PipelineState(mode="humanization", text="")
        result = asyncio.run(ceo.execute(state))
        assert result.has_errors()
        assert "requires text input" in result.errors[0]


# ── Test 2: Feedback routing logic ───────────────────────────────────────

class TestFeedbackRouting:
    def test_all_pass_returns_none(self):
        """When all metrics pass, route is None."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "scaffold_signals_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route is None

    def test_structural_failures_route_to_hm2(self):
        """Structural failures (triplets, scaffold) route to HM-2."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 3,           # FAIL → hm2 (P1=5)
            "announcement_opener_count": 2, # FAIL → hm2 (P1=5)
            "scaffold_signals_count": 1,   # FAIL → hm2 (P2=4)
            # Everything else passes:
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route == "hm2"

    def test_lexical_failures_route_to_hm3(self):
        """Lexical failures (P7, hedging) route to HM-3."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "scaffold_signals_count": 0,
            "para_ending_generalization_count": 0,
            "p7_violation_count": 5,             # FAIL → hm3 (P3=3)
            "modal_hedging_on_results": 3,       # FAIL → hm3 (P3=3)
            "attributive_passive_count": 2,      # FAIL → hm3 (P3=3)
            "pattern_elimination_rate": 0.60,    # FAIL → hm3 (P3=3)
            # Everything else passes:
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": 2.5,
            "connector_density_per_page": 0.8,
            "perplexity_lift": 1.8,
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route == "hm3"

    def test_russian_skips_perplexity_and_but_however(self):
        """Russian metrics (perplexity=None, but_however=None) are skipped."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()

        score_report = {
            "triplet_count": 0,
            "announcement_opener_count": 0,
            "para_ending_generalization_count": 0,
            "attributive_passive_count": 0,
            "scaffold_signals_count": 0,
            "p7_violation_count": 0,
            "modal_hedging_on_results": 0,
            "paragraph_cv": 0.55,
            "section_cv": 0.35,
            "sentence_cv": 0.50,
            "but_however_ratio": None,           # RU → skip
            "no_odnako_ratio": 2.5,              # RU equivalent active
            "connector_density_per_page": 0.8,
            "pattern_elimination_rate": 0.90,
            "perplexity_lift": None,             # RU → skip
            "coherence_score": 0.85,
            "length_reduction_ratio": 0.85,
        }

        route = ceo._determine_feedback_route(score_report)
        assert route is None  # No failures

    def test_empty_score_report_returns_none(self):
        """Empty score report returns None (no failures detected)."""
        from agents.ceo import CEOAgent
        ceo = CEOAgent()
        assert ceo._determine_feedback_route({}) is None
        assert ceo._determine_feedback_route(None) is None


# ── Test 3: ContentQA Gate ───────────────────────────────────────────────

class TestContentQAGate:
    def test_gate_instantiation(self):
        """ContentQAGate can be instantiated."""
        from agents.gates.content_qa import ContentQAGate
        gate = ContentQAGate()
        assert gate.agent_name == "content_qa_gate"
        assert gate.agent_type == "gate"

    def test_gate_skips_humanization_mode(self):
        """ContentQAGate skips if mode is humanization."""
        import asyncio
        from agents.gates.content_qa import ContentQAGate
        from agents.state import PipelineState

        gate = ContentQAGate()
        state = PipelineState(mode="humanization")
        result = asyncio.run(gate.execute(state))
        assert not result.has_errors()

    def test_viz_minimum_lookup(self):
        """Visualization minimums match БЛОК 16.2."""
        from agents.gates.content_qa import ContentQAGate
        gate = ContentQAGate()
        assert gate._get_viz_minimum("vkr", "bachelor") == 5
        assert gate._get_viz_minimum("vkr", "master") == 8
        assert gate._get_viz_minimum("coursework", "bachelor") == 3
        assert gate._get_viz_minimum("composition", "bachelor") == 0
        assert gate._get_viz_minimum("unknown_stream", "bachelor") == 0


# ── Test 4: Phase 0 not broken ──────────────────────────────────────────

class TestPhase0Intact:
    def test_foundation_imports(self):
        """Phase 0 imports still work after Phase 1 additions."""
        from agents.base import BaseAgent
        from agents.state import PipelineState, CostReport
        from agents.config import load_agent_config, AgentConfig
        assert True  # If we get here, imports work

    def test_pipeline_imports(self):
        """Existing pipeline imports still work."""
        from pipeline import Pipeline, load_config
        pipe = Pipeline()
        assert hasattr(pipe, "run")
        assert hasattr(pipe, "run_from_params")
```

---

## Правила создания

1. **НЕ трогать** ни один файл в `pipeline/`, `prompts/`, `config.yaml`, `tests/test_pipeline.py`, `tests/test_agents_foundation.py`.
2. **НЕ трогать** файлы Phase 0: `agents/__init__.py`, `agents/base.py`, `agents/state.py`, `agents/config.py`.
3. **Type hints** на всех функциях и параметрах.
4. **Docstrings** на всех классах и публичных методах.
5. **`from __future__ import annotations`** в каждом новом .py файле.
6. **loguru** для логирования.
7. **Не добавлять** новые зависимости.

---

## Верификация после создания

1. Проверить что все файлы созданы: `agents/ceo.py`, `agents/gates/__init__.py`, `agents/gates/content_qa.py`, `agents/prompts/ceo.md`
2. Проверить что `tests/test_phase1_ceo.py` создан
3. Запустить `pytest tests/test_phase1_ceo.py -v` — все тесты должны пройти
4. Запустить `pytest tests/test_agents_foundation.py -v` — все 13 Phase 0 тестов проходят
5. Запустить `pytest tests/test_pipeline.py -v` — существующие тесты проходят (0 regressions)
6. Проверить что `from agents.ceo import CEOAgent` работает
7. Проверить что `from agents.gates.content_qa import ContentQAGate` работает
8. Проверить что `CEOAgent` наследует от `BaseAgent`
9. Проверить что `ContentQAGate` наследует от `BaseAgent`
