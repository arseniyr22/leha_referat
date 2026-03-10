# Промпт для создания скилла #7: pattern-auditor

## Цель скилла

Создать Claude Code скилл `pattern-auditor` — единый структурированный справочник всех 53 AI-паттернов (P1–P53) + 8 Formatting Fingerprint Rules (F1–F8), организованный по worker-назначению из агентной архитектуры. Скилл используется при написании кода HM-2/HM-3/HM-4 workers, их промптов, тестов и при аудите выходного текста.

---

## Метаданные скилла

```yaml
name: pattern-auditor
description: "Полный справочник 53 AI-паттернов (P1–P53) + 8 F-rules (F1–F8), организованный по worker-назначению. SCAN — детекция паттернов в тексте. BUILD — проверка что worker/промпт покрывает свои паттерны. AUDIT — полный аудит текста на все 61 правило. Ядро знаний для Phases 4–5."
trigger: При написании/модификации любого HM-2/HM-3/HM-4 worker'а или промпта, при аудите текста на AI-паттерны, при создании тестовых фикстур, при проверке покрытия паттернов worker'ами
```

---

## Структура скилла

```
.claude/skills/pattern-auditor/
├── SKILL.md                              # Основной файл (триггер, цель, процесс, правила)
└── reference/
    ├── worker_pattern_map.md             # Маппинг: worker → паттерны (из GAP 7)
    ├── patterns_by_category.md           # Все 53 паттерна, сгруппированные по 8 категориям
    ├── f_rules.md                        # 8 F-rules (F1–F8, где F4b — подправило F4) с register-зависимыми условиями
    ├── detection_patterns.md             # Python regex/логика детекции для каждого паттерна
    └── pattern_interactions.md           # Взаимозависимости и конфликты между паттернами
```

---

## Содержание SKILL.md

### Секция 1: Имя и триггер

**Имя:** pattern-auditor

**Триггер (когда активировать):**
- При написании кода HM-2 workers: `hm2_scaffold_breaker.py`, `hm2_format_cleaner.py`, `hm2_connector_tuner.py`, `hm2_triplet_buster.py`
- При написании кода HM-3 workers: `hm3_vocab_eliminator.py`, `hm3_hedging_auditor.py`, `hm3_attribution_fixer.py`, `hm3_result_formatter.py`
- При написании кода HM-4 workers: `hm4_soul_injector.py`, `hm4_rhythm_shaper.py`, `hm4_pass_b_auditor.py`
- При написании промптов для agents/prompts/hm*.md
- При создании тестовых фикстур в tests/fixtures/
- При аудите текста на оставшиеся AI-паттерны
- При проверке что worker покрывает все назначенные ему паттерны

**Команда:** `/pattern-auditor [mode] [target]`

**Режимы:**
- `scan <text>` — найти все AI-паттерны в тексте, вернуть список с номерами и примерами
- `build <worker_name>` — показать все паттерны, которые этот worker должен обрабатывать, с regex детекции и fix-правилами
- `audit` — полный аудит текста на все 61 правило (53 P + 8 F) с отчётом pass/fail
- `fixtures <worker_name>` — сгенерировать тестовые примеры БЫЛО → СТАЛО для паттернов этого worker'а

**Примеры:**
```
/pattern-auditor build hm2_scaffold_breaker
→ Показать P9, P12, P24, P25–P27, P44–P53 с детекцией и fix-правилами

/pattern-auditor build hm3_vocab_eliminator
→ Показать P1, P2, P3, P4, P7, P8, P11, P22, P28, P35, F8 с детекцией и fix-правилами

/pattern-auditor scan
→ (запросит текст) → отчёт по всем найденным паттернам

/pattern-auditor audit
→ (запросит текст) → полный отчёт 61 правило с pass/fail/count
```

---

### Секция 2: Цель

Обеспечить Claude Code мгновенным доступом к полной базе знаний по AI-паттернам при написании любого компонента системы гуманизации. Без этого скилла Claude Code вынужден каждый раз перечитывать 1200+ строк CLAUDE.md и 750 строк IMPLEMENTATION_PLAN.md для поиска нужных паттернов.

**Ценность:**
1. При `build` mode — Claude Code получает ТОЛЬКО паттерны конкретного worker'а с полной детализацией (regex, fix, примеры, edge cases, register-зависимости)
2. При `scan` mode — быстрая проверка текста без запуска pipeline
3. При `audit` mode — полный 61-rule чеклист для финальной верификации
4. При `fixtures` mode — готовые тестовые пары для pytest

---

### Секция 3: Step-by-Step Process

#### Режим BUILD

Шаг 3.1 — Определить worker по имени
Шаг 3.2 — Загрузить reference/worker_pattern_map.md → найти все паттерны этого worker'а
Шаг 3.3 — Для каждого паттерна загрузить из reference/patterns_by_category.md:
  - Полное описание (что AI делает, что человек делает)
  - Watch words / detection signals
  - Fix правило с примером БЫЛО → СТАЛО
  - Register-зависимые ограничения (если есть)
  - Связанные AC-правила (если есть)
Шаг 3.4 — Загрузить из reference/detection_patterns.md: Python regex или структурная логика детекции
Шаг 3.5 — Загрузить из reference/f_rules.md: F-rules назначенные этому worker'у (если есть)
Шаг 3.6 — Загрузить из reference/pattern_interactions.md: взаимозависимости с другими паттернами
Шаг 3.7 — Вывести структурированный отчёт:

```
## Worker: {worker_name}
### Назначенные паттерны: {list}
---
### P{N} · {Name}
**Категория:** {category}
**Severity:** {hard_ban | soft | rate_limited}
**Что детектировать:** {watch words / regex}
**Как исправлять:** {fix rule}
**Пример:**
  БЫЛО: {ai_text}
  СТАЛО: {human_text}
**Register-gate:** {if applicable}
**AC-gate:** {if applicable}
**Python detection:**
```python
{regex or structural logic}
```
**Взаимодействия:** {related patterns}
---
### F{N} · {Name} (если назначен этому worker'у)
{same structure}
```

#### Режим SCAN

Шаг 3.1 — Получить текст (из аргумента или запросить)
Шаг 3.2 — Определить language и register (по содержанию текста)
Шаг 3.3 — Последовательно проверить все 53 P-паттерна + 8 F-rules
Шаг 3.4 — Для каждого найденного: номер, цитата из текста, fix-рекомендация
Шаг 3.5 — Вывести отчёт:

```
## Pattern Scan Report
Language: {ru|en} | Register: {academic|journalistic|...}
Total patterns found: {N}

### HARD FAILURES (must fix):
- P10 (Triplets): 3 instances — "social, cultural, and linguistic factors" (line 12)
- P9 (Announcement openers): 1 instance — "Here's the problem with..." (line 5)

### WARNINGS (should fix):
- P7 (AI Vocabulary): 5 instances — "crucial" ×2, "pivotal" ×1, "landscape" ×2
- P29 (Connector monotony): "Furthermore" ×3 in 300 words

### INFO:
- F2 (Em dashes): 4 em dashes (target: 0 for EN)
- But:However ratio: 1:3 (target: ≥ 2:1)
```

#### Режим AUDIT

Шаг 3.1 — Получить текст + language + register + domain
Шаг 3.2 — Выполнить SCAN mode
Шаг 3.3 — Дополнительно проверить:
  - Структурные метрики: paragraph CV, section CV, sentence CV
  - Connector density per page
  - But:However / Но:Однако ratio
  - Citation density vs. domain baseline
  - "Also" frequency
  - Modal hedging on result sentences
  - Passive voice percentage vs. threshold (AC-4)
  - Perplexity skip gate (AC-15)
Шаг 3.4 — Вывести полный 61-rule чеклист с pass/fail/count/target

#### Режим FIXTURES

Шаг 3.1 — Определить worker по имени
Шаг 3.2 — Для каждого назначенного паттерна: сгенерировать 2–3 тестовых пары:
  - input_text: AI-текст с этим паттерном (реалистичный, 2–4 предложения)
  - expected_output: человеческий текст без этого паттерна
  - pattern_id: "P{N}"
  - severity: "hard" | "soft"
Шаг 3.3 — Вывести в формате pytest fixtures:

```python
@pytest.mark.parametrize("input_text,expected_pattern_absent,pattern_id", [
    ("The model may achieve 95% accuracy.", "может", "P32"),
    ...
])
def test_{worker_name}_removes_pattern(input_text, expected_pattern_absent, pattern_id):
    ...
```

---

### Секция 4: Правила (R1–R8)

**R1 (Источник истины):** CLAUDE.md — единственный источник истины для описаний паттернов. Если reference файлы расходятся с CLAUDE.md — CLAUDE.md побеждает.

**R2 (Worker assignment):** Маппинг паттерн→worker берётся из IMPLEMENTATION_PLAN.md GAP 7. Если GAP 7 не покрывает паттерн — проверить CLAUDE.md "Stage assignment" строку.
**ВНИМАНИЕ — Stage reassignments:** GAP 7 перераспределяет некоторые паттерны между Stage'ами по сравнению с CLAUDE.md:
- P8 (Copula Avoidance): CLAUDE.md Stage 2 → GAP 7: hm3_vocab_eliminator (Stage 3). Причина: copula restoration — лексическая замена ("serves as" → "is"), группируется с P7/P28.
- P17 (Emojis), P18 (Curly Quotes): CLAUDE.md Stage 3 → GAP 7: hm2_format_cleaner (Stage 2). Причина: чисто форматные операции, группируются с P13–P16.
- P29 (Connector Monotony): CLAUDE.md Stage 3 → GAP 7: hm2_connector_tuner (Stage 2). Причина: connector tuning — структурная операция, связанная с P33/P40/P43.
Эти перемещения — намеренные архитектурные решения GAP 7, а НЕ ошибки.

**R3 (Hard bans):** Паттерны с severity "hard_ban" должны иметь target count = 0 в output. Это: P9 (announcement openers), P10 (triplets), P24 (paragraph-ending generalizations), P31 (information-first violations), P32 (modal hedging on results), P35 (standalone definitions), P44 (superlative opener), P45 (dramatic reveal), P46 (meta-media), P47 (binary future), P48 (neither wrap), P49 (elegant reversal), P50 (same-X-that-also), P51 (whether-or-just), P52 (mechanism run-on), P53 (participial simultaneity).
**НЕ hard_ban (register-dependent):** P17 (emojis — hard ban только в academic/professional).

**R4 (Register gates):** Следующие паттерны имеют register-зависимое применение:
- P26: academic → paragraph-level only (AC-3/AC-10)
- P30: academic → limited toolkit, journalistic → full toolkit
- P34: math/IT → 0 rhetorical questions, social science → 1–2 per 750w
- F5: academic → skip entirely; RU → skip entirely (AC-7)
- F6: academic → skip entirely; RU journalistic → comma only (AC-7)
- F7: academic → skip entirely

**R5 (Language gates):** Следующие паттерны имеют language-зависимое применение:
- P7: language='ru' → использовать p7_russian из config.yaml (AC-6/AC-14)
- P29: language='ru' → использовать p29_russian из config.yaml (AC-6)
- P13/F2: language='ru' → conservative em dash reduction (AC-1)
- P18/AC-8: language='ru' → guillemets «», language='en' → straight quotes "
- P33: language='ru' → Но:Однако ratio (AC-12), language='en' → But:However ratio
- Perplexity scoring: language='ru' → skip (AC-15), GPT-2 English-only

**R6 (Severity classification):**
- `hard_ban` = target count 0, any instance is FAIL → routing priority P1–P2
- `soft` = has target threshold, exceeding is WARN → routing priority P3–P5
- `rate_limited` = allowed N per 500 words or per document
- `injection` = must be ADDED to output (not removed) — P30, P34, F5, F6, F7

**R7 (Detection precision):** Regex patterns в detection_patterns.md — это СТАРТОВАЯ ТОЧКА. LLM-judgment нужен для: P12 (false range vs real range), P24 (paragraph-ending generalizations), P26 (structural ordering), P30 (imperfection absence), P41 (domain norms — meta-pattern, no regex possible). Regex catches ~70% of instances; LLM catches the rest.

**R8 (Cross-references):** При выводе BUILD отчёта ВСЕГДА указывать:
- Связанные AC-правила (из ac-gate скилла)
- Связанные метрики из config.yaml: scoring section
- Связанные промпты из prompts/ directory

---

## Содержание reference/worker_pattern_map.md

Это ПОЛНЫЙ маппинг из IMPLEMENTATION_PLAN.md GAP 7, дополненный F-rules:

```markdown
# Worker → Pattern Map

## HM-2 Workers (Stage 2: Structural & Format Rewrite)

### hm2_scaffold_breaker
Patterns: P9, P12, P24, P25, P26, P27, P44, P45, P46, P47, P48, P49, P50, P51, P52, P53
Summary: Announcement openers, false ranges, paragraph-ending generalizations, paragraph/section uniformity, default ordering, sentence-starter monotony, ALL Category 8 scaffold patterns (P44–P53)
Hard bans: P9, P24, P44, P45, P46, P47, P48, P49, P50, P51, P52, P53
Soft: P25 (para CV ≥ 0.50), P26 (structural ordering), P27 (no 3+ same-start)

### hm2_format_cleaner
Patterns: P13, P14, P15, P16, P17, P18
F-Rules: F1, F2, F3, F4, F4b
Summary: Em dashes, boldface, inline-header lists, title case, emojis, curly quotes + formatting fingerprints
AC-gates: AC-1 (em dashes RU), AC-8 (quotes RU), AC-9 (list-to-prose scope)
Soft (register-dependent): P17 (emojis — remove in academic/professional, tolerate in casual/social)
Register-dependent: F1 (Oxford comma), F2 (em dash = 0 ALL registers), F3 (semicolons: 0 journalistic, ≤1/500w academic), F4 (colons: 0 journalistic body, ≤1/300w academic), F4b (parentheses: ≤1/300w academic, 0–1/500w journalistic)

### hm2_connector_tuner
Patterns: P29, P33, P40, P43
Summary: Connector monotony, But:However ratio, connector scarcity baseline, "Also" frequency
AC-gates: AC-12 (Но:Однако for RU)
Hard bans: P29 absolute ban list (Firstly, Secondly, Thirdly, Finally, Additionally)
Soft: P33 (ratio ≥ 2:1), P40 (density ≤ targets), P43 (Also ≥ 0.08/page)

### hm2_triplet_buster
Patterns: P10
Summary: Rule of Three — zero tolerance on all three-item parallel series
Hard ban: P10 (target: 0 instances — noun, verb, adverbial tricolons)
Technical exception: exactly 3 genuinely existing items → use numbered list

## HM-3 Workers (Stage 3: Lexical & Tonal Cleanup)

### hm3_vocab_eliminator
Patterns: P1, P2, P3, P4, P7, P8, P11, P22, P28, P35
F-Rules: F8
Summary: Significance inflation, notability emphasis, -ing endings, promotional language, AI vocabulary banlist, copula avoidance, elegant variation, filler phrases, register inflation, jargon definitions, hyphenated compounds
AC-gates: AC-6/AC-14 (Russian P7), AC-11 (definition forms)
Hard bans: P7 absolute ban, P7 importance-framing ban, P7 announcement ban, P7 paired-abstraction ban
Domain-exempt: P7 context-dependent list (crucial/key/important — allowed in academic IF after evidence AND specific mechanism AND <3/500w)

### hm3_hedging_auditor
Patterns: P23, P32, P38
Summary: Excessive hedging → one qualifier max, modal hedging on results → remove modals on measured data, attribution-based hedging → name source
Hard bans: P32 (modal + number = FAIL)
Soft: P23 (stacked qualifiers), P38 (isolated modals without attribution: <0.5/300w)

### hm3_attribution_fixer
Patterns: P5, P39, P42
Summary: Vague attributions → named sources, counter-argument integration → named scholars, citation density calibration by domain
AC-gates: AC-2 (GOST [N] for RU academic), AC-13 (citation density vs GOST stream minimums — enforced independently)
Soft: P5 (attributive passive count target: 0), P42 (density vs domain baseline)

### hm3_result_formatter
Patterns: P6, P31, P36
Summary: Formulaic challenge/prospect sections, information-first posture, results without evaluative praise
Hard bans: P31 (information-first — delete importance claims)
Template: Result + number + baseline comparison + mechanism. No evaluative adjectives.

## HM-4 Workers (Stage 4: Voice & Discourse Injection)

### hm4_soul_injector
Patterns: P19, P20, P21, P30, P34
F-Rules: F5, F6, F7
Summary: Chatbot artifacts, knowledge-cutoff disclaimers, sycophancy, imperfection texture INJECTION, rhetorical questions
AC-gates: AC-5 (no figurative for RU academic), AC-7 (F5/F6 skip for RU/academic), AC-4 (passive threshold)
INJECTION patterns (add to output): P30 (imperfections), P34 (rhetorical questions), F5 (apostrophe drops), F6 (grammar errors), F7 (filler words)
Register-dependent:
  P30 academic: ONLY epistemic hedging, methodological asides, mild evaluative. Rate: ≤2/300w
  P30 journalistic: full toolkit (fragments, register drops, discourse markers)
  P34: social science 1–2/750w, math/IT 0, journalistic 1/500w
  F5: skip for RU, skip for academic (AC-7)
  F6: skip for academic; RU journalistic = comma only (AC-7)
  F7: skip for academic; RU = "в общем-то", "собственно говоря" sparingly

### hm4_rhythm_shaper
Patterns: P25, P37
Summary: Paragraph-level uniformity enforcement (para CV ≥ 0.50), section-level asymmetry (section CV ≥ 0.30)
Soft: P25 (para CV target), P37 (section CV target, conclusion < 20% of body)

### hm4_pass_b_auditor
Patterns: ALL (14-point checklist audit)
Summary: Two-pass audit Pass B — 14-point checklist covering residual tells from ALL categories
Checklist items (from CLAUDE.md Stage 4 Two-Pass):
  1. Topic-sentence pattern — break in ≥1 paragraph
  2. Transition variety — no connector >2× per page
  3. Linear structure — reorder ≥1 section
  4. Figurative language — ≥1 metaphor/analogy per section (unless AC-5 skip)
  5. Length — shorter than typical AI output
  6. Triplets — zero tolerance (P10)
  7. Abstraction altitude — no 3+ sentences at same level
  8. False certainty — add hedging on contested claims
  9. Tense monotony — no >80% same tense
  10. Announcement openers — 0 instances (P9)
  11. Paragraph-ending generalizations — 0 instances (P24)
  12. Information-first (P31) — added from corpus
  13. Modal hedging on results (P32) — added from corpus
  14. But:However ratio (P33) / Но:Однако (AC-12) — added from corpus

### hm4_example_loader
No patterns directly. Loads few-shot human examples from ВШЭ corpus for Stage 4 reference.

## Shared Services (не worker'ы, но обрабатывают паттерны)

### Domain Gate (language_gate.py / domain_gate.py)
Patterns: P41
Summary: Domain Epistemological Norm Adherence — мета-паттерн, который гейтит ВСЕ downstream workers через domain+register+language classification. Не детектирует/исправляет конкретные фразы, а определяет КАКИЕ правила применяются к тексту.
P41 enforcement: Stage 1 domain classifier → gates all P7 exemptions, P29 register rules, P30 mode selection, P34 domain distribution, AC-4/AC-5/AC-7 language gates.
Note: P41 нельзя назначить конкретному worker'у — это meta-pattern, который влияет на ВСЕ workers через config и gates.
```

---

## Содержание reference/patterns_by_category.md

Все 53 паттерна, дословно из CLAUDE.md (секции "AI Pattern Catalog" и "Category 8"), организованные по 8 категориям:

**ВАЖНО для реализации:** Содержание этого файла — ДОСЛОВНАЯ КОПИЯ паттернов из CLAUDE.md, секции:
- "Category 1 — Content Patterns" (P1–P6)
- "Category 2 — Language & Grammar Patterns" (P7–P12)
- "Category 3 — Style Patterns" (P13–P18)
- "Category 4 — Communication Patterns" (P19–P21)
- "Category 5 — Filler & Hedging Patterns" (P22–P24)
- "Category 6 — Structural & Discourse Patterns" (P25–P30)
- "Category 7 — Extended Patterns" (P31–P43)
- "Category 8 — GPTZero Scaffold Patterns" (P44–P53)

Каждый паттерн должен включать:
1. **Номер и имя** (P1 · Significance & Legacy Inflation)
2. **Watch words / detection signals** (полный список из CLAUDE.md)
3. **Fix rule** с примером БЫЛО → СТАЛО
4. **Stage assignment** (из CLAUDE.md, если указан)
5. **Severity classification:** hard_ban | soft | rate_limited | injection
6. **Register/language gates** (если есть)
7. **AC-rule связь** (если есть)

Добавить к каждому паттерну поле **Worker assignment** из worker_pattern_map.md.

---

## Содержание reference/f_rules.md

Все 8 F-rules дословно из CLAUDE.md секции "Formatting Fingerprint Rules (F1–F8)".
**Нумерация:** F1, F2, F3, F4, F4b, F5, F6, F7, F8. F4b — подправило F4 (parenthesis minimization vs colon reduction). При подсчёте: 8 основных (F1–F8) + 1 подправило (F4b) = 9 записей в файле, но формально 8 F-rules:

Каждый F-rule должен включать:
1. **Номер и имя** (F1 · No Oxford Comma)
2. **Rule** (полное описание)
3. **Before/After** пример
4. **Register-зависимость** (какие registers — какие правила)
5. **Language-зависимость** (RU отличия — AC-1, AC-7, AC-8)
6. **Worker assignment** (из worker_pattern_map)
7. **Stage assignment** (из CLAUDE.md)

---

## Содержание reference/detection_patterns.md

Python regex и структурная логика детекции для каждого паттерна. Организовать по worker'ам:

```markdown
# Detection Patterns by Worker

## hm2_scaffold_breaker

### P9 — Negative Parallelisms & Announcement Openers
```python
import re

# Part A: Negative parallelism constructions (PRIMARY definition of P9)
NEGATIVE_PARALLELISM_EN = [
    r"(?i)not\s+only\s+.{3,50},?\s+but\s+(?:also|additionally)",
    r"(?i)it'?s\s+not\s+just\s+(?:about\s+)?.{3,40}[;,—]\s+it'?s",
    r"(?i)not\s+merely\s+.{3,40},?\s+but",
    r"(?i)beyond\s+mere\s+.{3,30},?\s+it\s+represents",
    r"(?i)it\s+was\s+not\s+just\s+.{3,40}\.\s+It\s+was\s+",
    r"(?i)this\s+(?:isn'?t|wasn'?t|is\s+not)\s+(?:about|just)\s+.{3,40}[.;—]\s+(?:it'?s|this\s+is)",
]
NEGATIVE_PARALLELISM_RU = [
    r"не\s+только\s+.{3,50},?\s+но\s+(?:и|также)",
    r"это\s+не\s+просто\s+.{3,40}[,;—]\s+(?:это|а)",
    r"речь\s+идёт\s+не\s+(?:только\s+)?о\s+.{3,40},?\s+(?:а|но)\s+о",
]

# Part B: Announcement openers (SECONDARY — organic-sounding variants)
ANNOUNCEMENT_OPENERS_EN = [
    r"(?i)here'?s the problem with",
    r"(?i)is worth a brief detour",
    r"(?i)there'?s also a .+ worth flagging",
    r"(?i)one thing you rarely see .+ is",
    r"(?i)also deserves mention",
    r"(?i)I mention this mostly because",
    r"(?i)is actually (?:remarkable|unprecedented|substantial)",
    r"(?i)is instructive (?:about|for)",
    r"(?i)repeats the same (?:story|pattern) across",
    r"(?i)this section will (?:explore|examine|discuss)",
    r"(?i)in what follows,? we (?:examine|explore|discuss)",
    r"(?i)we will now (?:examine|explore|turn to)",
]

ANNOUNCEMENT_OPENERS_RU = [
    r"следует отметить,?\s*что",
    r"необходимо отметить,?\s*что",
    r"важно подчеркнуть,?\s*что",
    r"стоит отметить,?\s*что",
    r"обратим внимание на то",
    r"отметим,?\s*что",
    r"необходимо указать,?\s*что",
    r"хотелось бы отметить",
    r"в данном разделе (?:рассмотрим|проанализируем|исследуем)",
    r"далее (?:рассмотрим|проанализируем|перейдём к)",
]

def detect_p9(text: str, language: str) -> list[dict]:
    """Detect both negative parallelisms (Part A) and announcement openers (Part B)."""
    if language == 'ru':
        all_patterns = NEGATIVE_PARALLELISM_RU + ANNOUNCEMENT_OPENERS_RU
    else:
        all_patterns = NEGATIVE_PARALLELISM_EN + ANNOUNCEMENT_OPENERS_EN
    findings = []
    for p in all_patterns:
        for m in re.finditer(p, text):
            findings.append({'pattern': 'P9', 'match': m.group(), 'pos': m.start(), 'severity': 'hard_ban'})
    return findings
```

### P10 — Triplets (Zero Tolerance)
```python
# Noun triplets: "X, Y, and Z" / "X, Y и Z"
TRIPLET_EN = re.compile(r'\b(\w+(?:\s+\w+)?),\s+(\w+(?:\s+\w+)?),?\s+and\s+(\w+(?:\s+\w+)?)\b')
TRIPLET_RU = re.compile(r'\b(\w+(?:\s+\w+)?),\s+(\w+(?:\s+\w+)?)\s+и\s+(\w+(?:\s+\w+)?)\b')

# Verb tricolons: "She X, Y, and Z"
VERB_TRICOLON_EN = re.compile(r'(\w+ed|\w+s)\s.*?,\s+(\w+ed|\w+s)\s.*?,?\s+and\s+(\w+ed|\w+s)\b')

# Adverbial tricolons: "partly to X, partly to Y, partly to Z"
ADVERB_TRICOLON_EN = re.compile(r'(?:partly|partially)\s+(?:to|from|by)\s+.+?,\s+(?:partly|partially)\s+(?:to|from|by)\s+.+?,?\s+(?:and\s+)?(?:partly|partially)\s+(?:to|from|by)')
ADVERB_TRICOLON_RU = re.compile(r'отчасти\s+(?:из-за|благодаря|в силу)\s+.+?,\s+отчасти\s+(?:из-за|благодаря|в силу)\s+.+?,?\s+(?:и\s+)?отчасти')

# Parallel negation: "no X, no Y, no Z"
PARALLEL_NEG_EN = re.compile(r'\bno\s+\w+.{0,30},\s+no\s+\w+.{0,30},\s+no\s+\w+')
PARALLEL_NEG_RU = re.compile(r'\bни\s+\w+.{0,30},\s+ни\s+\w+.{0,30},\s+ни\s+\w+')
```

### P12 — False Ranges
```python
# "from X to Y" where X and Y are not on a meaningful spectrum
FALSE_RANGE_EN = re.compile(
    r'(?i)from\s+(?:the\s+)?(\w+(?:\s+\w+){0,3})\s+to\s+(?:the\s+)?(\w+(?:\s+\w+){0,3})',
)
FALSE_RANGE_RU = re.compile(
    r'(?:от|начиная\s+с)\s+(\w+(?:\s+\w+){0,3})\s+(?:до|к)\s+(\w+(?:\s+\w+){0,3})',
)
# NOTE: Regex catches all "from X to Y" constructions. LLM judgment required to
# distinguish genuine scalar ranges ("from 10 to 50", "from Monday to Friday")
# from false ranges ("from the singularity of the Big Bang to the grand cosmic web").
# False positive rate: ~60% — LLM filtering essential.
```

### P24 — Generic Positive Conclusions & Paragraph-Ending Generalizations
```python
# Part A: Generic positive conclusions (watch words — can appear anywhere in final sentence)
GENERIC_POSITIVE_EN = [
    r'(?i)the\s+future\s+looks?\s+bright',
    r'(?i)exciting\s+times\s+lie\s+ahead',
    r'(?i)major\s+step\s+in\s+the\s+right\s+direction',
    r'(?i)journey\s+toward\s+excellence',
    r'(?i)paves?\s+the\s+way\s+for\s+(?:a\s+)?(?:brighter|better|more)',
    r'(?i)promising\s+(?:future|outlook|trajectory)',
]
GENERIC_POSITIVE_RU = [
    r'(?i)перспективы\s+(?:выглядят|представляются)\s+(?:многообещающ|оптимистичн)',
    r'(?i)открывает\s+(?:новые\s+)?(?:горизонты|перспективы|возможности)',
    r'(?i)важный\s+шаг\s+(?:на\s+пути|в\s+направлении)',
]

# Part B: Paragraph-ending generalization wraps (abstract lessons extracted from concrete facts)
PARA_END_GENERALIZATION_EN = [
    r'(?i)complicates?\s+any\s+(?:\w+\s+)?(?:story|narrative|account)\s+about',
    r'(?i)repeats?\s+the\s+same\s+(?:\w+\s+)?(?:pattern|story|dynamic)\s+across',
    r'(?i)regardless\s+of\s+how',
    r'(?i)any\s+simple\s+(?:\w+\s+)?(?:story|narrative|explanation)\s+about',
    r'(?i)(?:the\s+)?(?:broader|larger|wider)\s+(?:lesson|implication|point|takeaway)\s+(?:is|here|being)',
    r'(?i)this\s+(?:demonstrates|illustrates|shows|suggests|underscores)\s+(?:that|how|the)',
]
PARA_END_GENERALIZATION_RU = [
    r'это\s+(?:свидетельствует|демонстрирует|показывает|иллюстрирует)',
    r'данный\s+(?:факт|пример)\s+(?:свидетельствует|подтверждает)',
    r'вышесказанное\s+(?:свидетельствует|подтверждает|демонстрирует)',
]

def detect_p24(text: str, language: str) -> list[dict]:
    """Detect generic positive conclusions (Part A) and paragraph-ending generalizations (Part B).
    Both parts applied only to LAST sentence of each paragraph."""
    paragraphs = text.split('\n\n')
    findings = []
    if language == 'ru':
        all_patterns = GENERIC_POSITIVE_RU + PARA_END_GENERALIZATION_RU
    else:
        all_patterns = GENERIC_POSITIVE_EN + PARA_END_GENERALIZATION_EN
    for i, para in enumerate(paragraphs):
        sentences = para.strip().split('. ')
        if not sentences:
            continue
        last_sentence = sentences[-1]
        for p in all_patterns:
            if re.search(p, last_sentence):
                findings.append({'pattern': 'P24', 'match': last_sentence[:80], 'paragraph': i, 'severity': 'hard_ban'})
    return findings
# NOTE: LLM judgment needed for subtle generalizations not caught by regex.
# Regex covers ~50% of cases; structural analysis (abstract vs specific) needed for rest.
```

### P27 — Sentence-Starter Monotony
```python
import spacy

def detect_p27(text: str, language: str) -> list[dict]:
    """Detect 3+ consecutive sentences starting with the same word or grammatical category."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    findings = []
    for i in range(len(sentences) - 2):
        # Simple check: same first word
        words = [s.split()[0].lower() if s.split() else '' for s in sentences[i:i+3]]
        if words[0] == words[1] == words[2] and words[0]:
            findings.append({
                'pattern': 'P27',
                'match': f'3 consecutive sentences starting with "{words[0]}"',
                'pos': i,
                'severity': 'soft',
                'sentences': [s[:60] for s in sentences[i:i+3]]
            })
    return findings

# Regex shortcut for common patterns:
P27_THE_RUN = re.compile(r'(?:^|\n)The\s+\w+[^.]*\.\s+The\s+\w+[^.]*\.\s+The\s+', re.MULTILINE)
P27_THIS_RUN = re.compile(r'(?:^|\n)This\s+\w+[^.]*\.\s+This\s+\w+[^.]*\.\s+This\s+', re.MULTILINE)
P27_IT_RUN = re.compile(r'(?:^|\n)It\s+\w+[^.]*\.\s+It\s+\w+[^.]*\.\s+It\s+', re.MULTILINE)
# Russian equivalents
P27_RU_PATTERNS = [
    re.compile(r'(?:^|\n)Это\s+[^.]*\.\s+Это\s+[^.]*\.\s+Это\s+', re.MULTILINE),
    re.compile(r'(?:^|\n)Данн\w+\s+[^.]*\.\s+Данн\w+\s+[^.]*\.\s+Данн\w+\s+', re.MULTILINE),
]
# NOTE: Full detection requires POS-tagging (spaCy) to catch grammatical category runs,
# not just same-word runs. Regex catches ~40% of cases.
```

### P44–P53 — GPTZero Scaffold Patterns
```python
# P44: Superlative importance opener
P44 = re.compile(r'^(?:The\s+)?(?:most|biggest|largest|greatest|single\s+most)\s+(?:consequential|significant|important|transformative|disruptive)', re.MULTILINE | re.IGNORECASE)

# P45: Two-sentence dramatic reveal (short sentence ≤8 words followed by reversal)
# Detection requires structural analysis — regex catches obvious cases
P45_PATTERN = re.compile(r'(?:wasn\'?t|isn\'?t|didn\'?t|aren\'?t|weren\'?t)\s+.{2,30}\.\s+(?:It\s+was|It\'?s|They\s+(?:were|are)|This\s+(?:is|was))\s+', re.IGNORECASE)

# P46: Meta-media commentary
P46_MARKERS = [
    r'(?i)(?:gets?|receives?)\s+less\s+(?:attention|coverage)\s+than',
    r'(?i)rarely\s+makes?\s+(?:front\s+pages?|headlines?)',
    r'(?i)(?:harder|difficult)\s+to\s+write\s+headlines?\s+about',
    r'(?i)the\s+story\s+that\s+(?:never|rarely)\s+(?:quite\s+)?gets?\s+told',
    r'(?i)beneath\s+the\s+(?:geopolitical|political|economic)\s+drama',
]

# P47: Binary future force projection
P47 = re.compile(r'(?i)will\s+(?:eventually|ultimately|inevitably)\s+(?:force|require|demand|mean)\s+(?:either|a\s+choice\s+between)')

# P48: Binary neither wrap-up
P48 = re.compile(r'(?i)neither\s+(?:outcome|side|option|scenario|of\s+these)\s+(?:is|are|benefits?|looks?)\s+(?:good|reassuring|promising|ideal)', re.IGNORECASE)

# P49: Elegant reversal
P49_PATTERNS = [
    r'(?i)what\s+\w+\s+(?:is|are)\s+doing\s+is\s+\w+\s+rather\s+than',
    r"(?i)the\s+question\s+isn'?t\s+.{3,40}\s*[—–-]\s*it'?s",
    r"(?i)(?:aren'?t|isn'?t|didn'?t|don'?t)\s+.{3,30};\s+they'?re\s+",
]

# P50: Same-X-that-also
P50 = re.compile(r'(?i)the\s+same\s+\w+\s+that\s+.{10,60}\s+also\s+')

# P51: Whether-or-just closure
P51 = re.compile(r'(?i)whether\s+.{10,80}\s+or\s+(?:just|merely|simply)\s+')

# P52: Mechanism attribution run-on (3+ nested "that" clauses)
# Count "that" in a single sentence
def detect_p52(sentence: str) -> bool:
    return sentence.count(' that ') >= 3

# P53: Participial simultaneity
P53_PATTERNS = [
    re.compile(r'(?i)while\s+(?:simultaneously|also)\s+(?:\w+ing)'),
    re.compile(r'(?i)even\s+as\s+\w+\s+simultaneously\s+(?:\w+s|\w+ed|\w+ing)'),
    re.compile(r'(?i)(?:\w+ing)\s+.{3,30}\s+while\s+simultaneously\s+(?:\w+ing)'),
]
```

Продолжить аналогично для ВСЕХ worker'ов (hm2_format_cleaner, hm2_connector_tuner, hm3_*, hm4_*).

Для каждого regex указать:
- Какой паттерн он детектирует
- Язык (EN / RU / both)
- Ожидаемый false positive rate
- Когда нужен LLM judgment вместо regex

---

## Содержание reference/pattern_interactions.md

Документирует взаимозависимости и потенциальные конфликты между паттернами:

```markdown
# Pattern Interactions

## Reinforcing Groups (fixing one helps fix others)

### Group A: Vocabulary Cleanup (P1 + P3 + P4 + P7 + P8 + P28)
Все эти паттерны связаны с AI-лексикой. Fixing P7 (banlist) автоматически уменьшает P1 (significance inflation) и P4 (promotional language). P8 (copula avoidance) часто сопровождается P7 словами.
Worker: hm3_vocab_eliminator handles all.

### Group B: Structural Scaffold (P9 + P25 + P26 + P27 + P44–P53)
Все эти паттерны связаны со структурной предсказуемостью AI-текста. P26 (default ordering) создаёт среду для P25 (uniformity). P44–P53 (scaffold patterns) — это конкретные проявления P26 на уровне аргументации.
Worker: hm2_scaffold_breaker handles all.

### Group C: Attribution & Hedging (P5 + P23 + P32 + P38 + P39)
Все связаны с тем, КАК AI ссылается на источники и хеджирует claims. P5 (vague attributions) и P38 (attribution-based hedging) — две стороны одной проблемы. P32 (modal hedging on results) — частный случай P23 (excessive hedging) для числовых данных.
Workers: hm3_hedging_auditor (P23, P32, P38) + hm3_attribution_fixer (P5, P39).

### Group D: Connector System (P29 + P33 + P40 + P43)
Все связаны с тем, как AI соединяет предложения. P29 (monotony) и P40 (scarcity baseline) — количественные метрики. P33 (But:However ratio) — качественная метрика. P43 ("Also" frequency) — injection target.
Worker: hm2_connector_tuner handles all.

## Potential Conflicts

### Conflict 1: P10 (triplets) vs. Technical enumeration
P10 requires zero triplets. But academic text may genuinely have 3 research questions, 3 experimental conditions.
Resolution: Technical enumeration exception — use numbered list format (1. X 2. Y 3. Z).

### Conflict 2: P30 (imperfection injection) vs. Register preservation
P30 injects roughness. Academic register requires polish.
Resolution: AC-5/AC-7 gates. Academic = limited P30 (epistemic hedging only). Journalistic = full toolkit.

### Conflict 3: P26 (non-linear ordering) vs. AC-3 (GOST macro-structure)
P26 wants to break linear ordering. AC-3 protects GOST section order.
Resolution: AC-3 wins at macro level. P26 operates at paragraph level within sections for academic.

### Conflict 4: P7 context-dependent vs. P41 domain norms
"Crucial", "key" banned by P7 but acceptable in management domain by P41.
Resolution: Domain exemption applies when: (a) after evidence, (b) specific mechanism, (c) <3/500w.

### Conflict 5: F2 (em dash = 0) vs. AC-1 (Russian copular dashes)
F2 wants zero em dashes. AC-1 requires preserving grammatical Russian dashes.
Resolution: AC-1 wins for language='ru'. F2 applies unconditionally for language='en'.

### Conflict 6: P29 (ban "Furthermore") vs. Academic convention
Some academic writers use "Furthermore" sparingly.
Resolution: Near-ban (≤1 per full document in academic). Not absolute ban.
```

---

## Инструкции для Claude Code

1. Создай папку `.claude/skills/pattern-auditor/` с файлами SKILL.md и reference/*.md
2. SKILL.md: реализуй по описанию в секциях 1–4 выше
3. reference/worker_pattern_map.md: скопируй маппинг из секции "Содержание reference/worker_pattern_map.md" выше
4. reference/patterns_by_category.md: скопируй ВСЕ 53 паттерна из CLAUDE.md (секции P1–P53), добавив к каждому поля severity и worker_assignment
5. reference/f_rules.md: скопируй все 8 F-rules из CLAUDE.md секции "Formatting Fingerprint Rules", добавив worker_assignment
6. reference/detection_patterns.md: реализуй Python regex для КАЖДОГО паттерна, организованные по worker'ам. Используй примеры из промпта как стартовую точку, но покрой ВСЕ 53+8 паттернов
7. reference/pattern_interactions.md: реализуй по описанию выше

**Критерий качества:** После создания скилла, вызов `/pattern-auditor build hm2_scaffold_breaker` должен вернуть ПОЛНУЮ информацию по всем 16 паттернам (P9, P12, P24, P25–P27, P44–P53) с regex, fix-правилами, примерами и AC-gates — достаточную для написания worker'а с нуля без обращения к CLAUDE.md.

**Верификация:**
1. Подсчитать паттерны в patterns_by_category.md — должно быть ровно 53
2. Подсчитать F-rules в f_rules.md — должно быть 9 записей (F1, F2, F3, F4, F4b, F5, F6, F7, F8). F4b — подправило F4.
3. Проверить что КАЖДЫЙ паттерн из CLAUDE.md присутствует (P1–P53, F1–F8)
4. Проверить что worker_pattern_map.md покрывает все 61 правило (53 P + 8 F). P41 покрыт через Shared Services (Domain Gate), не через worker.
5. Проверить что detection_patterns.md содержит regex для каждого worker'а
6. Сверить severity classification с hard ban списком в R3
