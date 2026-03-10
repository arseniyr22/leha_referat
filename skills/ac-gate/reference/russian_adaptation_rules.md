# Russian Language Adaptation Rules

Source: CLAUDE.md — "Russian Language Adaptation" section + "Russian F-Rules Differences" section
These rules define how the pipeline DIFFERS for Russian text vs. English.

---

## 1. Russian P7 Banlist

Source: `config.yaml: p7_russian` (verbatim values as of project current state)

### Absolute Ban (always remove, all registers)

These phrases are unconditionally removed from any Russian text regardless of domain or register:

```
следует отметить
является ключевым
играет важную роль
необходимо подчеркнуть
представляется актуальным
в условиях современности
на сегодняшний день
в наше время
как известно
очевидно, что
вышесказанное свидетельствует
немаловажно также
актуальность темы заключается в том
данная проблема является актуальной
в рамках данной работы
подводя итог вышесказанному
таким образом можно заключить
```

### Importance-Framing Ban (always remove)

Phrases that announce importance before stating content — delete entirely, state the content directly:

```
играет важную роль в
является ключевым для
имеет принципиальное значение
занимает особое место в
заслуживает особого внимания
представляет собой важный
является основополагающим
```

Fix pattern: "Миграционная политика играет важную роль в интеграции" → delete; write "Иммигранты, владеющие языком, находят стабильную работу в течение первого года [4]."

### Announcement Ban (always remove)

Phrases that describe what is about to be said instead of saying it:

```
следует отметить, что
необходимо отметить, что
важно подчеркнуть, что
стоит отметить, что
обратим внимание на то
отметим, что
необходимо указать, что
хотелось бы отметить
```

Fix pattern: "Следует отметить, что санкции оказали влияние" → delete preamble; write "Санкции привели к падению экспорта на 18% в 2022 году [3]."

---

## 2. Russian P29 Connector Rules

Source: `config.yaml: p29_russian` (verbatim values)

### Absolute Ban (0 per document)

```
во-первых
во-вторых
в-третьих
помимо этого
в дополнение к вышесказанному
```

### Near-Ban (≤ 1 per full document)

```
кроме того
```

### Rate-Limited (≤ 1 per 500 words)

```
более того
помимо прочего
```

### Permitted Connectors (not banned)

```
также
однако
но
при этом
между тем
тем не менее
вместе с тем
таким образом
следовательно
```

### Actively Encouraged (increase frequency vs. AI baseline)

```
также    ← primary additive connector (target: 0.10–0.25 per page)
но       ← primary contrast connector at sentence-initial position
однако   ← formal contrast (permitted but не overused)
```

### Target Но:Однако Ratio

Target: **≥ 2:1** (analogous to English But:However ≥ 2:1)
- Human corpus baseline: "Но" appears 2–4× more than "Однако" in academic text
- AI baseline: inverted (~Однако:Но = 3:1 to 5:1)
- Config key: `p29_russian.target_no_odnako_ratio: 2.0`

---

## 3. Russian P10 — Triplet Ban

The triplet ban (P10) applies **identically** in Russian.

Any three-item parallel series is a hard failure regardless of language:
- Noun tricolon: "социальные, культурные и языковые факторы" → "социальные и языковые факторы — и культурные, хотя их сложнее выделить"
- Verb tricolon: "повысила ставку, обязала экспортёров конвертировать выручку и ввела ограничения" → split after second item
- Adverbial tricolon: "отчасти из-за X, отчасти из-за Y, отчасти из-за Z" → keep two; third as separate sentence

Technical enumeration exception (identical to English): If exactly 3 items exist because only 3 genuinely exist, use numbered formatting (1. X 2. Y 3. Z) to break the typographic triplet.

---

## 4. Russian P32 — Modal Hedging on Results

The modal hedging ban applies **identically** in Russian.

Russian modal verbs banned from sentences containing numerical data:
```
может           (may)
мог бы          (could)
вероятно        (probably — when used as modal hedge on measured result)
по-видимому     (apparently — when hedging a measured result)
по всей видимости (apparently — when hedging a measured result)
можно предположить (one might assume)
предположительно  (presumably)
```

Rule: If a sentence contains **[число/статистика/метрика/процент]** AND **[modal verb from list above]** → remove the modal, state directly.

Correct: "CatBoost достиг наилучших показателей (RMSE: 0.096–0.109)."
Incorrect: "CatBoost может достичь наилучших показателей (RMSE: 0.096–0.109)."

Epistemic hedging IS allowed (and encouraged) for:
- Contested claims without numerical data
- Interpretive conclusions
- Methodological limitations
- Future projections

---

## 5. Russian F-Rules Differences

Source: CLAUDE.md — "Russian F-Rules Differences" section

### F2 — Em Dashes (CONSERVATIVE for Russian)

English rule: Remove all em dashes (target: 0).
Russian rule: **AC-1** governs. Conservative reduction only.

Preserve:
- Copular sentences: "Москва — столица России" (required by grammar)
- Definitions: "Перплексия — мера неожиданности текста для языковой модели"
- Appositives where em dash is grammatically standard

Remove (if >3 per paragraph):
- Stylistic mid-sentence asides where comma/parens would work
- Second+ em dash in sentences that already have one non-copular dash

### F3 — Semicolons (NO wholesale removal for Russian academic)

English rule (journalistic): Replace all semicolons with periods.
Russian academic rule: Semicolons acceptable in complex lists where list items themselves contain commas. Do NOT apply wholesale removal. Only remove if clearly stylistic/AI-generated outside list context.

### F5 — Apostrophe Drops (INAPPLICABLE to Russian)

English rule (journalistic): 3–5 controlled apostrophe drops on proper noun possessives.
Russian rule: **Skip entirely.** Russian language does not use apostrophes. No equivalent injection.

### F6 — Grammar Errors (RESTRICTED for Russian)

English (journalistic): 2–3 controlled minor grammar errors (types a–c).
Russian academic: **Skip entirely.** Grammar errors in Russian academic text are too visible and damage credibility.
Russian journalistic: Comma placement variation only (1–2 instances). No subject-verb agreement errors.

Permitted Russian journalistic F6 (comma variation only):
- Missing comma before subordinate clause in complex sentence (1 instance)
- Extra comma in compound predicate (1 instance)

Forbidden Russian F6 (any register):
- Subject-verb agreement errors
- Case ending errors
- Aspect errors (perfective/imperfective)
- Gender agreement errors

### F7 — Filler Words (LIMITED for Russian)

English: "basically", "honestly", "actually" — 2–4 per 2000 words in journalistic/casual.
Russian equivalents (journalistic/casual ONLY):
- "в общем-то" — sparingly (1 per 2000 words)
- "собственно говоря" — sparingly (1 per 2000 words)

Russian academic: **Skip entirely.** Fillers are register violations in academic text.

### F8 — Hyphenated Compounds (same rule, Russian equivalents)

No invented hyphenated compounds in journalistic Russian.
Convert "государственно-ориентированный рост" → "рост, направляемый государством" when not a standard dictionary compound.
Permitted: Standard dictionary hyphenated words (социально-экономический, культурно-исторический).

---

## 6. Russian spaCy Model

Primary: `ru_core_news_sm`
- Install: `python -m spacy download ru_core_news_sm`
- Config key: `local_models.spacy_model_ru: "ru_core_news_sm"` ✅

Fallback (if spaCy unavailable): Regex-based tokenization.
Used for: Passive voice detection (AC-4), POS tagging for grammatical analysis.

---

## 7. Perplexity — Skipped for Russian

Source: CLAUDE.md AC-15

GPT-2 perplexity model (`gpt2`) is English-only. Perplexity scores on Russian text are invalid.

Rule:
- `language == 'ru'` → `_skip_perplexity = True`
- Stage 5 skips perplexity computation entirely for Russian
- Score report shows `"N/A (Russian text)"` for all perplexity fields

Config keys:
- `local_models.perplexity_model_ru: null` ✅ (null signals skip)
- `scoring.skip_perplexity_for_russian: true` (required)

Alternative (future): If a Russian perplexity model becomes available (e.g., ruGPT-3), configure via `local_models.perplexity_model_ru` and update AC-15 decision tree.

---

## 8. Russian Passive Voice Baseline

Source: CLAUDE.md AC-4

Russian academic writing norm: **50%+ passive voice** in body text.
This is a domain epistemological norm (P41), not an AI signal in Russian academic context.

Threshold comparison:

| Context | Passive Threshold | Flag condition |
|---------|------------------|----------------|
| English (any register) | 0.20 | Flag if pct > 20% |
| Russian journalistic | 0.30 | Flag if pct > 30% |
| Russian academic-essay | 0.50 | Flag if pct > 50% |
| Russian academic | 0.70 | Flag if pct > 70% |

For Russian academic: If `passive_voice_pct < 0.40` → WARN: "Pipeline may have over-converted to active voice. Russian academic norm is 50%+."

---

## 9. Russian Quote Normalization

Source: CLAUDE.md AC-8

Russian typography standard: guillemets «»
- Opening: «
- Closing: »
- Nested quotes: „" (German-style) or « » (same character)

Method: `normalize_quotes_ru()` in `structural_rewriter.py` and `lexical_enricher.py`

Converts: `"текст"` → `«текст»`
Does not touch: Already-correct «текст»

Config key: None (hardcoded language gate)

---

## 10. Russian Citation Format Summary

Source: GOST Р 7.0.100-2018 + CLAUDE.md AC-2

| Register | Language | Format | Example |
|----------|----------|--------|---------|
| academic | ru | GOST [N] | "по данным Иванова [4], ..." |
| academic | ru | Attribution + [N] | "Как утверждает Петров [7], ..." |
| academic | en | Author-year | "Keohane (1969) argues..." |
| journalistic | ru | Flexible | Attribution or inline |
| any | ru | NEVER | "Иванов (2019)" without [N] ← FAIL |

GOST reference format (Р 7.0.100-2018):
- Russian monograph: "Фамилия И.О. Название / И.О. Фамилия. — Город: Издательство, 2023. — N с."
- English: "Author A.A. Title / A.A. Author. — City: Publisher, 2023. — N p."
- Online resource: must include URL + дата обращения (access date)
