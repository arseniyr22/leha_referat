---
description: "Gate-валидатор Anti-Conflict Rules (AC-1—AC-15): проверяет код, промпты, конфиги и выходной текст на соблюдение языковых/регистровых/доменных адаптаций. BUILD+RUNTIME. Предотвращает поломку русского академического текста англоцентричным pipeline."
---

# ac-gate

## Секция 1: Имя и триггер

**Имя:** ac-gate

**Триггер:** При написании/модификации любого Stage (1–5), при написании промптов, при проверке pipeline output, при добавлении нового AC-правила в CLAUDE.md

**Команда:** `/ac-gate [mode] [target]`

**Режимы:**
- `build` — проверить код/промпт/конфиг на наличие AC-compliant gates
- `runtime` — проверить текст на выходе pipeline на AC-нарушения
- `audit` — полный аудит всех компонентов системы

**Примеры вызова:**
- `/ac-gate build pipeline/structural_rewriter.py` — проверить код Stage 2
- `/ac-gate build prompts/voice_injection.md` — проверить промпт Stage 4
- `/ac-gate build config.yaml` — проверить конфиг на наличие всех AC-параметров
- `/ac-gate runtime` — проверить текст на выходе pipeline (запросит текст + params)
- `/ac-gate audit` — полный аудит всех pipeline/*.py + prompts/*.md + config.yaml
- `/ac-gate` без аргументов — интерактивный режим

---

## Секция 2: Цель

Гарантировать, что ни один компонент pipeline не нарушает Anti-Conflict Rules (AC-1—AC-15). Каждое AC-правило — это языковой, регистровый или доменный gate, который предотвращает деструктивное применение англоцентричных трансформаций к русскому/академическому тексту.

**Что входит в зону ответственности:**
- Проверка Python-кода pipeline stages на наличие language/register/domain gates
- Проверка LLM-промптов на включение `{{LANGUAGE}}`, `{{REGISTER}}`, `{{DOMAIN}}` и AC-совместимых инструкций
- Проверка `config.yaml` на наличие всех AC-обязательных параметров
- Проверка выходного текста (RUNTIME) на AC-нарушения
- Генерация JSON compliance report с `status: PASS|FAIL|WARN|N/A`

**Что НЕ входит в зону ответственности:**
- Проверка паттернов P1–P53 — зона humanizer и pattern-auditor
- Качество содержания (синтез, факты, глубина) — зона academic-writer
- Визуализации БЛОК 16 — зона academic-visualizer
- ГОСТ-форматирование .docx — зона formatter
- Антиплагиатный анализ — зона scorer

---

## Секция 3: Пошаговый процесс

### BUILD-режим: проверка кода (target = *.py)

**Шаг 3.1: Определить target_type и applicable AC rules**

Загрузить `reference/stage_ac_matrix.md`. Определить, какие AC-правила применяются к данному Stage-файлу:
```
analyzer.py      → AC-6, AC-14, AC-15
structural_rewriter.py → AC-1, AC-3, AC-6, AC-8, AC-9, AC-10
lexical_enricher.py    → AC-2, AC-6, AC-8, AC-11, AC-14
discourse_shaper.py    → AC-4, AC-5, AC-6, AC-7
scorer.py        → AC-1, AC-3, AC-6, AC-12, AC-13, AC-14, AC-15
generator.py     → AC-3, AC-5, AC-6
formatter.py     → AC-8
```

**Шаг 3.2: Проверить наличие language/register gates**

Для каждого применимого AC-правила:

```
AC-1 (HIGH): Есть ли if language == 'ru' перед reduce_em_dashes()?
             Вызывается ли reduce_em_dashes_ru() для русского?
             Для English: target = 0 em dashes?

AC-2 (HIGH): Есть ли citation_format параметр?
             При language='ru' AND register='academic': GOST [N], НЕ author-year?
             При других комбинациях: author-year применяется?

AC-3 (HIGH): P26 idea-order disruptor НЕ переставляет GOST section markers?
             Список protected: title_page, annotation, toc, introduction,
             chapter_1...N (by number), conclusion, references?
             P26 ограничен paragraph-level для academic register?

AC-4 (HIGH): Есть ли language+register gate перед passive voice flagging?
             language='ru' AND register='academic': threshold = 0.70 из config?
             English/non-academic: threshold = 0.20?

AC-5 (HIGH): Op 8 (metaphor injection) SKIP при language='ru' AND register='academic'?
             Op 8 SKIP для domain='math'?
             Op 8 APPLY для Russian journalistic/essay?

AC-6 (HIGH): language='ru' → _apply_russian_patterns(text, config) вызывается?
             p7_russian + p29_russian config blocks используются?

AC-7 (MED-HIGH): register='academic' → F5 AND F6 SKIP entirely?
                 language='ru' → F5 SKIP entirely, F6 = comma only?
                 language='en' AND register='journalistic' → F5 (3-5) + F6 (2-3)?

AC-8 (MEDIUM): language='en' → normalize_quotes() → ASCII "?
               language='ru' → normalize_quotes_ru() → guillemets «»?

AC-9 (MED-HIGH): P15 list-to-prose НЕ конвертирует TOC, bibliography, numbered sections?
                 Только content bullets с "**Header:** Content" форматом?

AC-10 (MEDIUM): Op 11 имеет assert register in ['academic', 'academic-essay', ...]?
                register='academic' → Op 11 = paragraph level ONLY?

AC-11 (LOW): language='en' → converts "X is defined as Y"?
             language='ru' → converts "Под X понимается Y"?

AC-12 (LOW): language='ru' → but_however_ratio = None в score report?
             language='ru' → reports no_odnako_ratio (Но:Однако) ≥ 2:1?

AC-13 (LOW): Per-page citation density (Stage 5) и GOST stream source minimums (Phase 0A)
             enforced INDEPENDENTLY? Оба присутствуют в score report?

AC-14 (LOW): p7_russian config block используется?
             _apply_russian_patterns() вызывается для language='ru'?

AC-15 (LOW): language='ru' → _skip_perplexity=True?
             Score report: "N/A (Russian text)" для perplexity fields?
```

**Шаг 3.3: Сгенерировать BUILD report (код)**

```json
{
  "target": "pipeline/structural_rewriter.py",
  "target_type": "code",
  "applicable_ac_rules": ["AC-1", "AC-3", "AC-6", "AC-8", "AC-9", "AC-10"],
  "results": {
    "AC-1": {"status": "PASS", "evidence": "language gate at line 47, reduce_em_dashes_ru() at line 51"},
    "AC-3": {"status": "FAIL", "issue": "P26 disruptor has no GOST section protection", "fix": "Add protected_sections list before Op 11 at line 82", "priority": "HIGH"},
    "AC-6": {"status": "PASS", "evidence": "_apply_russian_patterns() called at line 63"},
    "AC-8": {"status": "PASS", "evidence": "normalize_quotes_ru() at line 119 with language gate"},
    "AC-9": {"status": "WARN", "issue": "List-to-prose has no TOC detection", "fix": "Add TOC regex before P15 conversion", "priority": "MEDIUM-HIGH"},
    "AC-10": {"status": "PASS", "evidence": "register assertion at line 95"}
  },
  "overall": "FAIL",
  "blocking_issues": 1,
  "warnings": 1
}
```

---

### BUILD-режим: проверка промптов (target = prompts/*.md)

**Шаг 3.4: Проверить prompt compliance**

Для каждого промпта Stage 2–4:

```
✅/❌ Содержит {{LANGUAGE}} variable?
✅/❌ Содержит {{REGISTER}} variable?
✅/❌ Содержит {{DOMAIN}} variable (если domain-зависимый)?

Stage 2 prompts (structural_rewrite.md, connector_rebalancer.md):
  ❌ Нет инструкции переставлять ГОСТ-секции (AC-3)?
  ❌ Нет инструкции убирать ВСЕ em dashes без language gate (AC-1)?

Stage 3 prompts (lexical_enrichment.md, modal_hedging_audit.md):
  ❌ Нет инструкции конвертировать [N] → author-year для RU+academic (AC-2)?

Stage 4 prompts (voice_injection.md, audit.md):
  ❌ Нет инструкции вставлять метафоры для RU+academic (AC-5)?
  ❌ Нет инструкции вставлять F5/F6 для academic register (AC-7)?

Все промпты:
  ❌ Нет инструкции убирать пассивный залог без language gate (AC-4)?
```

---

### BUILD-режим: проверка конфига (target = config.yaml)

**Шаг 3.5: Проверить AC-обязательные параметры**

```yaml
# AC-1 — Em Dash
structural.em_dash_ru_max_per_paragraph: 3          # REQUIRED

# AC-4 — Passive Voice Threshold
discourse.academic_ru_passive_threshold: 0.70        # REQUIRED ✅ exists
discourse.default_passive_threshold: 0.20            # REQUIRED (or inline default)

# AC-6, AC-14 — Russian P7
p7_russian.absolute_ban: [list]                      # REQUIRED ✅ exists
p7_russian.importance_framing_ban: [list]            # REQUIRED ✅ exists
p7_russian.announcement_ban: [list]                  # REQUIRED ✅ exists

# AC-6 — Russian P29
p29_russian.absolute_ban: [list]                     # REQUIRED ✅ exists
p29_russian.near_ban_max_per_doc: {...}               # REQUIRED ✅ exists
p29_russian.rate_limited_per_500w: {...}              # REQUIRED ✅ exists
p29_russian.target_no_odnako_ratio: 2.0              # REQUIRED ✅ exists

# AC-12 — Russian ratio reporting
scoring.ru_no_odnako_ratio_target: 2.0               # REQUIRED
p29_russian.target_no_odnako_ratio: 2.0              # REQUIRED ✅ exists

# AC-15 — Perplexity skip for Russian
local_models.perplexity_model_ru: null               # REQUIRED ✅ exists
scoring.skip_perplexity_for_russian: true            # REQUIRED

# AC-7 — P30 mode for academic
p30_mode.academic: "limited"                         # REQUIRED ✅ exists

# AC (all) — spaCy Russian model
local_models.spacy_model_ru: "ru_core_news_sm"      # REQUIRED ✅ exists
```

---

### RUNTIME-режим: проверка текста на выходе pipeline

**Шаг R.1: Определить params**

```
language → 'ru' | 'en'
register → 'academic' | 'academic-essay' | 'journalistic' | 'general'
domain   → 'it_cs' | 'law' | 'psychology' | 'economics' | 'humanities' | 'media' | 'general'
stage    → '2' | '3' | '4' | '5' (какой Stage выдал текст)
```

Если не указаны — определить из контекста или запросить.

**Шаг R.2: Применить AC-фильтры (см. reference/violation_patterns.md)**

Для language='ru':
- **AC-1**: Подсчитать em dashes. >3/абзац при copular context → WARN (AI overuse). 0 em dashes при наличии копулярных конструкций → FAIL (pipeline удалил обязательные).
- **AC-2**: Если register='academic': regex для author-year паттернов `[А-Я][а-я]+\s*\(\d{4}\)`. Найдены → FAIL.
- **AC-4**: Если register='academic': подсчитать % пассивного залога. <40% → WARN (pipeline перегнул в актив). 40–70% → PASS. >70% → INFO.
- **AC-5**: Если register='academic': поиск маркеров метафор. Найдены → WARN.
- **AC-6/AC-14**: Поиск русских P7 фраз из p7_russian banlist. Найдены → FAIL.
- **AC-7**: Если register='academic': поиск apostrophe drops (F5) и grammar errors (F6). Найдены → FAIL.
- **AC-8**: Поиск ASCII straight quotes `"` в русском тексте. Найдены → WARN.
- **AC-12**: Подсчитать Но vs Однако. Ratio <2:1 → WARN.

Для language='en':
- **AC-1**: em dashes count > 0 → FAIL (target = 0 для English).
- **AC-8**: guillemets «» в English тексте. Найдены → FAIL.
- **AC-12**: But:However ratio <2:1 → WARN.
- **AC-15**: perplexity score = "N/A" → FAIL (English must have perplexity).

Для register='academic' (любой язык):
- **AC-3**: GOST section markers в правильном порядке (Введение → Глава N → Заключение → Список литературы).
- **AC-5**: Нет метафор (RU academic и math domain).
- **AC-7**: Нет F5 и F6.
- **AC-9**: TOC, bibliography, numbered sections не конвертированы в прозу.

**Шаг R.3: Сгенерировать RUNTIME report**

```json
{
  "language": "ru",
  "register": "academic",
  "domain": "economics",
  "stage_output": "4",
  "ac_checks": {
    "AC-1": {"status": "PASS", "em_dashes_total": 12, "grammatically_required": 10, "ai_overuse": 2},
    "AC-2": {"status": "PASS", "gost_citations_found": 34, "author_year_found": 0},
    "AC-4": {"status": "PASS", "passive_voice_pct": 0.58},
    "AC-5": {"status": "PASS", "metaphors_found": 0},
    "AC-6": {"status": "FAIL", "violations": ["следует отметить (line 42)", "является ключевым (line 87)"]},
    "AC-7": {"status": "PASS", "f5_found": 0, "f6_found": 0},
    "AC-8": {"status": "WARN", "straight_quotes": 3, "guillemets": 28},
    "AC-12": {"status": "PASS", "no_count": 14, "odnako_count": 5, "ratio": 2.8},
    "AC-14": {"status": "FAIL", "violations": ["играет важную роль (line 23)"]},
    "AC-15": {"status": "PASS", "perplexity_skipped": true}
  },
  "overall": "FAIL",
  "blocking_issues": ["AC-6: 2 Russian P7 violations", "AC-14: 1 importance-framing violation"],
  "warnings": ["AC-8: 3 straight quotes should be guillemets"]
}
```

---

### AUDIT-режим: полный аудит системы

**Шаг A.1: Последовательная проверка всех компонентов**

```
1. config.yaml         → BUILD config check (Шаг 3.5)
2. analyzer.py         → BUILD code check: AC-6, AC-14, AC-15
3. structural_rewriter.py → BUILD code check: AC-1, AC-3, AC-6, AC-8, AC-9, AC-10
4. lexical_enricher.py → BUILD code check: AC-2, AC-6, AC-8, AC-11, AC-14
5. discourse_shaper.py → BUILD code check: AC-4, AC-5, AC-6, AC-7
6. scorer.py           → BUILD code check: AC-1, AC-3, AC-6, AC-12, AC-13, AC-14, AC-15
7. structural_rewrite.md → BUILD prompt check: AC-1, AC-3, AC-6
8. lexical_enrichment.md → BUILD prompt check: AC-2, AC-6, AC-14
9. voice_injection.md  → BUILD prompt check: AC-4, AC-5, AC-6, AC-7
10. audit.md           → BUILD prompt check: AC-4, AC-5, AC-7
11. Сводный отчёт: таблица компонент × AC rule × статус
```

---

## Секция 4: Reference Files

| Файл | Содержание | Когда использовать |
|------|-----------|-------------------|
| `reference/ac_rules_full.md` | Все 15 AC-правил verbatim + decision tree для каждого | Шаги 3.2, R.2 |
| `reference/stage_ac_matrix.md` | Матрица Stage × AC с конкретными функциями/ключами | Шаг 3.1, A.1 |
| `reference/russian_adaptation_rules.md` | P7/P29/P10/P32/F-rules для русского языка verbatim | Шаг R.2, BUILD проверки |
| `reference/violation_patterns.md` | Python regex + code stubs для детекции нарушений | Шаги 3.2, R.2, R.3 |

---

## Секция 5: Правила

**R1 — БЛОКИРУЮЩИЙ = БЛОКИРУЮЩИЙ.** Если хотя бы одно HIGH-правило нарушено — `overall: FAIL`. Pipeline НЕ ДОЛЖЕН продолжать до исправления.

**R2 — Приоритеты AC:**
```
HIGH (6):        AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
                 Нарушение → FAIL (блокирует pipeline)
MEDIUM-HIGH (2): AC-7, AC-9
                 Нарушение → FAIL (блокирует; допустим override --allow-medium)
MEDIUM (2):      AC-8, AC-10
                 Нарушение → WARN
LOW (5):         AC-11, AC-12, AC-13, AC-14, AC-15
                 Нарушение → WARN
```

**R3 — Language gate обязателен.** Каждый Stage-файл ОБЯЗАН содержать `language` параметр и ветвление по нему. Отсутствие language gate = автоматический FAIL по AC-6.

**R4 — Register gate обязателен.** Stage 2/3/4 ОБЯЗАНЫ содержать `register` параметр. Отсутствие = автоматический FAIL по AC-4/AC-5/AC-7.

**R5 — Config completeness.** Все AC-обязательные параметры (Шаг 3.5) ОБЯЗАНЫ присутствовать в `config.yaml`. Отсутствие = FAIL.

**R6 — Prompt completeness.** Промпты Stage 2–4 ОБЯЗАНЫ содержать `{{LANGUAGE}}` и `{{REGISTER}}`. Отсутствие = FAIL по AC-6.

**R7 — RUNTIME ≠ BUILD.** BUILD проверяет код на НАЛИЧИЕ gates. RUNTIME проверяет текст на РЕЗУЛЬТАТ применения gates. Оба режима обязательны — BUILD ловит архитектурные ошибки, RUNTIME ловит runtime bugs.

**R8 — False positive mitigation (AC-1).** Regex детекции обязательных тире в русском тексте различает:
```
[Сущ.] — [Сущ./Прил.]   = обязательное (копула) → сохранить
"Москва — столица"        = обязательное → сохранить
— [конструкция] mid-sent  = стилистическое → кандидат на удаление
≥2 — в одном предложении  = AI overuse → удалить лишние
```

**R9 — Incremental updates.** При добавлении AC-16+ в CLAUDE.md:
1. Добавить правило в `reference/ac_rules_full.md`
2. Добавить строку в `reference/stage_ac_matrix.md`
3. Добавить паттерны нарушений в `reference/violation_patterns.md`
4. Обновить приоритет в R2

**R10 — Synergy map compliance.** Проверки ac-gate ДОЛЖНЫ быть синхронизированы с Megaprompt–Pipeline Synergy Map из CLAUDE.md. Каждый row synergy map, упоминающий AC-правило, должен быть покрыт соответствующей проверкой.

---

## Секция 6: Self-Improvement Log

После каждого использования записывать:

```
[ДАТА] [MODE] [TARGET] [AC_RULES_CHECKED] [VIOLATIONS_FOUND] [FALSE_POSITIVES]
Блокирующие нарушения: [список]
Предупреждения: [список]
```

Каждые 10 использований: проверить, не добавлены ли новые AC-правила в CLAUDE.md.

При изменении config.yaml: проверить, не устарели ли ссылки на config-ключи в Шаге 3.5.

### Лог использований

*(пока пуст — заполняется по мере использования)*
