# SKILL PROMPTS — Готовые промпты для Claude Code

Каждый промпт — копируй в Claude Code как есть. Все скиллы следуют 6-Step Skill Building Framework.

---

## Скилл #1: agent-builder ✅ СОЗДАН → 🔄 ДОРАБОТКА

**Статус**: Создан Claude Code (7 файлов). Требуется доработка по решениям D17-D21.
**Текущее расположение**: .claude/skills/agent-builder/ (уже LOCAL — D21 выполнено)
**Файлы**: SKILL.md + reference/ (6 шаблонов .py)

**Что создано**:
- 6-Step Framework полностью
- 5 типов шаблонов: stage, worker, micro_manager, gate, service + test
- 12 Rules (R1-R12) + запреты
- Reference files в отдельных .py файлах
- Self-improvement через improvements.log
- Human-in-the-loop: шаг 3.7 — показать перед записью

**Что нужно доработать** (промпт ниже):
- Добавить YAML front matter
- Хардкодить известные пути вместо поиска
- Добавить feedback cycle как формальный шаг
- Усилить шаблоны (error handling, cost tracking, Prompt Caching)
- Перенести в .claude/skills/ если сейчас в ~/.claude/skills/

**Промпт доработки**: см. секцию "ПРОМПТ ДОРАБОТКИ AGENT-BUILDER" ниже

---

---

## ПРОМПТ ДОРАБОТКИ AGENT-BUILDER (скопировать в Claude Code)

```
Доработай существующий скилл agent-builder в .claude/skills/agent-builder/.

Скилл уже создан и работает. Нужно внести 6 конкретных улучшений. НЕ переписывай с нуля — точечно дополни существующие файлы.

=== УЛУЧШЕНИЕ 1: YAML Front Matter в SKILL.md ===

Добавь в самое начало SKILL.md перед заголовком:

---
description: "Генерирует production-ready код агентов (worker, stage, gate, service, micro_manager) для системы AI Anti-Anti Plag с соблюдением архитектуры v3.1 FINAL"
allowed_tools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
---

Это даёт Claude Code короткое описание для решения когда активировать скилл, и ограничивает инструменты только теми, которые нужны для генерации кода.

=== УЛУЧШЕНИЕ 2: Хардкодинг известных путей ===

В SKILL.md в секцию "3. Step-by-Step Process" после шага 3.2 добавь новый блок:

### Хардкодированные пути (НЕ искать — использовать напрямую)

```
# Файловая структура проекта — ВСЕГДА актуальна:
PROJECT_ROOT = "."  # корень проекта AI Anti-anti plag

# Шаблоны агентов (reference/):
TEMPLATES = ".claude/skills/agent-builder/reference/"

# Куда складывать агентов:
AGENTS_DIR = "agents/"
AGENTS_HUMANIZER_STAGES = "agents/humanizer/stages/"
AGENTS_HUMANIZER_WORKERS = "agents/humanizer/workers/"
AGENTS_CONTENT_WORKERS = "agents/content/workers/"
AGENTS_CONTENT_MM = "agents/content/micro_managers/"
AGENTS_GATES = "agents/gates/"
AGENTS_SERVICES = "agents/services/"
AGENTS_PROMPTS = "agents/prompts/"

# Куда складывать тесты:
TESTS_DIR = "tests/"

# Существующий pipeline (ТОЛЬКО читать, НЕ менять):
PIPELINE_DIR = "pipeline/"
PIPELINE_MODULES = [
    "pipeline/analyzer.py",           # Stage 1
    "pipeline/structural_rewriter.py", # Stage 2
    "pipeline/lexical_enricher.py",    # Stage 3
    "pipeline/discourse_shaper.py",    # Stage 4
    "pipeline/scorer.py",              # Stage 5
    "pipeline/generator.py",           # Phase 0B
    "pipeline/source_finder.py",       # Phase 0A
    "pipeline/formatter.py",           # DOCX export
]

# Конфиг:
CONFIG = "config.yaml"
ENV = ".env"

# Промпты pipeline (reference — НЕ менять):
PIPELINE_PROMPTS = "prompts/"
```

Никогда не используй `find`, `glob`, `grep` для поиска этих путей. Они фиксированы.

=== УЛУЧШЕНИЕ 3: Feedback Cycle как формальный шаг ===

В SKILL.md после шага 3.7 добавь:

### Шаг 3.8 — Feedback Cycle (обязательный)
После создания агента — протестировать его:
1. Создать минимальный тест-кейс: `python -m pytest tests/test_{agent_name}.py -v`
2. Если тест провалился — прочитать ошибку, исправить код, повторить
3. Для workers/stages с LLM-вызовами: вызвать с mock-данными, проверить что промпт подставляется корректно
4. Записать результат в improvements.log:
   ```
   [DATE] [AGENT_NAME] [FEEDBACK] — Test result: PASS/FAIL. Issues: {issues}. Fixed: {fixes}.
   ```
5. Если паттерн ошибки повторился 2+ раза → обновить соответствующий шаблон в reference/

Минимум одна итерация feedback cycle на каждого агента. Без прохождения тестов агент считается незавершённым.

=== УЛУЧШЕНИЕ 4: Усиление worker_template.py ===

В reference/worker_template.py добавь после строки `state.text = self.chunk_manager.merge(results)`:

        # Cost tracking
        state.cost_tracker.add(
            agent=self.__class__.__name__,
            input_tokens=sum(r.input_tokens for r in self._last_responses),
            output_tokens=sum(r.output_tokens for r in self._last_responses),
            cached_tokens=sum(r.cached_tokens for r in self._last_responses),
        )

А в call_claude добавь комментарий-placeholder для Prompt Caching:

            try:
                result = await self.call_claude(
                    system_prompt=prompt,
                    user_prompt=chunk.text,
                    temperature={temperature},
                    # Prompt Caching: system_prompt передаётся с cache_control="ephemeral"
                    # Реализация в BaseAgent.call_claude() — НЕ дублировать здесь
                )

=== УЛУЧШЕНИЕ 5: Усиление base_agent_template.py ===

В reference/base_agent_template.py добавь обработку ошибок в worker loop:

        for worker_name in self.WORKERS:
            if worker_name in state.skipped_workers:
                self.logger.info(f"Skipping {worker_name} (Smart Worker Skip)")
                continue

            try:
                worker = self._load_worker(worker_name)
                state = await worker.execute(state)
            except Exception as e:
                self.logger.error(f"Worker {worker_name} failed: {e}")
                state.errors.append(f"{self.__class__.__name__}/{worker_name}: {e}")
                # НЕ прерываем цепочку — следующий worker может работать на частично обработанном тексте
                continue

=== УЛУЧШЕНИЕ 6: Усиление gate_template.py ===

В reference/gate_template.py добавь в GateCheckResult поле severity и метод to_feedback_string:

@dataclass
class GateCheckResult:
    """Result of a single gate evaluation pass."""
    all_passed: bool
    failures: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    severity: str = "warning"  # "warning" | "hard_fail"

    def to_feedback_string(self) -> str:
        """Format for state.feedback_from_qa injection."""
        lines = [f"GATE {self.severity.upper()}:"]
        for f in self.failures:
            lines.append(f"  ✗ {f}")
        for r in self.recommendations:
            lines.append(f"  → {r}")
        return "\n".join(lines)

И обнови execute() чтобы использовать severity:

        if not checks.all_passed:
            state.feedback_from_qa = {
                "gate": self.__class__.__name__,
                "failures": checks.failures,
                "recommendations": checks.recommendations,
                "severity": checks.severity,
                "feedback_text": checks.to_feedback_string(),
            }

=== ВАЖНЫЕ ОГРАНИЧЕНИЯ ===

1. НЕ удаляй ничего из существующего SKILL.md — только добавляй
2. НЕ меняй структуру файлов (SKILL.md + 6 reference/*.py)
3. Сохрани все 12 правил R1-R12 как есть
4. Сохрани все {placeholder} синтаксис в шаблонах
5. После всех изменений покажи мне:
   - git diff для SKILL.md (первые 50 строк diff)
   - git diff для каждого изменённого reference/*.py
   - Подтверждение что шаблоны по-прежнему содержат все {placeholder}

=== ПОСЛЕ ЗАВЕРШЕНИЯ ===

Покажи итоговую структуру:
find .claude/skills/agent-builder/ -type f | head -20

И первые 40 строк обновлённого SKILL.md:
head -40 .claude/skills/agent-builder/SKILL.md
```

---

## Скилл #2: prompt-crafter 🔄 ПРОМПТ ГОТОВ

**Назначение**: При написании каждого промпта для агента — скилл подставляет релевантные принципы из 38 Prompt Design Principles (CLAUDE.md) и все hard bans.
**Расположение**: .claude/skills/prompt-crafter/ (LOCAL — D20)

**Промпт для Claude Code** — см. секцию "ПРОМПТ СОЗДАНИЯ PROMPT-CRAFTER" ниже.

---

## ПРОМПТ СОЗДАНИЯ PROMPT-CRAFTER

Промпт вынесен в отдельный файл для удобства копирования:
**`.context/PROMPT_FOR_CLAUDE_CODE_skill2_prompt_crafter.md`**

Скопируй содержимое между линиями === в Claude Code.

---

## Скилл #3: humanizer 🔄 ПРОМПТ ГОТОВ

**Назначение**: Интерактивный отладочный инструмент для проверки текста на AI-паттерны. НЕ production dependency (D10).
**Расположение**: ~/.claude/skills/humanizer/ (GLOBAL — D20, единственный generic скилл)
**Источник**: https://github.com/blader/humanizer

Промпт вынесен в отдельный файл:
**`.context/PROMPT_FOR_CLAUDE_CODE_skill3_humanizer.md`**

Этот промпт НЕ просто git clone — он:
1. Клонирует репозиторий
2. Анализирует покрытие паттернов (24 humanizer vs 53+8 наших)
3. Создаёт ADDON.md с нашими расширениями (P31-P53, F1-F8, Russian, AC-rules)
4. Создаёт PATTERN_MAP.md с полным маппингом
5. Добавляет YAML front matter
6. Описывает синергию с agent-builder и prompt-crafter
7. Генерирует отчёт анализа

---

## Скилл #4: academic-writer 🔄 ПРОМПТ ГОТОВ

**Назначение**: Самый критичный скилл проекта — качество СОДЕРЖАНИЯ академических текстов. 7 доменных шаблонов, 5-уровневая шкала глубины, чеклисты плотности фактов, красные флаги.
**Расположение**: .claude/skills/academic-writer/ (LOCAL — D20)
**Режим**: BUILD + RUNTIME (D7)

Промпт вынесен в отдельный файл:
**`.context/PROMPT_FOR_CLAUDE_CODE_skill4_academic_writer.md`**

Этот промпт создаёт 7 файлов:
1. SKILL.md — 6-Step Framework, 9 правил R1-R9, BUILD + RUNTIME процессы
2. reference/megaprompt_rules.md — ВЕРБАТИМ блоки 1-16 из academic_megaprompt.md
3. reference/domain_templates.md — 7 доменных шаблонов (it_cs, law, psychology, economics, humanities, media, general) с минимумами плотности
4. reference/synthesis_depth_rubric.md — 5-уровневая шкала + экспресс-тест
5. reference/content_density_checklist.md — метрики на 500 слов + доменные надбавки
6. reference/structural_patterns.md — структуры работ по стримам + GOST + workflow
7. reference/quality_red_flags.md — БЛОК 7.6 + БЛОК 12 + расширенные + доменные

Ожидаемый объём: ≥ 1500 строк (самый большой скилл — содержит полный мегапромпт в reference).

---

## Скиллы #5-8: БУДУТ НАПИСАНЫ ПОСЛЕ #4

Промпты для academic-visualizer, ac-gate, pattern-auditor, cost-aware-llm-pipeline будут написаны после создания academic-writer. Каждый следует 6-Step Framework.
