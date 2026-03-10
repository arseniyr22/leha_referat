# Промпт для Claude Code — Скилл #2: prompt-crafter

Скопируй всё содержимое ниже (между линиями ===) в Claude Code:

===

Создай Claude Code skill `prompt-crafter` в `.claude/skills/prompt-crafter/`.

ВАЖНО: Скилл размещается ЛОКАЛЬНО в проекте (`.claude/skills/`), НЕ глобально (`~/.claude/skills/`).

Также: при доработке agent-builder мы обнаружили что Claude Code не добавил `allowed_tools` в YAML front matter. Перед созданием prompt-crafter, добавь `allowed_tools` в agent-builder:

```yaml
# В файле .claude/skills/agent-builder/SKILL.md, строка 2-3, между --- и ---:
---
description: "Генерирует production-ready код агентов (worker, stage, gate, service, micro_manager) для системы AI Anti-Anti Plag с соблюдением архитектуры v3.1 FINAL"
allowed_tools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
---
```

Теперь создавай prompt-crafter.

## Структура файлов

```
.claude/skills/prompt-crafter/
├── SKILL.md                       # Основной файл скилла
└── reference/
    ├── principles.md              # 38 Prompt Design Principles (ПОЛНЫЙ текст)
    ├── hard_bans.md               # Все ban-листы (ПОЛНЫЙ текст — каждое слово)
    ├── ac_rules_for_prompts.md    # 15 AC-правил с условиями применения
    ├── russian_patterns.md        # Русские ban-листы (P7_russian, P29_russian)
    └── prompt_template.md         # Шаблон промпта агента
```

## Содержимое SKILL.md

```markdown
---
description: "Генерирует LLM-промпты для агентов системы AI Anti-Anti Plag, включая все обязательные принципы, hard bans и AC-правила"
allowed_tools: ["Read", "Write", "Edit", "Grep"]
---

# prompt-crafter

---

## 1. Name + Trigger

**Name**: prompt-crafter
**Trigger phrases**:
- "напиши промпт", "create prompt", "write prompt"
- "новый промпт для агента", "промпт для {имя агента}"
- "write agent prompt for {name}"
- "agents/prompts/", "создай промпт-файл"
- Любое упоминание создания файла в agents/prompts/

---

## 2. Goal

Сгенерировать LLM-промпт для агента системы AI Anti-Anti Plag за один вызов: промпт включает все обязательные принципы, hard bans, AC-правила и {{переменные}} для данного типа операции, домена, регистра и языка.

---

## 3. Step-by-Step Process

### Шаг 3.1 — Определить контекст промпта

Спросить пользователя (если не указано явно):
- **Для какого агента**: имя (например `hm2_scaffold_breaker`, `hm3_vocab_cleaner`)
- **Тип операции**: rewrite | analysis | classification | audit | generation
- **Целевые паттерны**: P1-P53, F1-F8 (можно через ссылку на stage, например "все паттерны Stage 2")
- **Язык**: ru | en | оба
- **Регистр**: academic | journalistic | general | academic-essay
- **Домен**: it_cs | law | psychology | economics | humanities | media | general

### Хардкодированные пути (НЕ искать — использовать напрямую)

```python
# Куда сохранять промпты:
PROMPTS_DIR = "agents/prompts/"

# Reference файлы этого скилла:
SKILL_REF = ".claude/skills/prompt-crafter/reference/"

# Источники данных (читать, НЕ менять):
CLAUDE_MD = "CLAUDE.md"                              # Спецификация проекта
PIPELINE_PROMPTS = "prompts/"                        # Существующие промпты pipeline/
CONFIG = "config.yaml"                               # p7_russian, p29_russian секции
```

### Шаг 3.2 — Выбрать релевантные принципы

Загрузить `.claude/skills/prompt-crafter/reference/principles.md`.

Выбрать принципы ПО ТИПУ ОПЕРАЦИИ (не все 38 — только релевантные):

| Тип операции | Принципы |
|---|---|
| rewrite | 1-6, 9-11, 14-19, 23-27, 31-33, 36-38 |
| analysis | 1, 5, 14, 30 |
| classification | 1, 5, 30 |
| audit | 1-2, 6, 11, 13-14, 16-18, 20-21, 23-30, 37-38 |
| generation | 1-4, 8-11, 14-19, 23-30 |
| voice_injection | 1-2, 7-8, 13, 16-22, 25-30, 34, 38 |

### Шаг 3.3 — Загрузить hard bans (ВСЕГДА)

Загрузить `.claude/skills/prompt-crafter/reference/hard_bans.md`.

ОБЯЗАТЕЛЬНО включить в КАЖДЫЙ rewrite/generation/voice_injection промпт:
1. P7 vocabulary banlist (21 основных + extended + importance-framing + paired-abstraction)
2. P10 triplet ban (zero tolerance)
3. P9 announcement opener ban (zero tolerance)
4. P29 connector ban list (Firstly/Secondly/Additionally = 0)
5. P24 paragraph-ending generalization ban
6. P28 substitution table (leverage→use, utilize→use, etc.)
7. F-rules для текущего регистра (F1-F8)
8. P44-P53 scaffold pattern bans (GPTZero-validated)

Для analysis/classification промптов: включить bans как КРИТЕРИИ ОБНАРУЖЕНИЯ (что искать), не как запреты на генерацию.

### Шаг 3.4 — Применить AC-rules

Загрузить `.claude/skills/prompt-crafter/reference/ac_rules_for_prompts.md`.

Применить условно:

**Если language=ru:**
- AC-1: Em dash — консервативное удаление (сохранить грамматически обязательные)
- AC-2: Цитаты — GOST [N] формат, НИКОГДА author-year
- AC-4: Passive voice — порог 70% (не 20% как в English)
- AC-5: Пропустить Op 8 (figurative language) в academic
- AC-6: Применить русские паттерны из reference/russian_patterns.md
- AC-7: Пропустить F5 (apostrophes) полностью; F6 = только запятые в journalistic
- AC-8: Кавычки — guillemets «» (не straight quotes "")
- AC-14: Русский P7 banlist из config.yaml:p7_russian
- AC-15: Пропустить perplexity-метрики (GPT-2 English only)

**Если register=academic:**
- AC-3: НЕ переупорядочивать макроструктуру ГОСТ (Введение, Главы, Заключение)
- AC-9: НЕ конвертировать в прозу: нумерованные разделы, библиографию, оглавление
- AC-10: Idea-order disruptor — только на уровне параграфов, не секций
- AC-5: Пропустить метафоры/аналогии в ru+academic

**Если register=journalistic:**
- Полный набор P30 (imperfection textures): fragments, register drops, discourse markers
- F5: 3-5 пропущенных апострофов
- F6: 2-3 minor grammar errors
- F7: 2-4 filler words

### Шаг 3.5 — Применить domain conventions (P41)

По домену — добавить специфичные инструкции:

| Домен | Инструкция для промпта |
|---|---|
| it_cs | Passive voice — НОРМА ("the model is trained"). Алгоритмы как proper nouns. Результаты с confidence intervals. Citation density: низкая (2-8 per 20 pages). |
| law | Каждое утверждение — со ссылкой. Citation density: высокая (50+ per 20 pages). Терминология — точная, не упрощать. |
| psychology | Hedging на эмпирических claims допустим. Rhetorical questions: 1-2 per 750 words. Результаты с p-values и CI. |
| economics | Named identification strategy (gravity model, IV regression, DiD). Hypothesis numbered + testable. |
| humanities | Parenthetical asides — высокая частота (49-116 per 20 pages). Long sentences (avg 34 words). |
| media | Аудиторные метрики, графики, бизнес-модели. Informal register допустим. |
| general | Стандартные правила без domain overrides. |

### Шаг 3.6 — Собрать промпт по шаблону

Загрузить `.claude/skills/prompt-crafter/reference/prompt_template.md` и заполнить:

```
[SYSTEM]
You are rewriting text for the domain of {{DOMAIN}} in {{LANGUAGE}} language.
Register: {{REGISTER}}. Target reader: {reader_profile}.
Your task: {one_sentence_task_description}.

[TRANSFORMATION INSTRUCTIONS]
{specific instructions from selected principles}
{pattern-specific transformation rules from CLAUDE.md}

[HARD BANS — ZERO TOLERANCE]
The following MUST NOT appear in output:
{full hard ban lists from reference/hard_bans.md}

[AC-RULES FOR THIS CONTEXT]
{selected AC-rules with specific instructions}

[DOMAIN CONVENTIONS]
{domain-specific conventions from step 3.5}

[NEGATIVE EXAMPLES]
DO NOT write: {bad_example}
WRITE INSTEAD: {good_example}

[QUALITY SELF-CHECK]
Before returning output, verify:
{audit checklist items relevant to this operation type}
```

### Шаг 3.7 — Включить {{переменные}}

ОБЯЗАТЕЛЬНЫЕ runtime-переменные в КАЖДОМ промпте:
- `{{LANGUAGE}}` — "ru" | "en"
- `{{DOMAIN}}` — it_cs | law | psychology | economics | humanities | media | general
- `{{REGISTER}}` — academic | journalistic | general | academic-essay

ЗАПРЕЩЕНО хардкодить значения language/domain/register — ТОЛЬКО через переменные.

### Шаг 3.8 — Показать для ревью

Показать сгенерированный промпт пользователю:
- "Промпт для {agent_name} готов. Проверь и подтверди."
- НЕ записывать файл автоматически — дождаться подтверждения

### Шаг 3.9 — Feedback Cycle (обязательный)

После записи промпта:
1. Проверить что файл `agents/prompts/{agent_name}.md` создан
2. Проверить что файл содержит: {{LANGUAGE}}, {{DOMAIN}}, {{REGISTER}}
3. Проверить что файл содержит секцию [HARD BANS]
4. Если worker для этого промпта уже существует — прогнать `python -m pytest tests/test_{agent_name}.py -v`
5. Записать в improvements.log:
   ```
   [DATE] [PROMPT_NAME] [FEEDBACK] — Checks: PASS/FAIL. Missing: {what}. Fixed: {how}.
   ```

---

## 4. Reference Files

### reference/principles.md

Содержит ПОЛНЫЙ текст всех 38 Prompt Design Principles.

КРИТИЧЕСКИ ВАЖНО: НЕ пересказывать принципы своими словами. Извлечь ДОСЛОВНО из CLAUDE.md, секции "Prompt Design Principles" (принципы 1-22) и "Prompt Design Principles — Continued (31-38)" (принципы 23-38).

Каждый принцип записать в формате:
```
### Principle N: {short_name}
{полный текст принципа из CLAUDE.md дословно}
```

Полный список:
1. Always specify register + target reader profile
2. Preserve all factual claims — only rewrite style
3. Explicitly forbid AI vocabulary banlist
4. Forbid generic transitions (P29 full list)
5. One specific transformation per prompt call
6. Include negative constraint example
7. Require two-pass audit (Stage 4 only)
8. Require personality injection (soul requirement)
9. Require structural asymmetry (para-CV >= 0.50)
10. Require conciseness (≤90% input word count)
11. Forbid announcement patterns (zero tolerance)
12. Require auditory test instruction
13. Require figurative language check (1+ per section)
14. Require active voice default (flag >20% passive; >70% for ru academic AC-4)
15. HARD BAN triplets (zero tolerance, all grammatical forms)
16. HARD BAN announcement openers (full list from P9)
17. HARD BAN "genuinely [adj]" constructions
18. Paragraph-ending rule — end on specific fact, not generalization
19. Meaning-first rewriting — internalize then rewrite
20. Epistemic hedging audit — flag false certainty
21. Tense variation check — flag >80% same tense
22. Require imperfection texture (P30, register-dependent)
23. Information-first rule — no importance announcements
24. No modal hedging on results (P32)
25. Repeat key terms — never synonym-cycle (P11)
26. But:However ratio ≥ 2:1 (P33)
27. Attribution-based hedging — hedge by naming source (P38)
28. Source evaluation — explain why source matters for THIS argument
29. Results presentation format — fact + baseline + mechanism (P36)
30. Domain conventions — apply P41 domain-specific norms
31. Open flat, not clever — no superlative importance openers (P44)
32. Destroy the scaffold — no consistent thesis→evidence→synthesis (P26)
33. No dramatic reveals — collapse "X wasn't A. It was B." (P45)
34. No meta-media commentary — never comment on coverage (P46)
35. No binary force projections — hedge futures, break binaries (P47)
36. No elegant reversals — "not X, it's Y" → state Y directly (P49)
37. Formatting compliance checklist (F1-F8 in full)
38. Green-sentence pattern — increase data-dense + uncertainty sentences (P38-target)

### reference/hard_bans.md

Содержит ПОЛНЫЕ, ДОСЛОВНЫЕ списки из CLAUDE.md. НЕ сокращать, НЕ пересказывать.

Извлечь из CLAUDE.md следующие блоки ПОЛНОСТЬЮ:

1. **P7 — AI Vocabulary Banlist** (из секции "P7 · AI Vocabulary Banlist"):
   - Основной список 21 слово: `additionally, align with, crucial, delve...`
   - Extended banlist: `delve into, dive into, realm, harness...`
   - Importance-framing banlist: `plays a crucial role, is central to...`
   - Paired-abstraction banlist: `opportunities and challenges, strengths and weaknesses...`
   - Domain exemption rules (когда P7 слова допустимы)

2. **P9 — Announcement Opener Banlist** (из секции "P9 · Negative Parallelisms"):
   - `Here's the problem with X` → delete
   - `X is worth a brief detour` → delete
   - `There's also a X worth flagging` → delete
   - (все 10+ конструкций из CLAUDE.md)

3. **P10 — Triplet Ban** (из секции "P10 · Rule of Three Overuse"):
   - Noun triplets, verb tricolons, adverbial tricolons
   - "partly to X, partly to Y, partly to Z"
   - Technical enumeration exception

4. **P28 — Substitution Table** (из секции "P28 · Formal Register Inflation"):
   - leverage→use, utilize→use, facilitate→help/enable...
   - (полная таблица)

5. **P29 — Connector Bans** (из секции "P29 · Connector Monotony"):
   - Absolute ban: Firstly, Secondly, Thirdly, Finally, Additionally
   - Near-ban: Furthermore (≤1 per document)
   - Rate-limited: Moreover (≤1 per 500 words)
   - Permitted + Encouraged lists
   - Target But:However ratio ≥ 2:1

6. **P24 — Paragraph-ending Generalization Ban**:
   - "complicates any [adj] story about X"
   - "repeats the same [noun] across X"
   - (все конструкции)

7. **P44-P53 — GPTZero Scaffold Pattern Bans**:
   - P44: Superlative importance opener
   - P45: Two-sentence dramatic reveal
   - P46: Meta-media commentary
   - P47: Binary future force projection
   - P48: Binary neither wrap-up
   - P49: Elegant reversal
   - P50: Same-X-that-also
   - P51: Whether-or-just closure
   - P52: Mechanism attribution run-on
   - P53: Participial simultaneity

8. **F1-F8 — Formatting Fingerprint Rules**:
   - F1: No Oxford comma
   - F2: 0 em dashes (ALL registers)
   - F3: 0 semicolons (journalistic); ≤1/500w (academic)
   - F4: 0 colons in body paragraphs (journalistic); ≤1/300w (academic)
   - F4b: ≤1 parenthetical per 300w (academic); 0-1/500w (journalistic)
   - F5: 3-5 missing apostrophes (journalistic only)
   - F6: 2-3 controlled grammar errors (journalistic only)
   - F7: 2-4 filler words (journalistic only)
   - F8: 0 invented hyphenated compounds

### reference/russian_patterns.md

Из CLAUDE.md извлечь ПОЛНОСТЬЮ:

1. **P7_russian — Russian AI Vocabulary Banlist**:
   - Absolute ban: следует отметить, является ключевым, играет важную роль...
   - Importance-framing ban: играет важную роль в, является ключевым для...
   - Announcement ban: следует отметить что, необходимо отметить что...

2. **P29_russian — Russian Connector Rules**:
   - Absolute ban (0): во-первых, во-вторых, в-третьих, помимо этого
   - Near-ban (≤1): кроме того
   - Rate-limited: более того, помимо прочего
   - Permitted: также, однако, но, при этом, между тем...
   - Target Но:Однако ratio ≥ 2:1

3. **Russian P10**: Triplet ban applies identically
4. **Russian P32**: Modal hedging ban — может, мог бы, вероятно, по-видимому...
5. **Russian F-rules differences**: F2 conservative, F3 academic semicolons allowed, F5 skip, F6 skip academic...

### reference/ac_rules_for_prompts.md

Все 15 AC-правил в формате:

```
### AC-N: {name} [{priority}]
**Условие**: когда применять
**Действие**: что делать в промпте
**Не применять**: когда пропустить
```

Извлечь из CLAUDE.md секцию "Anti-Conflict Rules (AC-1 through AC-15)" ПОЛНОСТЬЮ.

### reference/prompt_template.md

Базовый шаблон:

```markdown
# Agent Prompt: {agent_name}
# Type: {operation_type} | Patterns: {pattern_list} | Stage: {stage_number}

[SYSTEM]
You are rewriting text for the domain of {{DOMAIN}} in {{LANGUAGE}} language.
Register: {{REGISTER}}.
Target reader: {reader_profile}.
Your task: {one_sentence_task_description}.

Preserve ALL factual claims. Change ONLY style and structure. Never invent new information.

[TRANSFORMATION INSTRUCTIONS]

{specific_instructions}

[HARD BANS — ZERO TOLERANCE]

The following MUST NOT appear in output under any circumstances:

{hard_bans_section}

[AC-RULES]

{ac_rules_section}

[DOMAIN CONVENTIONS — {{DOMAIN}}]

{domain_conventions}

[NEGATIVE EXAMPLES]

DO NOT write:
> {bad_example_1}

WRITE INSTEAD:
> {good_example_1}

DO NOT write:
> {bad_example_2}

WRITE INSTEAD:
> {good_example_2}

[QUALITY SELF-CHECK — verify before returning]

{quality_checklist}
```

---

## 5. Rules (Guardrails)

**R1 — Одна трансформация**: Каждый промпт — ОДНА операция. Никогда не комбинировать Stage 2 + Stage 3 в одном промпте. Одному worker = один промпт.

**R2 — Hard bans ВСЕГДА**: Hard bans включаются в КАЖДЫЙ rewrite/generation промпт, даже если кажутся нерелевантными. Лучше повторить чем пропустить.

**R3 — Runtime переменные**: {{LANGUAGE}}, {{DOMAIN}}, {{REGISTER}} — в каждом промпте. Никогда не хардкодить "ru" или "academic" — только через {{переменные}}.

**R4 — Промпт отдельным файлом**: Промпт сохраняется в `agents/prompts/{agent_name}.md`. НИКОГДА inline в Python-коде.

**R5 — Температура по типу**: Rewrite/generation: 0.85-1.1. Analysis/classification: 0.2-0.4.

**R6 — Негативный пример обязателен**: Каждый rewrite промпт содержит минимум 2 пары "НЕ пиши так / Пиши так".

**R7 — Русские эквиваленты**: Если промпт для language=ru или language=оба — включить русские ban-листы из reference/russian_patterns.md В ДОПОЛНЕНИЕ к английским.

**R8 — Не дублировать CLAUDE.md**: Reference files содержат извлечения из CLAUDE.md. Промпт НЕ должен копировать весь CLAUDE.md — только релевантные секции через reference/.

**R9 — Preserve existing prompts**: Если в `prompts/` (pipeline prompts) уже есть промпт для этой stage — ПРОЧИТАТЬ его перед генерацией нового. Новый промпт в agents/prompts/ должен покрывать всё что покрывал старый + добавлять hard bans и AC-rules.

---

## 6. Self-Improvement

### Feedback cycle
После каждого сгенерированного промпта:
1. Проверить наличие {{LANGUAGE}}, {{DOMAIN}}, {{REGISTER}}
2. Проверить наличие секции [HARD BANS]
3. Проверить наличие минимум 2 negative examples
4. Если worker уже есть → прогнать тест
5. Записать в `.claude/skills/prompt-crafter/improvements.log`

### Лог эффективности
Вести `reference/prompt_effectiveness.log`:
```
[DATE] [AGENT_NAME] [PROMPT_VERSION] — Metrics: {which metrics improved}. Issues: {remaining tells}.
```

### Обновление reference/
Если одно и то же слово/конструкция пропускается 2+ раза разными промптами → добавить в reference/hard_bans.md и записать:
```
[BAN_UPDATE] reference/hard_bans.md — добавлено: "{word}" в секцию {section}
```
```

---

## Содержание reference/ файлов

КРИТИЧЕСКИ ВАЖНО: reference/ файлы должны содержать ПОЛНЫЕ, ДОСЛОВНЫЕ извлечения из CLAUDE.md. Не сокращать, не пересказывать.

### Как извлекать данные:

1. Прочитай CLAUDE.md (файл в корне проекта)
2. Для principles.md → найди секции "Prompt Design Principles" и "Prompt Design Principles — Continued (31-38)". Извлеки КАЖДЫЙ принцип с полным текстом.
3. Для hard_bans.md → найди секции P7, P9, P10, P24, P28, P29, P44-P53, F1-F8. Извлеки КАЖДЫЙ список слов/конструкций ЦЕЛИКОМ.
4. Для russian_patterns.md → найди секции "Russian P7 Banlist", "Russian P29 Connector Rules", "Russian P10", "Russian P32", "Russian F-Rules Differences". Извлеки ПОЛНОСТЬЮ.
5. Для ac_rules_for_prompts.md → найди секцию "Anti-Conflict Rules (AC-1 through AC-15)". Извлеки ВСЕ 15 правил с полным описанием.

НЕ пиши "(см. CLAUDE.md)" — КОПИРУЙ содержимое в reference файл. Весь смысл reference/ — Claude Code не должен каждый раз перечитывать CLAUDE.md целиком.

---

## Verification

После создания проверь:

1. `find .claude/skills/prompt-crafter/ -type f` → 6 файлов (SKILL.md + 5 reference)
2. `head -5 .claude/skills/prompt-crafter/SKILL.md` → начинается с YAML front matter `---`
3. `grep -c "{{LANGUAGE}}" .claude/skills/prompt-crafter/reference/prompt_template.md` → >= 1
4. `grep -c "additionally" .claude/skills/prompt-crafter/reference/hard_bans.md` → >= 1 (слово присутствует в banlist)
5. `grep -c "следует отметить" .claude/skills/prompt-crafter/reference/russian_patterns.md` → >= 1
6. `grep -c "AC-1" .claude/skills/prompt-crafter/reference/ac_rules_for_prompts.md` → >= 1
7. `wc -l .claude/skills/prompt-crafter/reference/hard_bans.md` → >= 100 строк (полные списки, не заглушки)
8. `wc -l .claude/skills/prompt-crafter/reference/principles.md` → >= 150 строк (все 38 принципов с текстом)

ВАЖНО: Если reference/ файлы содержат заглушки типа "(содержит...)" или "(извлечь из CLAUDE.md)" вместо реального содержимого — это ПРОВАЛ. Каждый reference файл должен содержать ПОЛНЫЕ данные.

===
