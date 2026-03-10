# Plan: Конвертация Pipeline → Мульти-агентная система

## Context

Проект AI Anti-Anti Plag имеет полностью реализованный 5-стадийный pipeline (analyzer, structural_rewriter, lexical_enricher, discourse_shaper, scorer + Phase 0A/0B генерация + formatter). 150+ тестов, 10 промптов, config.yaml — всё готово. Нужно обернуть это в мульти-агентную систему по архитектуре v3.1 FINAL (82 компонента: CEO → Manager → Micro Manager → Worker), сохранив весь существующий код и тесты. Система будет запускаться через Claude Code, затем подключаться через n8n к сайту как SaaS-сервис.

**Принципы**: wrap (не rewrite), 0 breaking changes, custom orchestrator на anthropic SDK (без LangGraph/CrewAI), explicit state passing.

---

## Phase 0: Фундамент (2-3 дня)

Создаём инфраструктуру агентов без изменения существующего кода.

**Файлы:**
```
agents/__init__.py
agents/base.py              # BaseAgent(ABC): execute(state) → state, load_prompt(), call_claude_with_retry()
agents/state.py             # PipelineState dataclass: text, language, domain, register, mode, analysis_report, scores, feedback, errors
agents/config.py            # Загрузка agent-specific параметров из config.yaml
agents/prompts/             # Директория для промптов агентов
```

**Ключевой интерфейс:**
```python
class BaseAgent(ABC):
    async def execute(self, state: PipelineState) -> PipelineState: ...
    def load_prompt(self, prompt_name: str) -> str: ...

@dataclass
class PipelineState:
    stream_id: str; text: str; language: str; domain: str; register: str; mode: str
    source_list: Optional[SourceList]; analysis_report: dict; final_score_report: dict
    feedback_from_qa: Optional[dict]; feedback_iterations: int = 0; errors: list[str]
    cost_report: Optional[CostReport] = None  # Token/cost tracking per request
    skipped_workers: list[str] = field(default_factory=list)  # Smart Worker Skip log
```

**Тесты:** 5 unit tests (BaseAgent instantiation, PipelineState, Config loading)
**Верификация:** Все 150+ существующих тестов проходят

---

## Phase 1: CEO Agent + Оркестрация (3-4 дня)

**Файлы:**
```
agents/ceo.py                   # CEOAgent: routing table (generation → Content → Humanizer → Export; humanization → Humanizer → Export)
agents/gates/__init__.py
agents/gates/content_qa.py      # ContentQAGate: announcement openers=0, triplets=0, Block 12=0, viz count ≥ minimum
agents/prompts/ceo.md
```

**Логика CEO:**
- `mode == "generation"` → Content Manager → Handoff Gate → Humanizer Manager → Export
- `mode == "humanization"` → Humanizer Manager → Export
- Escalation: если HM-5 fail после 2 итераций → CEO решает (skip metric / re-generate / partial accept)
- Финал: вызывает DOCX Formatter Service

**Тесты:** 8 tests (routing, ContentQA gate, feedback escalation)

---

## Phase 2: Content Manager + 7 Micro Managers (4-5 дней)

**Файлы:**
```
agents/content/__init__.py
agents/content/manager.py            # ContentManager: вызывает SourceFinder ПЕРВЫМ, затем делегирует MM
agents/content/micro_managers/
  mm_coursework.py                   # 7 секций: title_page → toc → intro → ch1 → ch2 → conclusion → references
  mm_abstract_paper.py               # 6 секций: title_page → toc → intro → ch1 → conclusion → references
  mm_vkr.py                          # 9 секций: title → annotation → toc → intro → ch1-3 → conclusion → references
  mm_research.py                     # 8 секций: annotation → intro → lit_review → method → results → discussion → conclusion → references
  mm_text.py                         # 4 подтипа: аналитический, публицистический, обзорный, описательный
  mm_essay.py                        # 1 worker (единый текст)
  mm_composition.py                  # 1 worker (единый текст)
agents/prompts/content_manager.md
agents/prompts/mm_*.md               # 7 промптов для MM
```

**Порядок вызовов ContentManager:**
1. `source_list = await SourceFinderService.find(topic, domain, language, stream_id)` — ПЕРВЫЙ вызов
2. `state.source_list = source_list` — инжекция в PipelineState
3. `mm = self._get_micro_manager(stream_id)` — выбор MM по типу работы
4. `state = await mm.execute(state)` — MM генерирует все секции используя source_list из state

**Каждый MM:**
- Знает свой SECTION_ORDER из CLAUDE.md (Приложение A, GAP 4.4)
- Передаёт `state.source_list` каждому section worker (worker инжектирует в megaprompt)
- Отслеживает viz count (таблицы/рисунки) vs. БЛОК 16.2 минимум
- Если viz count < minimum → re-gen data-heavy section (max 1 retry)

**Тесты:** 10 tests (routing по stream_id, section ordering, viz counting)

---

## Phase 3: 36 Content Workers + Handoff Gate (4-5 дней)

**Файлы:**
```
agents/content/workers/__init__.py
agents/content/workers/base_section_worker.py    # BaseSectionWorker: wraps generator.generate_section()

# NB: SourceFinder — это Shared Service (Phase 6), НЕ section worker.
# ContentManager вызывает SourceFinder.find() ОДИН РАЗ до делегации в MM.
# Workers ниже генерируют ТОЛЬКО текстовые секции.
# VKR workers (9): vkr_title_page.py, vkr_annotation.py, vkr_toc.py, vkr_introduction.py, vkr_chapter_1.py, vkr_chapter_2.py, vkr_chapter_3.py, vkr_conclusion.py, vkr_references.py
# Coursework workers (7): cw_title_page.py, cw_toc.py, cw_introduction.py, cw_chapter_1.py, cw_chapter_2.py, cw_conclusion.py, cw_references.py
# Research workers (8): res_annotation.py, res_introduction.py, res_literature_review.py, res_methodology.py, res_results.py, res_discussion.py, res_conclusion.py, res_references.py
# Abstract paper workers (6): ap_title_page.py, ap_toc.py, ap_introduction.py, ap_chapter_1.py, ap_conclusion.py, ap_references.py
# Text workers (4): text_analytical.py, text_journalistic.py, text_review.py, text_descriptive.py
# Essay worker (1): essay_full.py
# Composition worker (1): comp_full.py

agents/gates/handoff_gate.py          # Передаёт text + domain + register + language + source_list + viz_count
agents/prompts/handoff_gate.md
```

**BaseSectionWorker** — шаблонный класс, вызывает `generator.generate_section(section_id)`. Каждый конкретный worker задаёт section_id и специфичные инструкции.

**Тесты:** 15 tests (worker generation, TOC 2-pass, handoff metadata preservation)

---

## Phase 4: Humanizer Manager + HM-1/HM-2 (5-6 дней)

**Файлы:**
```
agents/humanizer/__init__.py
agents/humanizer/manager.py           # Pipeline: HM-1 → HM-2 → QA → HM-3 → QA → HM-4 → QA → HM-5
agents/humanizer/stages/
  hm1_diagnostician.py               # Wraps analyzer.score() → 20 метрик + pattern scan
  hm2_architect.py                   # Wraps structural_rewriter.transform() → 4 workers
agents/humanizer/workers/
  hm1_pattern_scanner.py             # P1-P53 сканер (via Pattern Scanner SS)
  hm1_metrics_engine.py              # Perplexity, CV, ratios (local, без API)
  hm1_domain_classifier.py           # domain + register → Domain Gate
  hm2_scaffold_breaker.py            # P9, P12, P25-P27, P44-P53
  hm2_format_cleaner.py              # P13-P18, F1-F4b
  hm2_connector_tuner.py             # P29, P33, P40, P43
  hm2_triplet_buster.py              # P10 (zero tolerance)
agents/prompts/hm_manager.md
agents/prompts/hm1_diagnostician.md
agents/prompts/hm2_architect.md
```

**HumanizerManager** — центральный orchestrator:
- Управляет feedback loop: HM-5 → route to HM-2 (structural fail), HM-3 (lexical fail), HM-4 (voice fail)
- Max 2 iterations, затем CEO escalation
- QA gates после каждой трансформирующей стадии

**Тесты:** 12 tests (HM pipeline, QA gate failures, feedback routing)

---

## Phase 5: HM-3/HM-4/HM-5 + QA Gates (6-8 дней)

**Файлы:**
```
agents/humanizer/stages/
  hm3_lexicographer.py               # Wraps lexical_enricher.transform()
  hm4_voice.py                       # Two-pass: Pass A + Pass B audit
  hm5_controller.py                  # Wraps scorer.score() + feedback routing
agents/humanizer/workers/
  hm3_vocab_eliminator.py            # P7, P28, P8, P11, F8
  hm3_hedging_auditor.py             # P32, P38, P23
  hm3_attribution_fixer.py           # P5, P39, P42
  hm3_result_formatter.py            # P36, P31
  hm4_soul_injector.py               # P30, F5, F6, F7, Pass A
  hm4_rhythm_shaper.py               # P25, P37
  hm4_pass_b_auditor.py              # 14-пунктовый чеклист
  hm4_example_loader.py              # Few-shot ВШЭ корпус
  hm5_score_engine.py                # 20 метрик, pass/fail
  hm5_detector_probe.py              # GPTZero, Turnitin (optional)
  hm5_feedback_router.py             # → HM-2/3/4 or CEO
  hm5_report_builder.py              # score_report.json + .txt
agents/gates/
  qa_gate_post_hm2.py                # Coherence check (cosine similarity ≥ 0.85)
  qa_gate_post_hm3.py                # Coherence + Register drift check
  qa_gate_post_hm4.py                # Coherence post-voice (over-imperfection guard)
agents/prompts/hm3_lexicographer.md
agents/prompts/hm4_voice.md
agents/prompts/hm5_controller.md
agents/prompts/qa_*.md
```

**HM-4 Voice** — самый сложный этап:
- Pass A: voice injection (P30 + AC-5 skip figurative для RU academic + AC-4 passive 70% для RU + AC-7 skip F5/F6 для RU academic)
- Pass B: 14-пунктовый чеклист (включая P44-P53 scaffold patterns)
- F5/F6/F7 controlled imperfection injection

**Тесты:** 18 tests (lexical cleanup, two-pass audit, scoring, feedback loop end-to-end)

---

## Phase 6: Shared Services + Интеграция (4-5 дней)

**Файлы:**
```
agents/services/__init__.py
agents/services/base_service.py            # Singleton pattern
agents/services/language_gate.py           # AC-1 → AC-15 валидация
agents/services/domain_gate.py             # P41 epistemological norms
agents/services/source_finder_service.py   # Wraps pipeline.source_finder
agents/services/docx_formatter_service.py  # Wraps pipeline.formatter (ГОСТ 7.32-2017)
agents/services/chunk_manager.py           # 200-400 слов, ~1 sentence overlap, boundary dedup
agents/services/pattern_scanner.py         # P1-P53 единый движок (HM-1, HM-5, Content QA)
agents/services/api_gateway.py             # Claude API rate limiter, retry, token budget tracking
agents/export_manager.py                   # .txt + .docx + score_report.json + score_report.txt
agents/__main__.py                         # CLI: python -m agents --stream vkr --topic "..." --language ru
```

**API Gateway** — критичен: все LLM-вызовы идут через него. Трекинг токенов, cost estimation, exponential backoff.

**Prompt Caching** — обязательная оптимизация в API Gateway (экономия ~27% на input tokens):
```python
class APIGateway(BaseService):
    def call_with_cache(self, system_prompt: str, user_prompt: str, model: str, **kwargs):
        """Все system prompts автоматически кэшируются через cache_control=ephemeral."""
        # Claude API Prompt Caching: cache hit = 10% input price
        # Megaprompt (12K tok) × 9 секций → 8 cache hits = ~$0.30 экономия на Phase 0B
        # Stage prompts (2.5K tok) × 83 чанка → 82 cache hits = ~$2.40 экономия на HM-2/3/4
        # ИТОГО: ~$2.70 экономия на запрос ВКР
        messages = [{"role": "user", "content": user_prompt}]
        return self.client.messages.create(
            model=model,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=messages, **kwargs
        )
```

**Smart Worker Skip** — HM-1 анализ определяет, какие workers нужны:
```python
# Таблица: HM-1 метрика → Worker → Условие пропуска
SKIP_RULES = {
    # HM-2 workers:
    "hm2_triplet_buster":   {"metric": "triplet_count",              "skip_when": "== 0"},
    "hm2_scaffold_breaker": {"metric": "scaffold_signals_count",     "skip_when": "== 0",
                             "also_check": ["announcement_count", "p44_p53_count"]},
    "hm2_connector_tuner":  {"metric": "connector_violation_count",  "skip_when": "== 0",
                             "also_check": ["but_however_ratio >= 2.0"]},
    # HM-2 Format Cleaner: NEVER skip — всегда нужен (F1-F4b, P13-P18)
    # HM-3 workers:
    "hm3_vocab_eliminator": {"metric": "p7_violation_count",         "skip_when": "== 0"},
    "hm3_hedging_auditor":  {"metric": "modal_hedging_count",        "skip_when": "== 0"},
    "hm3_attribution_fixer":{"metric": "attributive_passive_count",  "skip_when": "== 0",
                             "also_check": ["vague_attribution_count"]},
    "hm3_result_formatter": {"metric": "result_praise_count",        "skip_when": "== 0"},
    # HM-4 workers: NEVER skip — voice injection и Pass B всегда нужны
}

# В HumanizerManager.execute():
analysis = state.analysis_report
for worker_name, rule in SKIP_RULES.items():
    if eval_skip_condition(analysis, rule):
        state.skipped_workers.append(worker_name)
        continue
    await worker.execute(state)
# Потенциальная экономия: 15-30% API-вызовов на уже частично чистых текстах
```

**Cost Tracking** — каждый запрос генерирует cost_report:
```python
@dataclass
class CostReport:
    total_input_tokens: int; total_output_tokens: int
    total_api_calls: int; total_cost_usd: float
    cache_hits: int; cache_savings_usd: float
    cost_by_stage: dict[str, float]  # {"phase_0b": 1.17, "hm2": 1.92, ...}
```
Включается в score_report.json для мониторинга и биллинга SaaS.

**Batch API** — опциональный режим для массовых заказов (50% скидка):
- `POST /generate?batch=true` — ставит запрос в очередь, возвращает job_id
- Обработка через `anthropic.Batch.create()` — результат через webhook
- Для SaaS: отдельный тариф "эконом" с доставкой через 1-2 часа

**Тесты:** 25 tests (singleton, AC rules, domain classification, export, **cache hit verification**, **cost tracking**) + full end-to-end integration test

---

## Phase 7: n8n + FastAPI + Deployment (4-5 дней)

**Файлы:**
```
api/main.py                          # FastAPI: POST /generate, POST /humanize, GET /health
api/models.py                        # Pydantic: GenerationRequest, HumanizationRequest
api/routes.py                        # Endpoint handlers
n8n/workflow_generation.json         # n8n workflow для generation mode
n8n/workflow_humanization.json       # n8n workflow для humanization mode
docs/API_CONTRACT.md                 # REST API спецификация
docs/DEPLOYMENT.md                   # Docker + AWS deployment guide
```

**FastAPI endpoints:**
- `POST /generate` — принимает stream_id, topic, language, domain → returns output_text + score_report
- `POST /humanize` — принимает text, language, domain, register → returns humanized_text + score_report
- n8n подключается через Webhook Trigger → FastAPI → CEO Agent → Export → Response

**Тесты:** 8 tests (API endpoints, n8n webhook, load test 10 concurrent)

---

## Сводная таблица

| Phase | Срок | Файлов | Ключевые классы | Тестов | Breaking changes |
|-------|------|--------|-----------------|--------|-----------------|
| 0 | 2-3 дня | 4 | BaseAgent, PipelineState | 5 | 0 |
| 1 | 3-4 дня | 3 | CEOAgent, ContentQAGate | 8 | 0 |
| 2 | 4-5 дней | 9 | ContentManager, 7 MicroManagers | 10 | 0 |
| 3 | 4-5 дней | 38 | BaseSectionWorker, 36 Workers, HandoffGate | 15 | 0 |
| 4 | 5-6 дней | 13 | HumanizerManager, HM1/HM2, 7 Workers | 12 | 0 |
| 5 | 6-8 дней | 19 | HM3/HM4/HM5, 12 Workers, 3 QA Gates | 18 | 0 |
| 6 | 4-5 дней | 10 | 7 Services, ExportManager, CLI | 25 | 0 |
| 7 | 4-5 дней | 7 | FastAPI, n8n workflows | 8 | 0 |
| **ИТОГО** | **~6-8 недель** | **~103** | **82 компонента** | **~101 новых** | **0** |

---

## Существующие файлы для повторного использования (НЕ переписываем)

- `pipeline/__init__.py` — оркестратор (call_claude, load_config, chunk_text)
- `pipeline/analyzer.py` — Stage 1 (HM-1 workers вызывают analyzer.score())
- `pipeline/structural_rewriter.py` — Stage 2 (HM-2 workers вызывают structural_rewriter.transform())
- `pipeline/lexical_enricher.py` — Stage 3 (HM-3 workers вызывают lexical_enricher.transform())
- `pipeline/discourse_shaper.py` — Stage 4 (HM-4 workers вызывают discourse_shaper.transform())
- `pipeline/scorer.py` — Stage 5 (HM-5 workers вызывают scorer.score())
- `pipeline/generator.py` — Phase 0B (Content Workers вызывают generator.generate_section())
- `pipeline/source_finder.py` — Phase 0A (SourceFinder Service wraps source_finder.find())
- `pipeline/formatter.py` — DOCX export (DOCX Formatter Service wraps formatter.export_to_docx())
- `pipeline/example_loader.py` — Few-shot (HM-4 Example Loader worker wraps example_loader)
- `prompts/*.md` — все 10 промптов переиспользуются как есть + новые agent-specific промпты
- `config.yaml` — расширяется секцией `agents:` для agent-specific параметров

---

## Верификация

После КАЖДОЙ фазы:
1. `pytest tests/` — все 150+ существующих тестов проходят
2. Новые тесты фазы проходят
3. Ручной smoke test: запуск CLI с тестовым текстом
4. После Phase 6: полный end-to-end тест (generation mode + humanization mode)
5. После Phase 7: нагрузочный тест (10 concurrent requests через FastAPI)

---
---

# ПРИЛОЖЕНИЕ A: Спецификации закрытых пробелов (GAP 1–6)

Эти спецификации ОБЯЗАТЕЛЬНЫ к реализации. Без них Phase 4–6 невозможны.

---

## GAP 1: Полная таблица AC-правил → Агент → Метод

| AC | Название | Severity | Агент-владелец | Сервис | Метод/Логика |
|----|----------|----------|----------------|--------|-------------|
| AC-1 | Em Dash Language Gate | HIGH | HM-2 Format Cleaner | Language Gate | `language=='en'`: `reduce_em_dashes()` (target: 0). `language=='ru'`: `reduce_em_dashes_ru()` (>3/paragraph → reduce, grammatические сохранять) |
| AC-2 | GOST [N] vs Author-Year | HIGH | HM-3 Attribution Fixer | Language Gate | `language=='ru' AND register=='academic'`: citation_format='GOST' → НИКОГДА не конвертировать [N] в author-year. Иначе: author-year |
| AC-3 | GOST Macro-Structure | HIGH | HM-2 Scaffold Breaker | — | P26 idea-order disruptor работает ТОЛЬКО на уровне параграфов внутри секций. НИКОГДА не переставлять: title_page, annotation, TOC, introduction, chapters (по номеру), conclusion, references |
| AC-4 | Passive Voice Threshold RU | HIGH | HM-4 Soul Injector | Language Gate | `language=='ru' AND register=='academic'`: passive_threshold = 0.70. EN или non-academic: 0.20. Из `config.yaml: discourse.academic_ru_passive_threshold` |
| AC-5 | Figurative Language RU | HIGH | HM-4 Soul Injector | Language Gate | Skip metaphor/analogy injection (Pass A Op 8) когда: `language=='ru' AND register=='academic'` ИЛИ domain=='math'. Применять для RU journalistic/essay |
| AC-6 | Russian Regex Patterns | HIGH | HM-2 + HM-3 | Language Gate | `language=='ru'`: вызывать `_apply_russian_patterns(text, config)` с `p7_russian` и `p29_russian` config blocks. Промпты содержат `{{LANGUAGE}}` |
| AC-7 | F5/F6 in RU/Academic | MED-HIGH | HM-4 Soul Injector | Language Gate | `language=='ru'`: skip F5 полностью; F6 = только запятые (1-2 шт). `register=='academic'` (любой язык): skip F5 И F6. `EN + journalistic`: F5 (3-5) + F6 (2-3) |
| AC-8 | Quote Normalization RU | MEDIUM | HM-2 Format Cleaner | Language Gate | `language=='en'`: ASCII straight quotes `"`. `language=='ru'`: guillemets «» через `normalize_quotes_ru()` |
| AC-9 | List-to-Prose Scope | MED-HIGH | HM-2 Format Cleaner | — | НИКОГДА не конвертировать: нумерованные секции (1.1, Глава N), библиографию, TOC. Только: body-text bullets формата `**Header:** Content` |
| AC-10 | Idea-Order Gating | MEDIUM | HM-2 Scaffold Breaker | — | Перед Op 11 (idea-order disruptor): assert `register in ['academic', 'academic-essay', 'journalistic', 'general']`. Для `academic`: только paragraph level |
| AC-11 | Standalone Definitions | LOW | HM-3 Vocab Eliminator | Language Gate | `language=='en'`: конвертировать "X is defined as Y". `language=='ru'`: конвертировать "Под X понимается Y" |
| AC-12 | But:However Ratio RU | LOW | HM-5 Score Engine | Language Gate | `language=='ru'`: `but_however_ratio = None`; вместо этого: `no_odnako_ratio` (Но:Однако ≥ 2:1) из `config.yaml: p29_russian.target_no_odnako_ratio` |
| AC-13 | Citation Density vs GOST | LOW | HM-5 Score Engine + Phase 0A | — | Ортогональны. Citation density per page (Stage 5) И GOST source minimums (Phase 0A) проверяются независимо |
| AC-14 | Russian P7 Words | LOW | HM-3 Vocab Eliminator | Language Gate | `p7_russian` config block + `_apply_russian_patterns()` + `{{LANGUAGE}}` в LLM промптах. Absolute ban: следует отметить, является ключевым, играет важную роль, etc. |
| AC-15 | Perplexity Scoring RU | LOW | HM-1 Metrics Engine + HM-5 | Language Gate | `language=='ru'`: `_skip_perplexity=True`. Score report: "N/A (Russian text)" для perplexity полей |

**Интеграция в код:**
- `LanguageGateService.get_config(language, register, domain)` возвращает `LanguageConfig` dataclass со всеми флагами
- Каждый HM-stage вызывает `language_gate.get_config()` в начале `execute()` и передаёт флаги worker'ам
- QA Gates проверяют AC-compliance по метрикам из Language Gate

---

## GAP 2: Language Gate Service — Полная спецификация

```python
@dataclass
class LanguageConfig:
    """Результат LanguageGateService.get_config() — все AC-флаги для текущего запуска."""
    language: str                          # "ru" | "en"
    register: str                          # "academic" | "journalistic" | "general" | "academic-essay"
    domain: str                            # "it_cs" | "economics" | ...

    # AC-1: Em Dash
    em_dash_mode: str                      # "eliminate" (EN) | "conservative_ru" (RU)

    # AC-2: Citation format
    citation_format: str                   # "GOST" (RU academic) | "AUTHOR_YEAR" (rest)

    # AC-4: Passive voice
    passive_threshold: float               # 0.70 (RU academic) | 0.20 (EN/non-academic)

    # AC-5: Figurative language
    skip_figurative: bool                  # True for RU academic + math domain

    # AC-6: Russian patterns
    use_russian_patterns: bool             # True when language=='ru'
    p7_russian_banlist: list[str]          # From config.yaml: p7_russian
    p29_russian_rules: dict                # From config.yaml: p29_russian

    # AC-7: F5/F6 gating
    skip_f5: bool                          # True for RU; True for academic (any lang)
    skip_f6: bool                          # True for academic (any lang); RU journalistic: comma only
    f6_mode: str                           # "skip" | "comma_only" | "full"

    # AC-8: Quote style
    quote_style: str                       # "straight" (EN) | "guillemets" (RU)

    # AC-12: Connector ratio
    connector_ratio_metric: str            # "but_however" (EN) | "no_odnako" (RU)
    connector_ratio_target: float          # ≥ 2.0

    # AC-15: Perplexity
    skip_perplexity: bool                  # True for RU

    # AC-3: Macro-structure protection
    allow_macro_reordering: bool           # False for academic (P26 only at paragraph level)

    # AC-9: List-to-prose exceptions
    list_to_prose_exceptions: list[str]    # ["numbered_sections", "bibliography", "toc"]

    # AC-10: Register validation
    register_valid_for_p26: bool           # True when register in ['academic','academic-essay','journalistic','general']

    # AC-11: Definition form
    definition_form: str                   # "en" → "X is defined as Y" | "ru" → "Под X понимается Y"

    # F3: Semicolon limit by register
    semicolon_limit_per_500: int           # 0 for journalistic | 1 for academic

    # spaCy model
    spacy_model_name: str                  # "ru_core_news_sm" | "en_core_web_sm"
```

**Service interface:**
```python
class LanguageGateService(BaseService):  # Singleton
    def get_config(self, language: str, register: str, domain: str) -> LanguageConfig: ...
    def validate_ac_compliance(self, text: str, config: LanguageConfig) -> list[ACViolation]: ...
```

**Фаза создания:** Phase 6, НО `LanguageConfig` dataclass создаётся в Phase 0 (agents/state.py), чтобы agents в Phase 4-5 могли типизировать параметры. До Phase 6: agents читают config напрямую через `agents/config.py`. После Phase 6: через singleton service.

---

## GAP 3: Feedback Routing — Полная таблица маршрутизации

HM-5 Feedback Router анализирует `final_score_report` и определяет маршрут:

| Метрика | Целевое значение | При fail → Route | Приоритет |
|---------|-----------------|------------------|-----------|
| `triplet_count` | 0 (hard) | → HM-2 (Triplet Buster) | P1 (highest) |
| `announcement_opener_count` | 0 (hard) | → HM-2 (Scaffold Breaker) | P1 |
| `para_ending_generalization_count` | 0 (hard) | → HM-4 (Pass B Auditor) | P2 |
| `paragraph_cv` | ≥ 0.50 | → HM-2 (Scaffold Breaker) | P3 |
| `section_cv` | ≥ 0.30 | → HM-2 (Scaffold Breaker) | P3 |
| `sentence_cv` (burstiness) | ≥ 0.45 | → HM-4 (Rhythm Shaper) | P4 |
| `p7_violation_count` | 0 | → HM-3 (Vocab Eliminator) | P3 |
| `modal_hedging_on_results` | 0% | → HM-3 (Hedging Auditor) | P3 |
| `but_however_ratio` (EN) | ≥ 2:1 | → HM-2 (Connector Tuner) | P4 |
| `no_odnako_ratio` (RU) | ≥ 2:1 | → HM-2 (Connector Tuner) | P4 |
| `connector_density` | ≤ config thresholds | → HM-2 (Connector Tuner) | P4 |
| `pattern_elimination_rate` | ≥ 85% | → HM-3 (полный re-run) | P3 |
| `perplexity_lift` (EN only) | ≥ 1.5x | → HM-4 (Soul Injector) | P5 |
| `coherence_score` | ≥ 4/5 (0.80 cosine) | → HM-4 (Pass B Auditor) | P2 |
| `length_reduction_ratio` | ≤ 0.90 | → HM-3 (Vocab Eliminator: cut filler) | P5 |
| `scaffold_signals` (P44-P53) | 0 | → HM-2 (Scaffold Breaker) | P2 |
| `attributive_passive_count` | 0 | → HM-3 (Attribution Fixer) | P3 |

**Алгоритм маршрутизации:**
```python
def determine_route(self, report: dict, lang_config: LanguageConfig) -> Optional[str]:
    # 1. Собрать все failed метрики с приоритетами
    failures = [(metric, priority, route) for metric in ROUTING_TABLE if not report[metric].pass]

    # 2. Если нет failures → return None (PASS)
    if not failures:
        return None

    # 3. Группировать по route, взять route с наибольшим количеством failures × priority weight
    route_scores = {"hm2": 0, "hm3": 0, "hm4": 0}
    for metric, priority, route in failures:
        route_scores[route] += (6 - priority)  # P1=5, P2=4, P3=3, P4=2, P5=1

    # 4. Return route с максимальным score
    return max(route_scores, key=route_scores.get)
```

**Max iterations:** 2. После 2-го fail → `return "ceo_escalation"` с полным score_report.

**Пороговые значения (METRIC_THRESHOLDS):**
```python
METRIC_THRESHOLDS = {
    "triplet_count":                  {"pass": lambda v: v == 0,        "type": "hard"},
    "announcement_opener_count":      {"pass": lambda v: v == 0,        "type": "hard"},
    "para_ending_generalization_count":{"pass": lambda v: v == 0,       "type": "hard"},
    "attributive_passive_count":      {"pass": lambda v: v == 0,        "type": "hard"},
    "scaffold_signals_count":         {"pass": lambda v: v == 0,        "type": "hard"},
    "p7_violation_count":             {"pass": lambda v: v == 0,        "type": "hard"},
    "modal_hedging_on_results":       {"pass": lambda v: v == 0,        "type": "hard"},
    "paragraph_cv":                   {"pass": lambda v: v >= 0.50,     "type": "soft"},
    "section_cv":                     {"pass": lambda v: v >= 0.30,     "type": "soft"},
    "sentence_cv":                    {"pass": lambda v: v >= 0.45,     "type": "soft"},
    "but_however_ratio":              {"pass": lambda v: v >= 2.0,      "type": "soft", "red_line": lambda v: v < 1.0},
    "no_odnako_ratio":                {"pass": lambda v: v >= 2.0,      "type": "soft", "red_line": lambda v: v < 1.0},
    "connector_density_per_page":     {"pass": lambda v: v <= 1.2,      "type": "soft"},
    "pattern_elimination_rate":       {"pass": lambda v: v >= 0.85,     "type": "soft"},
    "perplexity_lift":                {"pass": lambda v: v >= 1.5,      "type": "soft"},  # EN only
    "coherence_score":                {"pass": lambda v: v >= 0.80,     "type": "soft"},
    "length_reduction_ratio":         {"pass": lambda v: v <= 0.90,     "type": "soft"},
}
# hard = 0 tolerance, must fix; soft = degraded but not blocking
```

---

## GAP 4: Phase 0 — Детали генерации контента

### 4.1 Megaprompt Assembly

Content Workers вызывают `generator.generate_section()`, который внутри:

```python
def _assemble_megaprompt(self, params: GenerationParams, section_id: str) -> str:
    base = self._load_prompt("academic_megaprompt.md")
    # Подстановки:
    base = base.replace("{{STREAM_ID}}", params.stream_id)
    base = base.replace("{{DOMAIN}}", params.domain)
    base = base.replace("{{LANGUAGE}}", params.language)
    base = base.replace("{{RESEARCH_TYPE}}", params.research_type)
    base = base.replace("{{SECTION_ID}}", section_id)
    base = base.replace("{{SOURCES}}", self._format_sources_for_injection(params.source_list))
    return base
```

**Агентная обёртка:** BaseSectionWorker вызывает `generator.generate_section(section_id, params)` как есть. Worker НЕ собирает megaprompt сам — это делает generator.py.

### 4.2 Visualization Tracking

```python
# В MicroManager (mm_vkr.py, mm_coursework.py, etc.):
class MicroManagerVKR(BaseMicroManager):
    VIZ_MINIMUMS = {"bachelor": 5, "master": 8}  # Из БЛОК 16.2

    async def execute(self, state: PipelineState) -> PipelineState:
        table_count, figure_count = 0, 0

        for section_id in self.SECTION_ORDER:
            worker = self._get_worker(section_id)
            state = await worker.execute(state)
            tc, fc = self._count_viz(state.last_section_text)
            table_count += tc; figure_count += fc

        total_viz = table_count + figure_count
        minimum = self.VIZ_MINIMUMS.get(state.generation_params.level, 5)

        if total_viz < minimum:
            # Re-gen data-heavy sections (ch2 for economics, results for research)
            state = await self._regen_data_section(state, minimum - total_viz)

        state.viz_count = {"tables": table_count, "figures": figure_count, "total": total_viz}
        return state
```

### 4.3 TOC 2-Pass

```python
class TOCWorker(BaseSectionWorker):
    section_id = "toc"

    async def execute(self, state: PipelineState) -> PipelineState:
        # Pass 1: placeholder TOC (before content generated)
        state.toc_placeholder = self._generate_placeholder_toc(state)
        return state

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        # Pass 2: update TOC with actual section titles from generated text
        state.toc_final = self._update_toc_from_content(state.text, state.toc_placeholder)
        state.text = state.text.replace(state.toc_placeholder, state.toc_final)
        return state
```

MicroManager вызывает `toc_worker.execute()` в позиции TOC, затем после всех секций: `toc_worker.execute_pass_2()`.

### 4.4 Section Orders (точные, из CLAUDE.md)

```python
SECTION_ORDERS = {
    # NB: "sources" НЕ входит — Phase 0A SourceFinder.find() выполняется до генерации секций
    # и source_list инжектируется в megaprompt. "references" — финальная секция, форматирует source_list.
    "vkr":           ["title_page", "annotation", "toc", "introduction", "chapter_1", "chapter_2", "chapter_3", "conclusion", "references"],
    "coursework":    ["title_page", "toc", "introduction", "chapter_1", "chapter_2", "conclusion", "references"],
    "research":      ["annotation", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion", "references"],
    "abstract_paper": ["title_page", "toc", "introduction", "chapter_1", "conclusion", "references"],
    "text":          ["full"],          # single generation call
    "essay":         ["full"],
    "composition":   ["full"],
}
```

### 4.5 Source Minimums (из CLAUDE.md)

```python
SOURCE_MINIMUMS = {
    "vkr_bachelor": 50, "vkr_master": 60,
    "coursework": 20, "research": 30, "abstract_paper": 10,
    "text": 0, "essay": 0, "composition": 0,
}
```

---

## GAP 5: Russian spaCy Model — Setup

**Добавить в Phase 0 setup-скрипт:**
```bash
# requirements.txt — уже содержит spacy
# Добавить в scripts/setup.sh или agents/setup.py:
python -m spacy download ru_core_news_sm  # Russian tokenization
python -m spacy download en_core_web_sm   # English tokenization (если не установлена)
```

**Fallback в agents/config.py:**
```python
def get_spacy_model(language: str):
    import spacy
    model_name = "ru_core_news_sm" if language == "ru" else "en_core_web_sm"
    try:
        return spacy.load(model_name)
    except OSError:
        logger.warning(f"spaCy model {model_name} not found, falling back to regex tokenization")
        return None  # Pipeline falls back to regex-based tokenization
```

**Добавить в PipelineState (Phase 0):**
```python
@dataclass
class PipelineState:
    # ... existing fields ...
    spacy_model: Optional[Any] = None  # Loaded once in HM-1, reused by HM-2/3/4/5
```

---

## GAP 6: But:However Ratio — Полная спецификация

**Метрика:**
| Язык | Метрика | Target | Red line | Источник |
|------|---------|--------|----------|----------|
| EN | `but_however_ratio` = count("But")/count("However") | ≥ 2.0 | < 1.0 | P33, CLAUDE.md |
| RU | `no_odnako_ratio` = count("Но")/count("Однако") | ≥ 2.0 | < 1.0 | AC-12, config.yaml: p29_russian |

**Измерение (HM-5 Score Engine):**
```python
def _compute_connector_ratio(self, text: str, lang_config: LanguageConfig) -> dict:
    if lang_config.language == "en":
        but_count = len(re.findall(r'\bBut\b', text))
        however_count = len(re.findall(r'\bHowever\b', text)) or 1  # avoid div/0
        ratio = but_count / however_count
        return {"but_however_ratio": ratio, "pass": ratio >= 2.0, "red_line": ratio < 1.0}
    elif lang_config.language == "ru":
        no_count = len(re.findall(r'\bНо\b', text))
        odnako_count = len(re.findall(r'\bОднако\b', text)) or 1
        ratio = no_count / odnako_count
        return {"no_odnako_ratio": ratio, "pass": ratio >= 2.0, "red_line": ratio < 1.0}
```

**Feedback routing при fail:**
- `ratio < 2.0` → Route to HM-2 Connector Tuner (Priority P4)
- `ratio < 1.0` (red line) → Route to HM-2 Connector Tuner (Priority P2 — elevated)
- HM-2 Connector Tuner: конвертирует excess "However" → "But" или direct continuation

---

## GAP 7 (бонус): Полная карта паттернов → Агенты

| Паттерн(ы) | Категория | Агент-владелец | Worker |
|------------|-----------|----------------|--------|
| P1-P4 | Content | HM-3 | Vocab Eliminator (significance deflation, promotional language) |
| P5 | Content | HM-3 | Attribution Fixer (vague attributions + attributive passive) |
| P6 | Content | HM-3 | Result Formatter (formulaic challenge/prospect) |
| P7 | Language | HM-3 | Vocab Eliminator (AI vocabulary banlist + domain exemption) |
| P8 | Language | HM-3 | Vocab Eliminator (copula avoidance → is/are/has) |
| P9 | Language | HM-2 | Scaffold Breaker (announcement openers — hard ban) |
| P10 | Language | HM-2 | Triplet Buster (zero tolerance — hard ban) |
| P11 | Language | HM-3 | Vocab Eliminator (elegant variation → repeat clearest noun) |
| P12 | Language | HM-2 | Scaffold Breaker (false ranges) |
| P13 | Style | HM-2 | Format Cleaner (em dash overuse → F2) |
| P14 | Style | HM-2 | Format Cleaner (excessive boldface) |
| P15 | Style | HM-2 | Format Cleaner (inline-header lists → prose, gated by AC-9) |
| P16 | Style | HM-2 | Format Cleaner (Title Case → Sentence case) |
| P17 | Style | HM-2 | Format Cleaner (decorative emojis) |
| P18 | Style | HM-2 | Format Cleaner (curly quotes → straight/guillemets per AC-8) |
| P19-P21 | Communication | HM-4 | Soul Injector (chatbot artifacts, knowledge-cutoff, sycophancy) |
| P22 | Filler | HM-3 | Vocab Eliminator (filler phrases → delete/shorten) |
| P23 | Filler | HM-3 | Hedging Auditor (excessive hedging → one qualifier max) |
| P24 | Filler | HM-4 | Pass B Auditor (generic endings → specific fact) |
| P25 | Structure | HM-2 + HM-4 | Scaffold Breaker (paragraph uniformity) + Rhythm Shaper (enforce CV) |
| P26 | Structure | HM-2 | Scaffold Breaker (default ordering → non-linear, gated by AC-3/AC-10) |
| P27 | Structure | HM-2 | Scaffold Breaker (sentence-starter monotony) |
| P28 | Language | HM-3 | Vocab Eliminator (formal register inflation → substitution table) |
| P29 | Language | HM-2 | Connector Tuner (connector monotony + banned list) |
| P30 | Style | HM-4 | Soul Injector (imperfection texture injection, register-dependent) |
| P31 | Extended | HM-3 | Result Formatter (information-first posture → delete importance claims) |
| P32 | Extended | HM-3 | Hedging Auditor (modal hedging on empirical facts → remove modals) |
| P33 | Extended | HM-2 | Connector Tuner (But:However ratio ≥ 2:1 / Но:Однако per AC-12) |
| P34 | Extended | HM-4 | Soul Injector (rhetorical questions at argument pivots, domain-gated) |
| P35 | Extended | HM-3 | Vocab Eliminator (standalone definitions → parenthetical, per AC-11) |
| P36 | Extended | HM-3 | Result Formatter (results without evaluative praise) |
| P37 | Extended | HM-4 | Rhythm Shaper (section-level asymmetry, CV ≥ 0.30) |
| P38 | Extended | HM-3 | Hedging Auditor (attribution-based hedging) |
| P39 | Extended | HM-3 | Attribution Fixer (counter-argument integration → named scholars) |
| P40 | Extended | HM-2 | Connector Tuner (connector scarcity as baseline) |
| P41 | Extended | Domain Gate SS | Domain Gate (epistemological norms per domain) |
| P42 | Extended | HM-3 | Attribution Fixer (citation density calibration by domain) |
| P43 | Extended | HM-2 | Connector Tuner ("Also" frequency ≥ 0.08/page in academic) |
| P44 | Scaffold | HM-2 | Scaffold Breaker (superlative importance opener) |
| P45 | Scaffold | HM-2 | Scaffold Breaker (two-sentence dramatic reveal) |
| P46 | Scaffold | HM-2 | Scaffold Breaker (meta-media commentary) |
| P47 | Scaffold | HM-2 | Scaffold Breaker (binary future force projection) |
| P48 | Scaffold | HM-2 | Scaffold Breaker (binary neither wrap-up) |
| P49 | Scaffold | HM-2 | Scaffold Breaker (elegant reversal in analytical position) |
| P50 | Scaffold | HM-2 | Scaffold Breaker (same-X-that-also construction) |
| P51 | Scaffold | HM-2 | Scaffold Breaker (whether-or-just closure) |
| P52 | Scaffold | HM-2 | Scaffold Breaker (mechanism attribution run-on) |
| P53 | Scaffold | HM-2 | Scaffold Breaker (participial simultaneity) |

**F-Rules → Агенты:**

| F-Rule | Стадия | Worker |
|--------|--------|--------|
| F1 (No Oxford Comma) | Stage 2 | HM-2 Format Cleaner |
| F2 (Em Dash = 0) | Stage 2 | HM-2 Format Cleaner |
| F3 (Semicolon Near-Ban) | Stage 2 | HM-2 Format Cleaner |
| F4 (Colon Reduction) | Stage 2 | HM-2 Format Cleaner |
| F4b (Parenthesis Min) | Stage 2 | HM-2 Format Cleaner |
| F5 (Apostrophe Drops) | Stage 4 | HM-4 Soul Injector (skip per AC-7) |
| F6 (Grammar Errors) | Stage 4 | HM-4 Soul Injector (skip per AC-7) |
| F7 (Filler Words) | Stage 4 | HM-4 Soul Injector |
| F8 (Hyphenated Compounds) | Stage 3 | HM-3 Vocab Eliminator |

---

# ПРИЛОЖЕНИЕ B: Экономика запроса (Cost Model)

## Себестоимость одного запроса ВКР бакалавр

**Параметры**: ~25,000 слов → ~50,000 токенов | 83 чанка × 600 tok | 50 источников ГОСТ | ~395 API-вызовов

| Стадия | API-вызовов | Input tokens | Output tokens | Модель | Стоимость |
|--------|------------|-------------|--------------|--------|-----------|
| Phase 0A: SourceFinder | 1 | 3,500 | 6,000 | Sonnet | $0.10 |
| Phase 0B: AcademicGenerator | 9 | 139,500 | 50,000 | Sonnet | $1.17 |
| HM-1: Diagnostician | 0 | — | — | LOCAL | $0.00 |
| HM-2: Architect (4 workers) | 79 | 222,600 | 83,600 | Sonnet | $1.92 |
| HM-3: Lexicographer (4 workers) | 148 | 451,200 | 88,800 | Sonnet | $2.69 |
| HM-4: Voice (Pass A + Pass B) | 92 | 412,800 | 102,300 | Sonnet | $2.77 |
| HM-5: Controller | 0 | — | — | LOCAL | $0.00 |
| QA Gates (×3) | 3 | 154,500 | 1,500 | Haiku | $0.16 |
| Feedback Loop (~1 iter avg) | 59 | 180,500 | 35,500 | Sonnet | $1.07 |
| CEO + overhead | 3 | 9,000 | 1,500 | Haiku | $0.02 |
| **ИТОГО** | **~395** | **~1,577K** | **~369K** | | **~$9.90** |

## Распределение стоимости

- **85% — Гуманизация** (HM-2 → HM-4 + feedback): $8.45
- **13% — Генерация** (Phase 0A + 0B): $1.27
- **2% — Overhead** (CEO, QA, classifier): $0.18

## Оптимизации (обязательно реализовать в Phase 6)

| Оптимизация | Экономия | Итоговая цена | Как |
|-------------|----------|---------------|-----|
| Prompt Caching | −$2.70 (−27%) | $7.20 | `cache_control: ephemeral` на system prompts |
| Smart Worker Skip | −$1.00–$2.00 (−10–20%) | $5.20–$6.20 | HM-1 анализ → skip workers для отсутствующих паттернов |
| Batch API | −50% | $3.60 | `anthropic.Batch.create()` для не-real-time заказов |
| Cache + Skip + Batch | до −70% | **~$3.00** | Все три вместе |

## Стоимость по типам работ (оценка)

| Тип работы | Слов | Токенов | API-вызовов | Sonnet | С кэшем |
|------------|------|---------|-------------|--------|---------|
| ВКР бакалавр | 25K | 50K | ~395 | $9.90 | $7.20 |
| ВКР магистр | 35K | 70K | ~530 | $13.50 | $9.80 |
| Курсовая | 12K | 24K | ~210 | $5.20 | $3.80 |
| Реферат | 8K | 16K | ~140 | $3.50 | $2.50 |
| Текст/Эссе | 3K | 6K | ~70 | $1.80 | $1.30 |
| Только humanize (5K слов) | 5K | 10K | ~120 | $3.20 | $2.30 |

## Ценообразование SaaS (ориентир)

| Цена продажи | Себестоимость (с кэшем) | Маржа | Прибыль |
|-------------|------------------------|-------|---------|
| 500₽ | ~650₽ ($7.20) | −29% | убыток |
| 1,000₽ | ~650₽ | 35% | ~350₽ |
| 1,500₽ | ~650₽ | 57% | ~850₽ |
| 2,000₽ | ~650₽ | 68% | ~1,350₽ |
| 3,000₽ | ~650₽ | 78% | ~2,350₽ |

**Минимальная безубыточная цена**: ~700₽ (с Prompt Caching). Рекомендуемая цена для SaaS: **1,500–2,000₽** за ВКР (маржа 57–68%).
