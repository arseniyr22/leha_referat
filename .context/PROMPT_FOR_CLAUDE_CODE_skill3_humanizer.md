# Промпт для Claude Code — Скилл #3: humanizer (анализ + интеграция)

Скопируй всё содержимое ниже (между линиями ===) в Claude Code:

===

## Задача: Скачать, проанализировать и адаптировать скилл humanizer

Скилл humanizer — это интерактивный инструмент для обнаружения и удаления AI-паттернов из текста. Источник: https://github.com/blader/humanizer

### ВАЖНО: Это НЕ production-dependency, а отладочный инструмент (решение D10)

humanizer используется для:
- Ручного тестирования текста на AI-паттерны перед запуском pipeline
- Сравнения качества pipeline output vs. humanizer output
- Генерации "gold standard" примеров для tests/expected/
- Быстрой проверки отдельных паттернов при разработке

humanizer НЕ используется:
- Как часть runtime pipeline (pipeline использует свои agents/prompts/)
- Как замена наших Stage 2-4 (наша система покрывает 53+8 паттернов vs 24 у humanizer)

---

## Шаг 1 — Клонировать репозиторий

```bash
git clone https://github.com/blader/humanizer ~/.claude/skills/humanizer
```

Размещение: GLOBAL (`~/.claude/skills/`) — это единственный generic-скилл, полезный в любом проекте (решение D20).

После клонирования покажи:
```bash
ls -la ~/.claude/skills/humanizer/
cat ~/.claude/skills/humanizer/SKILL.md | head -50
```

---

## Шаг 2 — Проанализировать содержимое

Прочитай `~/.claude/skills/humanizer/SKILL.md` ПОЛНОСТЬЮ.

Составь отчёт по следующим пунктам:

### 2.1 — Покрытие паттернов

Оригинальный humanizer покрывает ~24 паттерна в 4 категориях.
Наша система (CLAUDE.md) покрывает 53 паттерна + 8 F-rules + 15 AC-правил.

Создай таблицу маппинга:

```
| Humanizer Pattern | Наш паттерн | Совпадение | Что у нас добавлено |
|---|---|---|---|
| Significance inflation | P1 | Полное | + конкретные watch words расширены |
| ... | ... | ... | ... |
```

### 2.2 — Что humanizer покрывает, а мы нет

Если humanizer содержит какие-то техники/инструкции, которых НЕТ в нашей системе — перечисли их. Это может быть полезно для улучшения наших промптов.

### 2.3 — Что мы покрываем, а humanizer нет

Составь список наших паттернов, которые humanizer НЕ покрывает:
- P31-P43 (corpus-validated, HSE diploma works)
- P44-P53 (GPTZero scaffold patterns)
- F1-F8 (formatting fingerprint rules)
- AC-1 through AC-15 (anti-conflict rules)
- Russian language adaptation (P7_russian, P29_russian)
- Domain-specific norms (P41 — math/CS/economics/management/social science/linguistics)
- Citation density calibration (P42)

### 2.4 — Two-pass methodology comparison

Humanizer использует two-pass approach:
- Pass A: Pattern detection + rewrite
- Pass B: "What still makes this obviously AI?" audit

Наша система тоже использует two-pass (Stage 4 в CLAUDE.md), но с расширенным 11-point checklist.

Сравни: что в humanizer's Pass B есть, а в нашем audit нет? И наоборот.

---

## Шаг 3 — Создать адаптацию для нашего проекта

Создай файл `.claude/skills/humanizer/ADDON.md` — дополнение к оригинальному SKILL.md, специфичное для нашего проекта.

### Содержание ADDON.md:

```markdown
# Humanizer — Дополнение для AI Anti-Anti Plag

Это дополнение к оригинальному humanizer skill. Читается ПОСЛЕ основного SKILL.md.

---

## Расширенный набор паттернов

Оригинальный humanizer покрывает 24 паттерна.
Наш проект расширяет покрытие до 53 + 8 + 15:

### Паттерны НЕ покрытые оригиналом (проверяй дополнительно):

**P31 — Information-First Posture Violation**
Описание: AI анонсирует важность перед содержанием. "Resource optimization is pivotal in modern logistics."
Fix: Удалить предложение с importance claim. Начать с содержания.
Тест: Найти конструкции "[X] is [importance-word] for [Y]" где importance-word ∈ {crucial, pivotal, key, central, essential, vital, fundamental}.

**P32 — Modal Hedging on Empirical Facts**
Описание: AI хеджирует измеренные результаты. "The model may achieve 95% accuracy."
Fix: Если предложение содержит число/статистику + модальный глагол → удалить модальный.

**P33 — But:However Ratio**
Описание: Человеческий текст: But:However ≥ 2:1. AI текст: However:But ≥ 3:1.
Тест: Посчитать But vs However. Если However > But → проблема.

**P34-P43** (см. CLAUDE.md секцию "Category 7 — Extended Patterns")
Кратко: rhetorical questions (P34), parenthetical definitions (P35), results without praise (P36), section asymmetry (P37), attribution-based hedging (P38), counter-argument integration (P39), connector scarcity (P40), domain norms (P41), citation density (P42), "Also" frequency (P43).

**P44-P53 — GPTZero Scaffold Patterns** (см. CLAUDE.md секцию "Category 8")
Кратко: superlative opener (P44), dramatic reveal (P45), meta-media (P46), binary future (P47), neither wrap-up (P48), elegant reversal (P49), same-X-that-also (P50), whether-or-just (P51), mechanism run-on (P52), participial simultaneity (P53).

**F1-F8 — Formatting Fingerprint Rules** (см. CLAUDE.md секцию "Formatting Fingerprint Rules")
Кратко: no Oxford comma (F1), 0 em dashes (F2), 0 semicolons journalistic (F3), 0 body colons journalistic (F4), parenthesis minimization (F4b), controlled apostrophe drops (F5), controlled grammar errors (F6), filler words (F7), no invented hyphenated compounds (F8).

---

## Русская адаптация

При работе с русским текстом дополнительно проверяй:

### Russian P7 Banlist
Абсолютный бан: следует отметить, является ключевым, играет важную роль, необходимо подчеркнуть, представляется актуальным, в условиях современности, на сегодняшний день, в наше время, как известно, очевидно что, вышесказанное свидетельствует, немаловажно также, актуальность темы заключается в том, данная проблема является актуальной

### Russian P29 Connectors
Абсолютный бан (0 per document): во-первых, во-вторых, в-третьих, помимо этого
Near-ban (≤1): кроме того
Permitted: также, однако, но, при этом, между тем, тем не менее, вместе с тем
Target: Но:Однако ≥ 2:1

### AC-правила для русского
- AC-1: Em dash — сохранить грамматически обязательные ("Москва — столица России")
- AC-2: Цитаты — GOST [N], не author-year
- AC-4: Passive voice — порог 70% (не 20%)
- AC-5: Пропустить метафоры в academic
- AC-8: Guillemets «» вместо ""

---

## Расширенный Pass B Audit Checklist

При запуске humanizer на тексте, добавь к оригинальному audit ЕЩЁ эти проверки:

1. Есть ли триплеты (3 элемента в серии)? → разбить (P10 zero tolerance)
2. But:However ratio ≥ 2:1? → скорректировать (P33)
3. Есть ли модальные глаголы на предложениях с числами? → удалить (P32)
4. Параграфы заканчиваются на абстрактное обобщение? → заменить на конкретный факт (P24)
5. Есть ли "The same X that also Y" конструкции? → разбить (P50)
6. Есть ли "whether X or just Y" в концовках? → стейтнуть позицию (P51)
7. Есть ли em dashes? → заменить ВСЕ (F2: 0 em dashes)
8. Есть ли semicolons в journalistic тексте? → заменить на точки (F3)
9. Oxford comma присутствует? → удалить (F1)
10. Секции примерно одинаковой длины? → асимметрия обязательна (P37)

---

## Синергия с другими скиллами

### С agent-builder:
Перед созданием worker'а для конкретного паттерна — запусти humanizer на тестовом тексте и проверь, ловит ли humanizer этот паттерн. Если да — используй humanizer output как expected/ для теста.

### С prompt-crafter:
После генерации промпта — вставь тестовый AI-текст, прогони через humanizer. Если humanizer находит паттерны, которые промпт должен был устранить — промпт недостаточно строг, нужно усилить.

### Workflow тестирования:
1. Взять AI-сгенерированный текст (500 слов)
2. Прогнать через humanizer → получить humanized_v1
3. Прогнать тот же текст через наш pipeline (Stages 2-4) → получить pipeline_v1
4. Сравнить humanized_v1 vs pipeline_v1:
   - Какие паттерны humanizer поймал, а pipeline нет?
   - Какие pipeline поймал, а humanizer нет?
5. Записать результат → помогает улучшить и pipeline, и промпты
```

---

## Шаг 4 — Создать reference-файл связей

Создай файл `.claude/skills/humanizer/PATTERN_MAP.md` — маппинг humanizer patterns → наши patterns:

```markdown
# Pattern Mapping: Humanizer → AI Anti-Anti Plag

| # | Humanizer Category | Humanizer Pattern | Our Pattern(s) | Our Coverage |
|---|---|---|---|---|
| 1 | Content | Significance inflation | P1 | Full + extended watch words |
| 2 | Content | Notability emphasis | P2 | Full |
| 3 | Content | Superficial -ing endings | P3 | Full + stacking ban |
| 4 | Content | Promotional language | P4 | Full |
| 5 | Content | Vague attributions | P5 + P38 | Extended: attributive passive form |
| 6 | Content | Formulaic challenge/prospect | P6 | Full |
| 7 | Language | AI vocabulary | P7 | Extended: 4 sublists + domain exemptions |
| 8 | Language | Copula avoidance | P8 | Full |
| 9 | Language | Negative parallelisms | P9 | Extended: announcement openers banlist |
| 10 | Language | Rule of three | P10 | Extended: verb + adverbial tricolons |
| 11 | Language | Elegant variation | P11 | Full |
| 12 | Language | False ranges | P12 | Full |
| 13 | Style | Em dash overuse | P13 + F2 | Stricter: 0 em dashes (F2) |
| 14 | Style | Excessive boldface | P14 | Full |
| 15 | Style | Inline-header lists | P15 | Full |
| 16 | Style | Title case headings | P16 | Full |
| 17 | Style | Decorative emojis | P17 | Full |
| 18 | Style | Curly quotes | P18 | Full |
| 19 | Communication | Chatbot artifacts | P19 | Full |
| 20 | Communication | Cutoff disclaimers | P20 | Full |
| 21 | Communication | Sycophantic tone | P21 | Full |
| 22 | Filler | Filler phrases | P22 | Full |
| 23 | Filler | Excessive hedging | P23 | Full |
| 24 | Filler | Generic conclusions | P24 | Extended: para-ending generalization ban |

## Patterns ONLY in our system (not in humanizer):

| Our Pattern | Category | Description |
|---|---|---|
| P25 | Structural | Paragraph-level uniformity |
| P26 | Structural | Default structural ordering |
| P27 | Structural | Sentence-starter monotony |
| P28 | Structural | Formal register inflation (substitution table) |
| P29 | Structural | Connector monotony (full ban system) |
| P30 | Structural | Imperfection absence |
| P31-P43 | Corpus-validated | HSE diploma analysis patterns |
| P44-P53 | GPTZero scaffold | Live-tested scaffold patterns |
| F1-F8 | Formatting | Formatting fingerprint rules |
| AC-1 to AC-15 | Anti-conflict | Russian/academic conflict resolution |
```

---

## Шаг 5 — Добавить YAML front matter (если отсутствует)

Проверь `~/.claude/skills/humanizer/SKILL.md`. Если в начале НЕТ YAML front matter — добавь:

```yaml
---
description: "Интерактивный two-pass инструмент для обнаружения и удаления AI-паттернов из текста. 24 базовых паттерна + расширения в ADDON.md"
---
```

НЕ добавляй `allowed_tools` — humanizer работает интерактивно в основном контексте, ему нужны все инструменты.

НЕ модифицируй оригинальный SKILL.md кроме добавления front matter. Все наши расширения — в ADDON.md.

---

## Шаг 6 — Verification

После всех шагов проверь:

```bash
# 1. Скилл клонирован
ls ~/.claude/skills/humanizer/SKILL.md

# 2. ADDON.md создан
ls ~/.claude/skills/humanizer/ADDON.md

# 3. PATTERN_MAP.md создан
ls ~/.claude/skills/humanizer/PATTERN_MAP.md

# 4. Front matter добавлен (если не было)
head -5 ~/.claude/skills/humanizer/SKILL.md

# 5. Оригинальный SKILL.md не повреждён (должен содержать two-pass methodology)
grep -c "Pass" ~/.claude/skills/humanizer/SKILL.md

# 6. ADDON.md содержит русские паттерны
grep "следует отметить" ~/.claude/skills/humanizer/ADDON.md

# 7. PATTERN_MAP.md содержит все 24 маппинга + наши уникальные
grep -c "|" ~/.claude/skills/humanizer/PATTERN_MAP.md
```

Покажи результаты всех 7 проверок.

---

## Шаг 7 — Отчёт по анализу

После завершения покажи мне краткий отчёт:

```
## Humanizer Analysis Report

### Покрытие:
- Humanizer паттернов: N
- Наших паттернов покрытых humanizer: N/53
- Наших паттернов НЕ покрытых: N

### Уникальные находки humanizer:
- [перечислить если есть техники/формулировки которых нет у нас]

### Two-pass comparison:
- Humanizer Pass B checklist items: N
- Наш Stage 4 Pass B checklist items: 11
- Уникальные в humanizer: [перечислить]
- Уникальные у нас: [перечислить]

### Рекомендации:
- [что можно перенять из humanizer в наши промпты]
```

===
