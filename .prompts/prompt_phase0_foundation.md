# Phase 0: Фундамент агентной системы

## Контекст

Проект AI Anti-Anti Plag имеет работающий 5-стадийный pipeline в `pipeline/` (analyzer, structural_rewriter, lexical_enricher, discourse_shaper, scorer + Phase 0A/0B генерация + formatter). Все существующие тесты проходят. Нужно создать инфраструктуру мульти-агентной системы **рядом** с pipeline/, не ломая его.

**Принцип**: wrap, не rewrite. 0 breaking changes. Новый код в `agents/`, существующий pipeline НЕ трогаем.

---

## Что создать

### Файловая структура

```
agents/
├── __init__.py          # Package init + version
├── base.py              # BaseAgent ABC
├── state.py             # PipelineState dataclass
├── config.py            # AgentConfig loader
└── prompts/             # Пустая директория для будущих промптов агентов
    └── .gitkeep

tests/
└── test_agents_foundation.py   # 5+ unit tests для Phase 0
```

---

## Файл 1: `agents/__init__.py`

```python
"""
AI Anti-anti Plag — Multi-Agent System
Architecture v3.1 FINAL: CEO → Manager → Micro Manager → Worker

This package wraps the existing pipeline/ modules in an agent orchestration layer.
The pipeline/ code is NOT modified — agents call pipeline functions via their execute() methods.
"""
__version__ = "0.1.0"
```

---

## Файл 2: `agents/base.py`

### Требования

Абстрактный базовый класс для ВСЕХ агентов системы (82 компонента).

```python
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from loguru import logger

from agents.state import PipelineState


class BaseAgent(ABC):
    """
    Abstract base for all agents in the multi-agent pipeline.

    Every agent (CEO, Manager, Stage, Worker, Gate, Service) inherits this class
    and implements execute(state) → state.

    Design principles:
    - Pure state-in, state-out: no hidden side effects
    - Each agent has a name for logging and cost tracking
    - Prompt loading from agents/prompts/ directory
    - Claude API calls go through call_claude() with retry + cost tracking
    - All errors are caught and stored in state.errors (never crash pipeline)
    """

    # Subclasses set this
    agent_name: str = "base"
    agent_type: str = "base"  # "ceo" | "manager" | "stage" | "worker" | "gate" | "service"

    def __init__(self) -> None:
        self._prompts_dir = Path(__file__).parent / "prompts"

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Main entry point. Takes PipelineState, returns modified PipelineState.
        Must be implemented by every agent.
        """
        ...

    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt template from agents/prompts/<prompt_name>.md

        Args:
            prompt_name: filename without extension (e.g., "hm2_architect")

        Returns:
            Prompt text as string

        Raises:
            FileNotFoundError: if prompt file does not exist
        """
        path = self._prompts_dir / f"{prompt_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def call_claude(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> tuple[str, dict]:
        """
        Call Claude API with retry logic and cost tracking.

        Uses cache_control=ephemeral on system prompt for Prompt Caching
        (cache hit = 10% input price — critical optimization from IMPLEMENTATION_PLAN).

        Args:
            system: System prompt text
            user: User message text
            model: Override model (default: from config.yaml pipeline.rewrite_model)
            temperature: Override temperature (default: from config.yaml)
            max_tokens: Max output tokens

        Returns:
            tuple of (response_text, usage_dict)
            usage_dict: {"input_tokens": int, "output_tokens": int, "cache_hit": bool}
        """
        import anthropic
        from pipeline import load_config

        cfg = load_config()
        model = model or cfg["pipeline"]["rewrite_model"]
        temperature = temperature if temperature is not None else cfg["pipeline"]["rewrite_temperature"]
        delay = cfg["pipeline"].get("retry_delay_seconds", 2)
        max_retries = cfg["pipeline"].get("max_retries", 3)

        client = anthropic.Anthropic()

        for attempt in range(max_retries):
            try:
                t0 = time.time()
                resp = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=[{
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": user}],
                )
                elapsed = time.time() - t0

                usage = {
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                    "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0),
                    "model": model,
                    "elapsed_seconds": round(elapsed, 2),
                }

                logger.debug(
                    f"[{self.agent_name}] API call: "
                    f"in={usage['input_tokens']} out={usage['output_tokens']} "
                    f"cache_read={usage['cache_read_input_tokens']} "
                    f"time={elapsed:.1f}s"
                )

                return resp.content[0].text, usage

            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    wait = delay * (2 ** attempt)
                    logger.warning(
                        f"[{self.agent_name}] Rate limit on attempt {attempt + 1}, "
                        f"retrying in {wait}s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"[{self.agent_name}] Rate limit exceeded after {max_retries} retries")
                    raise

            except anthropic.APIError as e:
                logger.error(f"[{self.agent_name}] API error: {e}")
                raise

        return "", {}

    def safe_execute(self, state: PipelineState) -> PipelineState:
        """
        Wrapper around execute() that catches exceptions and stores them in state.errors.
        Use this in orchestration code to prevent single-agent failures from crashing the pipeline.
        Sync-only: do NOT call from inside an async context (use `await execute()` there).
        """
        import asyncio
        try:
            return asyncio.run(self.execute(state))
        except Exception as e:
            error_msg = f"[{self.agent_name}] {type(e).__name__}: {e}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            return state

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.agent_name} type={self.agent_type}>"
```

### Ключевые решения

1. **`call_claude()` возвращает `tuple[str, dict]`** — не просто текст, а текст + usage для cost tracking (CostReport в Phase 6).
2. **`cache_control=ephemeral`** на system prompt — обязательно. Это Prompt Caching из плана ($2.70 экономия на запрос ВКР).
3. **`safe_execute()`** — для orchestration кода (CEO/Manager) чтобы один упавший worker не убил весь pipeline. Ошибка идёт в `state.errors`.
4. **`load_prompt()`** загружает из `agents/prompts/`** — отдельно от `pipeline/prompts/` (те остаются для существующего pipeline).
5. **Async `execute()`** — все агенты async для будущей параллелизации (HM-2 workers могут работать параллельно).

---

## Файл 3: `agents/state.py`

### Требования

Центральный объект состояния, передаваемый между ВСЕМИ агентами.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CostReport:
    """Tracks API usage and costs for a single pipeline run."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_api_calls: int = 0
    total_cost_usd: float = 0.0
    cache_savings_usd: float = 0.0
    cost_by_stage: dict[str, float] = field(default_factory=dict)
    calls_by_agent: dict[str, int] = field(default_factory=dict)

    def add_usage(self, agent_name: str, usage: dict) -> None:
        """
        Add a single API call's usage to the running totals.

        Args:
            agent_name: Name of the agent that made the call
            usage: Dict from BaseAgent.call_claude() with token counts
        """
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)
        self.total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)
        self.total_cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
        self.total_api_calls += 1
        self.calls_by_agent[agent_name] = self.calls_by_agent.get(agent_name, 0) + 1


@dataclass
class PipelineState:
    """
    Central state object passed between all agents.

    Every agent receives this, may modify fields relevant to its job,
    and returns it. Fields are additive — agents add data, never delete it.

    Lifecycle:
    1. Created by CEO with initial parameters (mode, stream_id, topic, etc.)
    2. Phase 0: source_list, generated_text populated
    3. Stage 1 (HM-1): analysis_report populated
    4. Stages 2-4 (HM-2/3/4): text progressively transformed
    5. Stage 5 (HM-5): final_score_report populated
    6. Export: .txt + .docx + score_report.json generated
    """

    # ── Required fields (set at creation) ──────────────────────────
    mode: str                        # "generation" | "humanization"
    text: str = ""                   # Current text (mutated by each stage)

    # ── Identity fields (set by CEO or user input) ─────────────────
    stream_id: str = ""              # vkr | coursework | research | abstract_paper | text | essay | composition
    topic: str = ""                  # Full topic string
    language: str = "en"             # "en" | "ru"
    domain: str = "general"          # it_cs | law | psychology | economics | humanities | media | general
    register: str = "general"        # academic | academic-essay | journalistic | general
    level: str = ""                  # bachelor | master | specialist | postgraduate
    research_type: str = ""          # theoretical | empirical | applied
    university: str = ""             # Optional institution name

    # ── Phase 0 output ─────────────────────────────────────────────
    source_list: Any = None          # SourceList from source_finder (Phase 0A)
    generated_sections: dict = field(default_factory=dict)  # section_id → text (Phase 0B)
    visualization_count: dict = field(default_factory=lambda: {"tables": 0, "figures": 0})

    # ── Stage 1 (HM-1) output ─────────────────────────────────────
    analysis_report: dict = field(default_factory=dict)

    # ── Stage 5 (HM-5) output ─────────────────────────────────────
    final_score_report: dict = field(default_factory=dict)

    # ── Feedback loop ──────────────────────────────────────────────
    feedback_from_qa: Optional[dict] = None     # QA gate feedback → routed to specific HM stage
    feedback_iterations: int = 0                # Count of HM-5 → HM-2/3/4 loops (max 2)
    feedback_target: str = ""                   # "hm2" | "hm3" | "hm4" — where to route feedback

    # ── Error tracking ─────────────────────────────────────────────
    errors: list[str] = field(default_factory=list)

    # ── Cost tracking ──────────────────────────────────────────────
    cost_report: CostReport = field(default_factory=CostReport)

    # ── Worker skip tracking (Smart Worker Skip from Phase 6) ──────
    skipped_workers: list[str] = field(default_factory=list)

    # ── Output paths (set by ExportManager) ────────────────────────
    output_dir: str = ""             # Path to output directory
    output_txt_path: str = ""        # Path to .txt output
    output_docx_path: str = ""       # Path to .docx output
    output_score_path: str = ""      # Path to score_report.json

    # ── Metadata ───────────────────────────────────────────────────
    pipeline_version: str = "0.1.0"

    def add_error(self, agent_name: str, error: str) -> None:
        """Add a formatted error entry."""
        self.errors.append(f"[{agent_name}] {error}")

    def has_errors(self) -> bool:
        """Check if any errors occurred during pipeline execution."""
        return len(self.errors) > 0

    def word_count(self) -> int:
        """Current text word count."""
        return len(self.text.split()) if self.text else 0
```

### Ключевые решения

1. **`mode` — единственное обязательное поле** (всё остальное имеет defaults).
2. **`CostReport` — отдельный dataclass** для чистого отделения cost tracking от остального state.
3. **`source_list: Any`** а не конкретный тип — потому что `SourceList` определён в `pipeline/source_finder.py` и мы не хотим жёсткую зависимость в state.
4. **`generated_sections: dict`** — для Phase 0B, где каждая секция генерируется отдельно (vkr_chapter_1, vkr_chapter_2, etc.).
5. **`feedback_target`** — для HM-5 feedback routing (GAP 3 из IMPLEMENTATION_PLAN_FINAL).
6. **`skipped_workers`** — для Smart Worker Skip (Phase 6 оптимизация).
7. **`visualization_count`** — для БЛОК 16.2 проверки (Phase 0 only).

---

## Файл 4: `agents/config.py`

### Требования

Загрузчик agent-specific конфигурации. Расширяет существующий config.yaml секцией `agents:`.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pipeline import load_config


@dataclass
class AgentConfig:
    """
    Agent-specific configuration loaded from config.yaml `agents:` section.

    Falls back to pipeline-level defaults if agents section is missing.
    This allows gradual migration: agents work with existing config.yaml
    and use agent-specific overrides when they exist.
    """
    # Model selection (can differ from pipeline defaults)
    rewrite_model: str = "claude-sonnet-4-6"
    analysis_model: str = "claude-haiku-4-5-20251001"

    # Temperature
    rewrite_temperature: float = 0.9
    analysis_temperature: float = 0.3

    # Retry
    max_retries: int = 3
    retry_delay_seconds: int = 2

    # Feedback loop
    max_feedback_iterations: int = 2

    # Cost guardrails
    max_cost_per_request_usd: float = 15.0    # Hard stop if exceeded
    warn_cost_threshold_usd: float = 10.0     # Warning log if exceeded

    # Smart Worker Skip
    enable_smart_skip: bool = True


def load_agent_config() -> AgentConfig:
    """
    Load agent configuration from config.yaml.

    Reads from `agents:` section if it exists.
    Falls back to `pipeline:` section defaults for model/temperature/retry.
    Returns AgentConfig with all fields populated.
    """
    cfg = load_config()

    # Start with pipeline defaults
    pipeline_cfg = cfg.get("pipeline", {})
    defaults = {
        "rewrite_model": pipeline_cfg.get("rewrite_model", "claude-sonnet-4-6"),
        "analysis_model": pipeline_cfg.get("analysis_model", "claude-haiku-4-5-20251001"),
        "rewrite_temperature": pipeline_cfg.get("rewrite_temperature", 0.9),
        "analysis_temperature": pipeline_cfg.get("analysis_temperature", 0.3),
        "max_retries": pipeline_cfg.get("max_retries", 3),
        "retry_delay_seconds": pipeline_cfg.get("retry_delay_seconds", 2),
    }

    # Override with agents section if present
    agents_cfg = cfg.get("agents", {})
    defaults.update({k: v for k, v in agents_cfg.items() if v is not None})

    return AgentConfig(**{
        k: defaults.get(k, getattr(AgentConfig, k, None))
        for k in AgentConfig.__dataclass_fields__
        if k in defaults
    })
```

### Ключевые решения

1. **Fallback к pipeline defaults** — `agents:` секции в config.yaml ещё нет, и это ОК. Агенты будут работать с текущим config.yaml без изменений.
2. **`max_cost_per_request_usd`** — hard stop для безопасности (ВКР стоит ~$9.90, лимит $15 даёт запас).
3. **`max_feedback_iterations: 2`** — из IMPLEMENTATION_PLAN: CEO escalation после 2 итераций.

---

## Файл 5: `agents/prompts/.gitkeep`

Пустой файл. Директория нужна для `BaseAgent.load_prompt()`.

---

## Файл 6: `tests/test_agents_foundation.py`

### Требования

Минимум 5 unit тестов, которые проверяют всё созданное в Phase 0.
**НЕ мокать Claude API** — тесты проверяют structure, не API.

```python
"""
Phase 0 Foundation Tests.
Run: pytest tests/test_agents_foundation.py -v
"""
from __future__ import annotations

import pytest


# ── Test 1: PipelineState creation with defaults ──────────────────────

class TestPipelineState:
    def test_creation_with_mode_only(self):
        """PipelineState can be created with just mode — all else defaults."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization")
        assert state.mode == "humanization"
        assert state.text == ""
        assert state.language == "en"
        assert state.domain == "general"
        assert state.errors == []
        assert state.feedback_iterations == 0
        assert state.skipped_workers == []

    def test_creation_generation_mode(self):
        """PipelineState for generation mode has all needed fields."""
        from agents.state import PipelineState
        state = PipelineState(
            mode="generation",
            stream_id="vkr",
            topic="Влияние цифровизации на банковский сектор РФ",
            language="ru",
            domain="economics",
            register="academic",
            level="bachelor",
        )
        assert state.mode == "generation"
        assert state.stream_id == "vkr"
        assert state.language == "ru"
        assert state.register == "academic"
        assert state.word_count() == 0  # text not yet generated

    def test_add_error(self):
        """add_error() formats and appends correctly."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization")
        state.add_error("hm2_triplet_buster", "Regex timeout on chunk 3")
        assert len(state.errors) == 1
        assert "[hm2_triplet_buster]" in state.errors[0]
        assert state.has_errors() is True

    def test_word_count(self):
        """word_count() returns correct count."""
        from agents.state import PipelineState
        state = PipelineState(mode="humanization", text="This is a test sentence with eight words total.")
        assert state.word_count() == 9  # 9 words in the sentence above


# ── Test 2: CostReport accumulation ───────────────────────────────────

class TestCostReport:
    def test_add_usage(self):
        """CostReport.add_usage() accumulates tokens and call counts."""
        from agents.state import CostReport
        report = CostReport()
        report.add_usage("hm2_scaffold_breaker", {
            "input_tokens": 1500,
            "output_tokens": 800,
            "cache_read_input_tokens": 1200,
            "cache_creation_input_tokens": 0,
        })
        assert report.total_input_tokens == 1500
        assert report.total_output_tokens == 800
        assert report.total_cache_read_tokens == 1200
        assert report.total_api_calls == 1
        assert report.calls_by_agent["hm2_scaffold_breaker"] == 1

    def test_multiple_agents(self):
        """CostReport tracks calls from multiple agents independently."""
        from agents.state import CostReport
        report = CostReport()
        report.add_usage("hm2_scaffold_breaker", {"input_tokens": 100, "output_tokens": 50})
        report.add_usage("hm2_triplet_buster", {"input_tokens": 200, "output_tokens": 100})
        report.add_usage("hm2_scaffold_breaker", {"input_tokens": 150, "output_tokens": 75})
        assert report.total_api_calls == 3
        assert report.calls_by_agent["hm2_scaffold_breaker"] == 2
        assert report.calls_by_agent["hm2_triplet_buster"] == 1
        assert report.total_input_tokens == 450


# ── Test 3: BaseAgent interface ───────────────────────────────────────

class TestBaseAgent:
    def test_cannot_instantiate_abstract(self):
        """BaseAgent cannot be instantiated directly — it's abstract."""
        from agents.base import BaseAgent
        with pytest.raises(TypeError):
            BaseAgent()

    def test_concrete_agent_works(self):
        """A concrete agent implementing execute() can be instantiated."""
        from agents.base import BaseAgent
        from agents.state import PipelineState

        class DummyAgent(BaseAgent):
            agent_name = "dummy"
            agent_type = "worker"

            async def execute(self, state: PipelineState) -> PipelineState:
                state.text = "transformed"
                return state

        agent = DummyAgent()
        assert agent.agent_name == "dummy"
        assert agent.agent_type == "worker"
        assert repr(agent) == "<DummyAgent name=dummy type=worker>"

    def test_load_prompt_not_found(self):
        """load_prompt() raises FileNotFoundError for missing prompts."""
        from agents.base import BaseAgent
        from agents.state import PipelineState

        class DummyAgent(BaseAgent):
            agent_name = "dummy"
            agent_type = "worker"
            async def execute(self, state: PipelineState) -> PipelineState:
                return state

        agent = DummyAgent()
        with pytest.raises(FileNotFoundError):
            agent.load_prompt("nonexistent_prompt")


# ── Test 4: AgentConfig loading ───────────────────────────────────────

class TestAgentConfig:
    def test_load_with_existing_config(self):
        """AgentConfig loads defaults from pipeline section of config.yaml."""
        from agents.config import load_agent_config
        config = load_agent_config()
        assert config.rewrite_model == "claude-sonnet-4-6"
        assert config.max_retries == 3
        assert config.max_feedback_iterations == 2

    def test_default_values(self):
        """AgentConfig has sensible defaults for agent-specific fields."""
        from agents.config import AgentConfig
        config = AgentConfig()
        assert config.max_cost_per_request_usd == 15.0
        assert config.enable_smart_skip is True


# ── Test 5: Existing pipeline not broken ──────────────────────────────

class TestExistingPipelineIntact:
    def test_pipeline_imports_still_work(self):
        """Importing pipeline modules still works after agents/ package added."""
        from pipeline import load_config, load_prompt, chunk_text
        cfg = load_config()
        assert "pipeline" in cfg
        assert "scoring" in cfg

    def test_pipeline_class_instantiation(self):
        """Pipeline class can still be instantiated."""
        from pipeline import Pipeline
        pipe = Pipeline()
        assert hasattr(pipe, "run")
        assert hasattr(pipe, "run_from_params")
```

---

## Config.yaml — НЕ менять

НЕ добавлять секцию `agents:` в config.yaml на этом этапе. `load_agent_config()` спроектирован с fallback к `pipeline:` defaults. Секция `agents:` будет добавлена в Phase 1 когда появятся agent-specific настройки.

---

## Правила создания

1. **НЕ трогать** ни один файл в `pipeline/`, `prompts/`, `tests/test_pipeline.py`, `config.yaml`.
2. **Type hints** на всех функциях и параметрах.
3. **Docstrings** на всех классах и публичных методах.
4. **`from __future__ import annotations`** в каждом файле (PEP 604 forward refs).
5. **loguru** для логирования (уже в requirements.txt).
6. **Не добавлять** новые зависимости в requirements.txt — всё что нужно уже есть (anthropic, pyyaml, loguru, pytest, pytest-asyncio).

---

## Верификация после создания

1. Проверить что все 5 файлов созданы: `agents/__init__.py`, `agents/base.py`, `agents/state.py`, `agents/config.py`, `agents/prompts/.gitkeep`
2. Проверить что `tests/test_agents_foundation.py` создан
3. Запустить `pytest tests/test_agents_foundation.py -v` — все тесты должны пройти
4. Запустить `pytest tests/test_pipeline.py -v` — все СУЩЕСТВУЮЩИЕ тесты должны пройти (0 regressions)
5. Проверить что `from agents.base import BaseAgent` работает
6. Проверить что `from agents.state import PipelineState, CostReport` работает
7. Проверить что `from agents.config import load_agent_config, AgentConfig` работает
8. Проверить что `BaseAgent` нельзя инстанциировать напрямую (TypeError)
9. Проверить что `PipelineState(mode="humanization")` создаётся с defaults
