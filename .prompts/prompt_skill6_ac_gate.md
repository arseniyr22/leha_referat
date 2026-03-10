# Промпт для создания скилла `ac-gate`

## Контекст для Claude Code

Ты создаёшь скилл `ac-gate` для проекта AI Anti-Anti Plag — production-grade текстовой гуманизации. Проект описан в `CLAUDE.md` в корне репозитория.

В проекте есть 15 Anti-Conflict Rules (AC-1 — AC-15), которые разрешают конфликты между `prompts/academic_megaprompt.md` (русскоцентричный) и английскоцентричным pipeline (Stages 1–5). Без строгого соблюдения этих правил pipeline ломает русский академический текст: удаляет грамматически обязательные тире, конвертирует ГОСТ-ссылки [N] в author-year, снижает пассивный залог ниже нормы, вставляет метафоры в ВКР и т.д.

Скилл `ac-gate` — это **gate-валидатор**, который гарантирует, что каждый компонент pipeline (код, промпты, конфиги, выходной текст) соблюдает все 15 AC-правил. Он работает и как BUILD-инструмент (при написании кода/промптов), и как RUNTIME-проверка (при прогоне текста через pipeline).

---

## Инструкции по созданию

### Структура файлов

Создай скилл в `.claude/skills/ac-gate/` со следующей структурой:

```
.claude/skills/ac-gate/
├── SKILL.md                           # Основной файл скилла (≤500 строк)
└── reference/
    ├── ac_rules_full.md               # Все 15 AC-правил: verbatim из CLAUDE.md + decision logic
    ├── stage_ac_matrix.md             # Матрица "какой AC применяется в каком Stage"
    ├── russian_adaptation_rules.md    # Русская адаптация: P7/P29/P10/P32/F-rules различия
    └── violation_patterns.md          # Конкретные паттерны нарушений с примерами
```

### SKILL.md — Структура (6 секций по формату academic-writer)

**YAML front matter:**
```yaml
---
description: "Gate-валидатор Anti-Conflict Rules (AC-1—AC-15): проверяет код, промпты, конфиги и выходной текст на соблюдение языковых/регистровых/доменных адаптаций. BUILD+RUNTIME. Предотвращает поломку русского академического текста англоцентричным pipeline."
---
```

**Секция 1: Имя и триггер**
- Имя: ac-gate
- Триггер: при написании/модификации любого Stage (1–5), при написании промптов, при проверке pipeline output, при добавлении нового AC-правила
- Команда: `/ac-gate [mode] [target]`
- Примеры:
  - `/ac-gate build structural_rewriter.py` — проверить код Stage 2 на AC-соблюдение
  - `/ac-gate build prompts/voice_injection.md` — проверить промпт Stage 4
  - `/ac-gate runtime` — проверить текст на выходе pipeline
  - `/ac-gate audit config.yaml` — проверить config на наличие всех AC-параметров
  - `/ac-gate` без аргументов — интерактивный режим

**Секция 2: Цель**

Гарантировать, что ни один компонент pipeline не нарушает Anti-Conflict Rules. Каждое AC-правило — это языковой, регистровый или доменный gate, который предотвращает деструктивное применение англоцентричных трансформаций к русскому/академическому тексту.

Что входит в зону ответственности:
1. Проверка Python-кода pipeline stages на наличие language/register gates
2. Проверка LLM-промптов на включение {{LANGUAGE}} и AC-совместимых инструкций
3. Проверка config.yaml на наличие всех AC-параметров
4. Проверка выходного текста (RUNTIME) на AC-нарушения
5. Генерация AC-compliance report

Что НЕ входит:
- Проверка паттернов P1–P53 — зона humanizer и pattern-auditor
- Качество содержания — зона academic-writer
- Визуализации — зона academic-visualizer
- ГОСТ-форматирование .docx — зона formatter

**Секция 3: Пошаговый процесс**

#### BUILD-режим (проверка кода / промптов / конфигов)

**Шаг 3.1: Определить target type**
```
code   → Python файл pipeline stage (*.py)
prompt → LLM промпт (prompts/*.md)
config → config.yaml
all    → полный аудит всех компонентов
```

**Шаг 3.2: Загрузить AC-матрицу для target**
→ Прочитать `reference/stage_ac_matrix.md`
→ Определить, какие AC-правила применяются к данному target
→ Для каждого применимого AC: загрузить decision logic из `reference/ac_rules_full.md`

**Шаг 3.3: BUILD проверка кода (для code target)**
Для каждого применимого AC-правила проверить:

**AC-1 (Em Dash Language Gate):**
- [ ] Есть ли `if language == 'ru':` gate перед `reduce_em_dashes()`?
- [ ] Вызывается ли `reduce_em_dashes_ru()` для русского (conservative: >3 per para)?
- [ ] Для English: target = 0 em dashes?

**AC-2 (GOST [N] vs Author-Year):**
- [ ] Есть ли `citation_format` параметр?
- [ ] При `language='ru' AND register='academic'`: GOST [N] NEVER конвертируется в author-year?
- [ ] При других комбинациях: author-year формат применяется?

**AC-3 (GOST Macro-Structure):**
- [ ] P26 idea-order disruptor НЕ переставляет GOST section markers?
- [ ] Список protected markers: title_page, annotation, toc, introduction, chapters (by number), conclusion, references?
- [ ] P26 ограничен paragraph-level для academic register?

**AC-4 (Passive Voice Threshold):**
- [ ] Есть ли language+register gate перед passive voice flagging?
- [ ] `language='ru' AND register='academic'`: threshold = 0.70?
- [ ] English/non-academic: threshold = 0.20?
- [ ] Threshold читается из `config.yaml: discourse.academic_ru_passive_threshold`?

**AC-5 (Figurative Language):**
- [ ] Op 8 (metaphor/analogy injection) SKIP когда `language='ru' AND register='academic'`?
- [ ] Op 8 SKIP для math domain?
- [ ] Op 8 APPLY для Russian journalistic/essay?

**AC-6 (Russian Regex Patterns):**
- [ ] Для `language='ru'`: вызывается `_apply_russian_patterns(text, config)`?
- [ ] Используются `p7_russian` и `p29_russian` config blocks?
- [ ] Промпт-шаблоны содержат `{{LANGUAGE}}` variable?

**AC-7 (F5/F6 in Russian/Academic):**
- [ ] `language='ru'`: F5 (apostrophe drops) SKIP entirely?
- [ ] `language='ru'`: F6 = comma variation only (1-2 instances)?
- [ ] `register='academic'` (любой язык): F5 AND F6 SKIP entirely?
- [ ] `language='en' AND register='journalistic'`: F5 (3-5 drops) + F6 (2-3 errors) APPLY?

**AC-8 (Quote Normalization):**
- [ ] `language='en'`: normalize to ASCII straight quotes `"`?
- [ ] `language='ru'`: normalize to guillemets «» via `normalize_quotes_ru()`?

**AC-9 (List-to-Prose Scope):**
- [ ] P15 list-to-prose NEVER converts: numbered section markers (1.1, Глава N), bibliography entries, TOC items?
- [ ] P15 ONLY converts: content bullets with "**Header:** Content" format?

**AC-10 (Idea-Order Disruptor Gating):**
- [ ] Op 11 assert `register in ['academic', 'academic-essay', 'journalistic', 'general']`?
- [ ] `register='academic'`: Op 11 = paragraph level only, NEVER macro-structure?

**AC-11 (Standalone Definitions):**
- [ ] `language='en'`: converts "X is defined as Y" form?
- [ ] `language='ru'`: converts "Под X понимается Y" form?

**AC-12 (But:However → Но:Однако):**
- [ ] `language='ru'`: `but_however_ratio` = None в score report?
- [ ] `language='ru'`: вместо этого reports `no_odnako_ratio` (Но:Однако ≥ 2:1)?

**AC-13 (Citation Density vs GOST minimums):**
- [ ] Per-page citation density (Stage 5) и GOST stream source minimums (Phase 0A) enforced INDEPENDENTLY?
- [ ] Оба метрики присутствуют в score report?

**AC-14 (Russian P7 Words):**
- [ ] `p7_russian` config block существует и содержит absolute ban, importance-framing ban, announcement ban?
- [ ] `_apply_russian_patterns()` метод вызывается для `language='ru'`?

**AC-15 (Perplexity for Russian):**
- [ ] `language='ru'`: `_skip_perplexity=True`?
- [ ] Score report: "N/A (Russian text)" для perplexity fields?

**Шаг 3.4: BUILD проверка промптов (для prompt target)**
Для каждого промпта проверить:
- [ ] Содержит `{{LANGUAGE}}` variable?
- [ ] Содержит `{{REGISTER}}` variable?
- [ ] Содержит `{{DOMAIN}}` variable (если domain-зависимый)?
- [ ] Инструкции НЕ противоречат AC-правилам для соответствующего Stage?
- [ ] Для Stage 2 промптов: нет инструкции переставлять ГОСТ-секции (AC-3)?
- [ ] Для Stage 3 промптов: нет инструкции конвертировать [N] → author-year для RU+academic (AC-2)?
- [ ] Для Stage 4 промптов: нет инструкции вставлять метафоры для RU+academic (AC-5)?
- [ ] Для Stage 4 промптов: нет инструкции вставлять F5/F6 для academic register (AC-7)?
- [ ] Для всех промптов: нет инструкции убирать ВСЕ em dashes без language gate (AC-1)?

**Шаг 3.5: BUILD проверка config.yaml**
Проверить наличие следующих параметров:
```yaml
# AC-1
structural.em_dash_ru_max_per_paragraph: 3

# AC-4
discourse.academic_ru_passive_threshold: 0.70
discourse.default_passive_threshold: 0.20

# AC-6 + AC-14
p7_russian:
  absolute_ban: [список]
  importance_framing_ban: [список]
  announcement_ban: [список]

p29_russian:
  absolute_ban: [во-первых, во-вторых, в-третьих, помимо этого]
  near_ban: [кроме того]
  rate_limited: [более того, помимо прочего]
  permitted: [также, однако, но, при этом, между тем, тем не менее, вместе с тем]
  encouraged: [также, но]
  target_no_odnako_ratio: 2.0

# AC-12
scoring.ru_no_odnako_ratio_target: 2.0

# AC-15
scoring.skip_perplexity_for_russian: true
```

**Шаг 3.6: Сгенерировать BUILD report**
```json
{
  "target": "pipeline/structural_rewriter.py",
  "target_type": "code",
  "applicable_ac_rules": ["AC-1", "AC-3", "AC-6", "AC-8", "AC-9", "AC-10"],
  "results": {
    "AC-1": {"status": "PASS", "evidence": "language gate at line 47"},
    "AC-3": {"status": "FAIL", "issue": "P26 disruptor has no GOST section protection", "fix": "Add protected_sections list at line 82"},
    "AC-6": {"status": "PASS", "evidence": "_apply_russian_patterns() called at line 63, {{LANGUAGE}} present"},
    "AC-8": {"status": "PASS", "evidence": "normalize_quotes_ru() called at line 119"},
    "AC-9": {"status": "WARN", "issue": "List-to-prose has no TOC protection", "fix": "Add TOC detection regex before conversion"},
    "AC-10": {"status": "PASS", "evidence": "register assertion at line 95"}
  },
  "overall": "FAIL",
  "blocking_issues": 1,
  "warnings": 1
}
```

#### RUNTIME-режим (проверка текста на выходе pipeline)

**Шаг R.1: Определить language + register + domain**
```
language → 'ru' | 'en'
register → 'academic' | 'academic-essay' | 'journalistic' | 'general'
domain   → 'it_cs' | 'law' | 'psychology' | 'economics' | 'humanities' | 'media' | 'general'
```
Если не указаны — определить из контекста pipeline state или запросить.

**Шаг R.2: Применить AC-фильтры к тексту**

Для `language='ru'`:
- **AC-1**: Подсчитать em dashes. Если >3 на абзац → WARN (AI overuse). Если 0 и в тексте есть копулярные предложения → FAIL (pipeline удалил грамматически обязательные).
  - Детекция: regex `— ` в контексте `[Существительное] — [существительное/прилагательное]` = обязательное тире. Пример: "Москва — столица России" — ДОЛЖНО сохраниться.
- **AC-2**: Если register='academic': поиск author-year паттернов `([А-ЯA-Z][а-яa-z]+\s*\(\d{4}\))` — если найдены → FAIL (author-year ВСЕГДА ошибочен в RU+academic, даже если ГОСТ [N] тоже присутствует).
  - Допустимо: "Как утверждает Петров [4], ..." — автор + [N].
  - Недопустимо: "Петров (2019) утверждает, что..." — author-year без [N].
  - Недопустимо: "Петров (2019) [4]" — author-year + [N] одновременно (author-year = лишний).
- **AC-4**: Если register='academic': подсчитать % пассивного залога. Если <40% → WARN (pipeline чрезмерно конвертировал в актив — норма русского академического текста 50%+). Если 40–70% → PASS. Если >70% → INFO (в пределах порога, но на верхней границе).
- **AC-5**: Если register='academic': поиск метафор/аналогий. Если найдены → WARN (pipeline вставил метафоры в ВКР).
- **AC-6**: Поиск русских AI-паттернов из p7_russian banlist. Если найдены → FAIL (pipeline не применил русские regex).
- **AC-7**: Если register='academic': поиск F5 (apostrophe drops) и F6 (grammar errors). Если найдены → FAIL (pipeline вставил F5/F6 в академический текст).
- **AC-8**: Поиск ASCII straight quotes `"` в русском тексте. Если найдены → WARN (должны быть «»).
- **AC-12**: Подсчитать Но vs Однако. Если ratio <2:1 → WARN.
- **AC-14**: Поиск русских P7 фраз (следует отметить, является ключевым и др.). Если найдены → FAIL.

Для `language='en'`:
- **AC-1**: em dashes count. Если >0 → FAIL (target = 0 для English; AC-1 = HIGH priority).
- **AC-8**: guillemets «» в English тексте. Если найдены → FAIL.
- **AC-12**: But:However ratio. Если <2:1 → WARN.
- **AC-15**: perplexity score present. Если "N/A" → FAIL (English must have perplexity).

Для register='academic' (любой язык):
- **AC-3**: GOST section markers в правильном порядке. Порядок: Введение → Глава 1 → Глава 2 → ... → Заключение → Список литературы.
- **AC-5**: Нет метафор/аналогий (RU academic и math domain). Для EN academic и других комбинаций — AC-5 не применяется (метафоры допустимы).
- **AC-7**: Нет F5 и F6 (любой язык academic).
- **AC-9**: TOC, bibliography, numbered sections НЕ конвертированы в прозу.
- **AC-10**: Macro-structure сохранена (chapters в правильном порядке).

**Шаг R.3: Сгенерировать RUNTIME report**
```json
{
  "language": "ru",
  "register": "academic",
  "domain": "economics",
  "ac_checks": {
    "AC-1": {"status": "PASS", "em_dashes_total": 12, "grammatically_required": 10, "ai_overuse": 2, "max_per_paragraph": 2},
    "AC-2": {"status": "PASS", "gost_citations_found": 34, "author_year_found": 0},
    "AC-4": {"status": "PASS", "passive_voice_pct": 0.58, "threshold": 0.70},
    "AC-5": {"status": "PASS", "metaphors_found": 0},
    "AC-6": {"status": "FAIL", "russian_p7_violations": ["следует отметить (line 42)", "является ключевым (line 87)"]},
    "AC-7": {"status": "PASS", "f5_found": 0, "f6_found": 0},
    "AC-8": {"status": "WARN", "straight_quotes_found": 3, "guillemets_found": 28},
    "AC-12": {"status": "PASS", "no_count": 14, "odnako_count": 5, "ratio": 2.8},
    "AC-14": {"status": "FAIL", "violations": ["играет важную роль (line 23)"]},
    "AC-15": {"status": "PASS", "perplexity_skipped": true}
  },
  "overall": "FAIL",
  "blocking_issues": ["AC-6: 2 Russian P7 violations", "AC-14: 1 importance-framing violation"],
  "warnings": ["AC-8: 3 straight quotes should be guillemets"]
}
```

#### AUDIT-режим (полный аудит всей системы)

**Шаг A.1**: Последовательно проверить:
1. `config.yaml` → Шаг 3.5
2. `pipeline/analyzer.py` → BUILD с AC-6, AC-14, AC-15
3. `pipeline/structural_rewriter.py` → BUILD с AC-1, AC-3, AC-6, AC-8, AC-9, AC-10
4. `pipeline/lexical_enricher.py` → BUILD с AC-2, AC-6, AC-8, AC-11, AC-14
5. `pipeline/discourse_shaper.py` → BUILD с AC-4, AC-5, AC-6, AC-7
6. `pipeline/scorer.py` → BUILD с AC-1, AC-3, AC-6, AC-12, AC-13, AC-14, AC-15
7. Все промпты в `prompts/` → Шаг 3.4
8. Сводный отчёт

**Секция 4: Reference-файлы**

| Файл | Шаг | Содержимое |
|------|-----|------------|
| `reference/ac_rules_full.md` | 3.2, 3.3, R.2 | Все 15 AC-правил verbatim + decision tree для каждого |
| `reference/stage_ac_matrix.md` | 3.2, A.1 | Матрица Stage × AC с указанием что именно проверять |
| `reference/russian_adaptation_rules.md` | R.2 | Русские P7/P29/P10/P32/F-rules различия |
| `reference/violation_patterns.md` | 3.3, R.2 | Конкретные regex/code паттерны нарушений |

**Секция 5: Правила**

**R1 — БЛОКИРУЮЩИЙ = БЛОКИРУЮЩИЙ.** Если хотя бы одно AC-правило с приоритетом HIGH нарушено — overall = FAIL. Pipeline НЕ ДОЛЖЕН продолжать до исправления.

**R2 — Приоритеты AC.** HIGH = AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 (6 правил). MEDIUM-HIGH = AC-7, AC-9 (2 правила). MEDIUM = AC-8, AC-10 (2 правила). LOW = AC-11, AC-12, AC-13, AC-14, AC-15 (5 правил). HIGH violations → FAIL. MEDIUM-HIGH → FAIL (но можно override с аргументом `--allow-medium`). MEDIUM и LOW → WARN.

**R3 — Language gate обязателен.** Каждый Stage-файл ОБЯЗАН содержать `language` параметр и ветвление по нему. Отсутствие language gate = автоматический FAIL по AC-6.

**R4 — Register gate обязателен.** Каждый Stage 2/3/4 файл ОБЯЗАН содержать `register` параметр. Отсутствие register gate = автоматический FAIL по AC-4/AC-5/AC-7.

**R5 — Config completeness.** Все 15 AC-правил ОБЯЗАНЫ иметь соответствующие параметры в config.yaml. Отсутствие параметра = FAIL.

**R6 — Prompt completeness.** Каждый промпт для Stages 2–4 ОБЯЗАН содержать `{{LANGUAGE}}` и `{{REGISTER}}`. Отсутствие = FAIL по AC-6.

**R7 — RUNTIME != BUILD.** BUILD проверяет код на НАЛИЧИЕ gates. RUNTIME проверяет текст на РЕЗУЛЬТАТ gates. Оба режима необходимы — BUILD ловит архитектурные ошибки, RUNTIME ловит runtime bugs.

**R8 — False positive mitigation.** Для AC-1 (em dashes в русском): regex детекции грамматически обязательных тире должен различать:
- `[Сущ.] — [Сущ./Прил.]` = обязательное (копула) → сохранить
- `— [конструкция]` после запятой или в середине предложения = стилистическое → кандидат на удаление
- Два или более `—` в одном предложении = AI overuse → удалить лишние

**R9 — Incremental updates.** При добавлении AC-16+ в CLAUDE.md:
1. Добавить правило в `reference/ac_rules_full.md`
2. Добавить в `reference/stage_ac_matrix.md`
3. Добавить паттерны нарушений в `reference/violation_patterns.md`
4. Обновить приоритет в R2

**R10 — Synergy map compliance.** Проверки ac-gate ДОЛЖНЫ быть синхронизированы с Megaprompt–Pipeline Synergy Map из CLAUDE.md. Каждый row в synergy map, упоминающий AC-правило, должен быть покрыт соответствующей проверкой.

**Секция 6: Self-Improvement Log**
```
v1.0 — Initial creation
```

---

### reference/ac_rules_full.md — Содержимое

Для КАЖДОГО из 15 AC-правил включить:

1. **Номер и имя** (verbatim из CLAUDE.md)
2. **Приоритет**: HIGH / MEDIUM-HIGH / MEDIUM / LOW
3. **Конфликт**: что именно конфликтует (megaprompt rule vs pipeline operation)
4. **Decision tree** (if-then logic):
```
IF language == 'ru' AND register == 'academic':
    → применить conservative em dash reduction (>3 per para)
    → сохранить грамматически обязательные
ELIF language == 'ru' AND register != 'academic':
    → применить moderate reduction
ELIF language == 'en':
    → применить full reduction (target: 0)
```
5. **Affected stages**: список Stage-ов, где правило применяется
6. **Config parameter**: ключ в config.yaml
7. **Verification method**: как BUILD и RUNTIME проверяют соблюдение

Полный decision tree для всех 15 правил:

**AC-1 — Em Dash Language Gate [HIGH]**
```
Конфликт: F2 требует 0 em dashes → русская грамматика требует em dashes в копулярных предложениях
Stages: Stage 2 (structural_rewriter.py)
Config: structural.em_dash_ru_max_per_paragraph = 3

IF language == 'en':
    target = 0 em dashes
    method = reduce_em_dashes()
ELIF language == 'ru':
    target = preserve grammatically required, reduce AI overuse (>3/para)
    method = reduce_em_dashes_ru()

BUILD check: function exists + language gate present
RUNTIME check: em_dash_count + grammatical_analysis
```

**AC-2 — Attribution Format [HIGH]**
```
Конфликт: Stage 3 instructs author-year → ГОСТ 7.32-2017 требует [N]
Stages: Stage 3 (lexical_enricher.py), Stage 4 (discourse_shaper.py)
Config: N/A (hardcoded gate on language+register)

IF language == 'ru' AND register == 'academic':
    citation_format = 'GOST'
    NEVER convert [N] to author-year
    Format: "Как утверждает [Автор] [N], ..."
ELSE:
    citation_format = 'AUTHOR_YEAR'
    Format: "Keohane (1969) suggests..."

BUILD check: citation_format parameter exists + conditional logic
RUNTIME check: regex for author-year pattern absence in RU+academic
```

**AC-3 — GOST Macro-Structure [HIGH]**
```
Конфликт: P26 idea-order disruptor может переставить ГОСТ-секции
Stages: Stage 2 (structural_rewriter.py)
Config: N/A (hardcoded protected list)

protected_sections = [title_page, annotation, toc, introduction,
                      chapter_1...N (by number), conclusion, references]

IF register == 'academic':
    P26 applies ONLY to paragraph-level (within sections)
    NEVER reorder section markers
ELSE:
    P26 applies at section and paragraph level

BUILD check: protected_sections list exists + P26 scope restriction
RUNTIME check: section order validation (Введение before Глава 1, etc.)
```

**AC-4 — Passive Voice Threshold [HIGH]**
```
Конфликт: Stage 4 flags >20% passive → Russian academic norm = 50%+
Stages: Stage 4 (discourse_shaper.py)
Config: discourse.academic_ru_passive_threshold = 0.70, discourse.default_passive_threshold = 0.20

IF language == 'ru' AND register == 'academic':
    passive_threshold = 0.70
ELSE:
    passive_threshold = 0.20

BUILD check: threshold from config + language+register gate
RUNTIME check: passive_voice_pct vs threshold
```

**AC-5 — Figurative Language [HIGH]**
```
Конфликт: Stage 4 Pass A Op 8 injects metaphors → Russian VKR = no metaphors
Stages: Stage 4 (discourse_shaper.py)
Config: N/A (hardcoded gate)

IF language == 'ru' AND register == 'academic':
    SKIP Op 8 entirely
ELIF domain == 'math':
    SKIP Op 8 entirely
ELSE:
    APPLY Op 8 (1-2 metaphors per section)

BUILD check: Op 8 skip condition exists
RUNTIME check: metaphor/analogy detection in RU+academic output
```

**AC-6 — Russian Regex Patterns [HIGH]**
```
Конфликт: All regex patterns English-only → Russian AI patterns go undetected
Stages: ALL stages (1-5)
Config: p7_russian block + p29_russian block

IF language == 'ru':
    APPLY _apply_russian_patterns(text, config) using p7_russian + p29_russian
    Prompt templates: include {{LANGUAGE}} variable
ELSE:
    APPLY standard English regex patterns

BUILD check: _apply_russian_patterns() method exists + {{LANGUAGE}} in prompts
RUNTIME check: Russian P7/P29 banlist scan
```

**AC-7 — F5/F6 in Russian/Academic [MEDIUM-HIGH]**
```
Конфликт: Pass B injects F5 (apostrophe drops) + F6 (grammar errors) → inapplicable to Russian/academic
Stages: Stage 4 (discourse_shaper.py)
Config: N/A (hardcoded gate)

IF register == 'academic' (any language):
    SKIP F5 AND F6 entirely
ELIF language == 'ru':
    SKIP F5 entirely
    F6 = comma placement variation only (1-2 instances)
ELIF language == 'en' AND register == 'journalistic':
    APPLY F5 (3-5 drops) + F6 (2-3 errors)

BUILD check: F5/F6 skip conditions exist
RUNTIME check: apostrophe drop detection + grammar error detection in academic text
```

**AC-8 — Quote Normalization [MEDIUM]**
```
Конфликт: Stage 2/3 normalizes to ASCII " → Russian uses «»
Stages: Stage 2, Stage 3
Config: N/A

IF language == 'en':
    normalize to ASCII straight quotes "
ELIF language == 'ru':
    normalize to guillemets «» via normalize_quotes_ru()

BUILD check: normalize_quotes_ru() exists + language gate
RUNTIME check: straight quote count in Russian text
```

**AC-9 — List-to-Prose Scope [MEDIUM-HIGH]**
```
Конфликт: P15 list-to-prose can convert ГОСТ structure
Stages: Stage 2
Config: N/A

NEVER convert:
- numbered section markers (1.1, Глава N)
- bibliography entries
- TOC items

ONLY convert:
- content bullets with "**Header:** Content" format

BUILD check: protected patterns list before list-to-prose
RUNTIME check: ГОСТ section numbering preserved
```

**AC-10 — Idea-Order Disruptor Gating [MEDIUM]**
```
Конфликт: Op 11 on ambiguous register may break text
Stages: Stage 2
Config: N/A

ASSERT register in ['academic', 'academic-essay', 'journalistic', 'general']

IF register == 'academic':
    Op 11 = paragraph level ONLY
ELSE:
    Op 11 = paragraph + section level

BUILD check: register assertion + scope restriction
RUNTIME check: macro-structure preservation
```

**AC-11 — Standalone Definitions [LOW]**
```
Stages: Stage 3
IF language == 'en': convert "X is defined as Y"
IF language == 'ru': convert "Под X понимается Y"
```

**AC-12 — But:However → Но:Однако [LOW]**
```
Stages: Stage 5 (scorer.py)
IF language == 'ru':
    but_however_ratio = None
    REPORT no_odnako_ratio (Но:Однако) ≥ 2:1
IF language == 'en':
    REPORT but_however_ratio ≥ 2:1
```

**AC-13 — Citation Density vs GOST Minimums [LOW]**
```
Stages: Stage 5, Phase 0A
Both metrics enforced independently.
```

**AC-14 — Russian P7 Words [LOW]**
```
Stages: Stage 3, Stage 1
p7_russian config + _apply_russian_patterns() + {{LANGUAGE}} in prompts
```

**AC-15 — Perplexity for Russian [LOW]**
```
Stages: Stage 1, Stage 5
IF language == 'ru': _skip_perplexity = True
Score report: "N/A (Russian text)"
```

---

### reference/stage_ac_matrix.md — Содержимое

Матрица формат:

```
| AC Rule | Priority | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Stage 5 | Phase 0A | Phase 0B | config.yaml | prompts/ |
```

Для каждой ячейки: что ИМЕННО проверять (конкретная функция или параметр).

Полная матрица:

| AC | Priority | Stage 1 (analyzer) | Stage 2 (structural) | Stage 3 (lexical) | Stage 4 (discourse) | Stage 5 (scorer) | Phase 0 | config | prompts |
|---|---|---|---|---|---|---|---|---|---|
| AC-1 | HIGH | — | `reduce_em_dashes_ru()` + language gate | — | — | em_dash_count metric | — | `structural.em_dash_ru_max_per_paragraph` | Stage 2 prompt: {{LANGUAGE}} |
| AC-2 | HIGH | — | — | citation_format gate | citation_format gate | — | GOST [N] in generated text | — | Stage 3+4: {{LANGUAGE}}+{{REGISTER}} |
| AC-3 | HIGH | — | P26 protected_sections list | — | — | section_order_validation | GOST section generation order | — | Stage 2 prompt: section protection |
| AC-4 | HIGH | — | — | — | passive_threshold gate | passive_voice_pct metric | — | `discourse.academic_ru_passive_threshold` | Stage 4 prompt: {{LANGUAGE}}+{{REGISTER}} |
| AC-5 | HIGH | — | — | — | Op 8 skip gate | — | — | — | Stage 4 prompt: skip metaphors |
| AC-6 | HIGH | `_apply_russian_patterns()` | `_apply_russian_patterns()` | `_apply_russian_patterns()` | `_apply_russian_patterns()` | Russian pattern rescan | — | `p7_russian` + `p29_russian` blocks | ALL prompts: {{LANGUAGE}} |
| AC-7 | MED-HIGH | — | — | — | F5/F6 skip gate | — | — | — | Stage 4 prompt: skip F5/F6 |
| AC-8 | MEDIUM | — | `normalize_quotes_ru()` | `normalize_quotes_ru()` | — | — | — | — | — |
| AC-9 | MED-HIGH | — | P15 protected list | — | — | — | — | — | Stage 2 prompt |
| AC-10 | MEDIUM | — | Op 11 register assertion | — | — | — | — | — | Stage 2 prompt |
| AC-11 | LOW | — | — | definition form gate | — | — | — | — | Stage 3 prompt: {{LANGUAGE}} |
| AC-12 | LOW | — | — | — | — | no_odnako_ratio metric | — | `scoring.ru_no_odnako_ratio_target` | — |
| AC-13 | LOW | — | — | — | — | citation_density + source_minimums (independent) | source_minimums enforcement | — | — |
| AC-14 | LOW | pattern scan includes Russian P7 | — | Russian P7 banlist application | — | Russian P7 rescan | — | `p7_russian` block | Stage 3 prompt: {{LANGUAGE}} |
| AC-15 | LOW | skip_perplexity for RU | — | — | — | "N/A (Russian text)" | — | `scoring.skip_perplexity_for_russian` | — |

---

### reference/russian_adaptation_rules.md — Содержимое

Verbatim из CLAUDE.md секции "Russian Language Adaptation" + "Russian F-Rules Differences":

1. **Russian P7 Banlist** — три списка:
   - Absolute ban (14 фраз): следует отметить, является ключевым, играет важную роль, необходимо подчеркнуть, представляется актуальным, в условиях современности, на сегодняшний день, в наше время, как известно, очевидно что, вышесказанное свидетельствует, немаловажно также, актуальность темы заключается в том, данная проблема является актуальной
   - Importance-framing ban (5 фраз): играет важную роль в, является ключевым для, имеет принципиальное значение, занимает особое место в, заслуживает особого внимания
   - Announcement ban (6 фраз): следует отметить что, необходимо отметить что, важно подчеркнуть что, стоит отметить что, обратим внимание на то, отметим что

2. **Russian P29 Connector Rules** — полная таблица:
   - Absolute ban (0 per document): во-первых, во-вторых, в-третьих, помимо этого
   - Near-ban (≤1 per document): кроме того
   - Rate-limited (≤1 per 500 words): более того, помимо прочего
   - Permitted: также, однако, но, при этом, между тем, тем не менее, вместе с тем
   - Encouraged: также, но
   - Target Но:Однако ratio: ≥ 2:1

3. **Russian P10** — triplet ban applies identically (any three-item parallel = hard failure)

4. **Russian P32** — modal hedging ban on result sentences applies identically. Русские модальные: может, мог бы, вероятно, по-видимому, по всей видимости — все banned from sentences with numerical data.

5. **Russian F-Rules Differences:**
   - F2 (em dashes): Conservative. Preserve copular. AC-1 gates.
   - F3 (semicolons): Academic Russian may use in complex lists — no wholesale removal.
   - F5 (apostrophes): Inapplicable to Russian. Skip entirely.
   - F6 (grammar errors): Russian academic — skip entirely. Russian journalistic — comma variation only (1-2).
   - F7 (filler words): Russian equivalents: "в общем-то", "собственно говоря" — journalistic/casual only.

6. **Russian spaCy Model:** Primary: `ru_core_news_sm`. Fallback: regex tokenization.

7. **Perplexity:** Skipped for Russian (GPT-2 English only). Stage 5 → "N/A".

---

### reference/violation_patterns.md — Содержимое

Конкретные regex-паттерны и code-паттерны для детекции нарушений:

**AC-1 violations (Em Dash):**
```python
# RUNTIME: detect grammatically required Russian em dashes
import re

# Copular em dash (Сущ. — Сущ.)
COPULAR_DASH = re.compile(r'[А-ЯЁа-яё]+\s+—\s+[а-яё]')

# Definition em dash (X — это Y)
DEFINITION_DASH = re.compile(r'\b\w+\s+—\s+это\s')

# AI-overuse: >3 em dashes per paragraph
def check_ac1(text: str, language: str) -> dict:
    if language != 'ru':
        # English: any em dash = violation
        count = text.count('—')
        return {'status': 'PASS' if count == 0 else 'FAIL', 'count': count}

    paragraphs = text.split('\n\n')
    violations = []
    for i, para in enumerate(paragraphs):
        dashes = para.count('—')
        required = len(COPULAR_DASH.findall(para)) + len(DEFINITION_DASH.findall(para))
        overuse = dashes - required
        if overuse > 3:
            violations.append(f'Para {i+1}: {dashes} dashes ({required} required, {overuse} excess)')
    return {'status': 'WARN' if violations else 'PASS', 'violations': violations}
```

**AC-2 violations (Citation Format):**
```python
# RUNTIME: detect author-year in RU+academic
AUTHOR_YEAR_RU = re.compile(r'[А-ЯЁ][а-яё]+\s*\(\d{4}\)')
AUTHOR_YEAR_EN = re.compile(r'[A-Z][a-z]+\s*\(\d{4}\)')
GOST_CITATION = re.compile(r'\[\d+\]')

def check_ac2(text: str, language: str, register: str) -> dict:
    if language == 'ru' and register == 'academic':
        ay_matches = AUTHOR_YEAR_RU.findall(text) + AUTHOR_YEAR_EN.findall(text)
        gost_matches = GOST_CITATION.findall(text)
        # Author-year format is ALWAYS wrong in RU+academic, even if GOST also present
        # Correct: "Петров [4]". Wrong: "Петров (2019)" or "Петров (2019) [4]"
        if ay_matches:
            return {'status': 'FAIL', 'author_year_found': ay_matches, 'gost_citations': len(gost_matches)}
        return {'status': 'PASS', 'gost_citations': len(gost_matches)}
    return {'status': 'N/A'}
```

**AC-6 violations (Russian P7):**
```python
# RUNTIME: detect Russian AI patterns
P7_RUSSIAN_ABSOLUTE = [
    'следует отметить', 'является ключевым', 'играет важную роль',
    'необходимо подчеркнуть', 'представляется актуальным',
    'в условиях современности', 'на сегодняшний день', 'в наше время',
    'как известно', 'очевидно что', 'вышесказанное свидетельствует',
    'немаловажно также', 'актуальность темы заключается в том',
    'данная проблема является актуальной',
]
P7_RUSSIAN_IMPORTANCE = [
    'играет важную роль в', 'является ключевым для',
    'имеет принципиальное значение', 'занимает особое место в',
    'заслуживает особого внимания',
]
P7_RUSSIAN_ANNOUNCEMENT = [
    'следует отметить что', 'необходимо отметить что',
    'важно подчеркнуть что', 'стоит отметить что',
    'обратим внимание на то', 'отметим что',
]

P29_RUSSIAN_BANNED = ['во-первых', 'во-вторых', 'в-третьих', 'помимо этого']

def check_ac6_ac14(text: str, language: str) -> dict:
    if language != 'ru':
        return {'status': 'N/A'}

    text_lower = text.lower()
    violations = []

    for phrase in P7_RUSSIAN_ABSOLUTE + P7_RUSSIAN_IMPORTANCE + P7_RUSSIAN_ANNOUNCEMENT:
        if phrase in text_lower:
            violations.append(f'P7: "{phrase}"')

    for connector in P29_RUSSIAN_BANNED:
        if connector in text_lower:
            violations.append(f'P29: "{connector}"')

    return {
        'status': 'FAIL' if violations else 'PASS',
        'violations': violations
    }
```

**AC-3 violations (GOST Macro-Structure):**
```python
# RUNTIME: verify GOST section order is preserved
GOST_SECTION_ORDER_RU = [
    'введение', 'глава 1', 'глава 2', 'глава 3', 'глава 4',
    'заключение', 'список литературы', 'список использованных источников',
    'приложение',
]
GOST_SECTION_ORDER_EN = [
    'introduction', 'chapter 1', 'chapter 2', 'chapter 3', 'chapter 4',
    'conclusion', 'references', 'bibliography', 'appendix',
]

def check_ac3(text: str, language: str, register: str) -> dict:
    if register != 'academic':
        return {'status': 'N/A'}

    order = GOST_SECTION_ORDER_RU if language == 'ru' else GOST_SECTION_ORDER_EN
    text_lower = text.lower()

    found_sections = []
    for section in order:
        pos = text_lower.find(section)
        if pos != -1:
            found_sections.append((section, pos))

    # Check that found sections are in correct order
    for i in range(len(found_sections) - 1):
        if found_sections[i][1] > found_sections[i+1][1]:
            return {
                'status': 'FAIL',
                'issue': f'"{found_sections[i][0]}" appears AFTER "{found_sections[i+1][0]}"',
                'found_sections': [s[0] for s in found_sections]
            }
    return {'status': 'PASS', 'found_sections': [s[0] for s in found_sections]}
```

**AC-4 violations (Passive Voice Threshold):**
```python
# RUNTIME: check passive voice percentage in Russian academic text
# Uses spaCy ru_core_news_sm or regex fallback
import re

# Regex fallback for Russian passive detection
PASSIVE_RU_PATTERNS = [
    re.compile(r'\b\w+(?:ется|ются|ится|ятся|ался|алась|алось|ались)\b'),  # reflexive passive
    re.compile(r'\b(?:был|была|было|были)\s+\w+(?:ен|ан|ят|ит|от|ут)\b'),  # был + short participle
]

def check_ac4(text: str, language: str, register: str) -> dict:
    if language != 'ru' or register != 'academic':
        return {'status': 'N/A'}

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    if not sentences:
        return {'status': 'N/A'}

    passive_count = 0
    for sent in sentences:
        for pattern in PASSIVE_RU_PATTERNS:
            if pattern.search(sent):
                passive_count += 1
                break

    pct = passive_count / len(sentences)
    threshold = 0.70  # from config.yaml: discourse.academic_ru_passive_threshold

    if pct < 0.40:
        return {'status': 'WARN', 'passive_pct': round(pct, 2),
                'issue': f'Passive voice {pct:.0%} is below 40% — pipeline may have over-converted to active'}
    return {'status': 'PASS', 'passive_pct': round(pct, 2), 'threshold': threshold}
```

**AC-5 violations (Figurative Language in RU Academic):**
```python
# RUNTIME: detect metaphors/analogies in Russian academic text
METAPHOR_MARKERS_RU = [
    'подобно', 'словно', 'как будто', 'своего рода',
    'является своеобразным', 'напоминает', 'сродни',
    'можно сравнить с', 'аналогично тому как',
]

def check_ac5(text: str, language: str, register: str, domain: str = '') -> dict:
    # AC-5: Skip metaphors for RU+academic AND math domain (any register)
    should_skip = (language == 'ru' and register == 'academic') or domain == 'math'
    if should_skip:
        text_lower = text.lower()
        found = [m for m in METAPHOR_MARKERS_RU if m in text_lower]
        return {
            'status': 'WARN' if found else 'PASS',
            'metaphor_markers': found,
            'reason': 'RU+academic' if language == 'ru' else f'domain={domain}'
        }
    return {'status': 'N/A'}
```

**BUILD violation patterns (code checks):**
```python
# Patterns to search in Python code for AC compliance

# AC-1: Missing language gate before em dash reduction
MISSING_GATE_AC1 = "reduce_em_dashes(" without preceding "if.*language"

# AC-4: Hardcoded passive threshold (should read from config)
HARDCODED_THRESHOLD = re.compile(r'passive.*threshold\s*=\s*0\.\d+')  # should be config.get()

# AC-6: Missing {{LANGUAGE}} in prompt template
MISSING_LANGUAGE_VAR = "prompt template without {{LANGUAGE}}"

# AC-7: F5/F6 without register check
MISSING_REGISTER_GATE = "inject_apostrophe_drops(" without preceding "if.*register"
```

Включить по 2-3 примера НАРУШЕНИЙ и ПРАВИЛЬНОГО кода для каждого HIGH-приоритетного AC.

---

## Пояснения для тебя (Артём)

### Что такое ac-gate и зачем он нужен

Представь pipeline как конвейер: текст проходит 5 стадий обработки. Проблема в том, что pipeline проектировался для **английского** текста. Когда через него проходит **русский академический** текст, pipeline ломает его:

- **AC-1**: Удаляет ВСЕ тире, включая грамматически обязательные ("Москва — столица России" → "Москва, столица России" — грамматическая ошибка)
- **AC-2**: Конвертирует ГОСТ-ссылки [4] в author-year (Петров, 2019) — нарушение ГОСТ
- **AC-4**: Переписывает 60% пассивных конструкций в активные — для русского академического текста это нарушение стиля (норма 50%+)
- **AC-5**: Вставляет метафоры в ВКР — в русских дипломных работах метафоры НЕ допускаются
- **AC-7**: Вставляет ошибки грамматики в академический текст — дипломная работа с намеренными ошибками = провал на защите

`ac-gate` — это **gate-keeper** (контролёр на воротах), который стоит перед каждым Stage и проверяет: "Ты точно учёл язык, регистр и домен? Ты не собираешься сломать русский текст английскими правилами?"

### Два режима работы

1. **BUILD** — проверяет **код и промпты** при их написании. Это как code review, только автоматический и специализированный на AC-правилах. Когда ты пишешь Stage 2, ac-gate проверяет: есть ли language gate перед reduce_em_dashes()? Есть ли protected_sections для ГОСТ?

2. **RUNTIME** — проверяет **выходной текст** после прогона через pipeline. Это как unit test, только на выходном тексте: "В русском академическом тексте не должно быть author-year ссылок. Не должно быть метафор. Не должно быть F5/F6 ошибок."

### Структура reference-файлов

- **ac_rules_full.md** — полное описание всех 15 правил с decision trees (если язык=X и регистр=Y, то делай Z). Это "закон", по которому ac-gate судит.
- **stage_ac_matrix.md** — матрица "какое правило где проверять". Stage 2 → AC-1, AC-3, AC-6, AC-8, AC-9, AC-10. Stage 4 → AC-4, AC-5, AC-6, AC-7. Это "маршрутная карта" для проверки.
- **russian_adaptation_rules.md** — все русские списки банов (P7, P29), F-rules различия, spaCy модель. Это "словарь" русских паттернов.
- **violation_patterns.md** — конкретные regex-паттерны и код для детекции нарушений. Это "инструменты" проверки.

### Почему 15 правил, а не 5 или 50

15 — это точное количество конфликтов между megaprompt и pipeline, выявленных при анализе. Каждое правило — это конкретный баг, который проявляется при обработке русского текста английским pipeline. Ни одно нельзя убрать (текст сломается), ни одного лишнего нет.

### Приоритеты

- **HIGH** (6 правил: AC-1–AC-6): Если нарушить — текст гарантированно сломан (грамматические ошибки, нарушение ГОСТ, метафоры в ВКР)
- **MEDIUM-HIGH** (2 правила: AC-7, AC-9): Если нарушить — текст ухудшается заметно, но не критично
- **MEDIUM** (2 правила: AC-8, AC-10): Косметическое — кавычки «» вместо ", gating ambiguous register
- **LOW** (5 правил: AC-11–AC-15): Метрики в score report — не ломают текст, но дают неверные оценки

### Связь с другими скиллами

- `prompt-crafter` пишет промпты → `ac-gate` проверяет, что они содержат {{LANGUAGE}} и не противоречат AC
- `agent-builder` пишет код Stage → `ac-gate` проверяет, что код содержит language/register gates
- `humanizer` трансформирует текст → `ac-gate` проверяет, что выходной текст не нарушает AC
- `academic-writer` отвечает за качество содержания → `ac-gate` отвечает за language/register корректность

ac-gate — это единственный скилл в системе, который отвечает за **language×register×domain совместимость**. Без него pipeline будет работать корректно только для английского journalistic текста.
