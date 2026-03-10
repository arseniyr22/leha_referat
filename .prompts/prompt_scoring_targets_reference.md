# Задача: Добавить reference/scoring_targets.md в существующий скилл pattern-auditor

## Что нужно сделать

Добавить ОДИН новый файл `reference/scoring_targets.md` в существующий скилл `.claude/skills/pattern-auditor/` и обновить SKILL.md чтобы он ссылался на этот файл.

**НЕ создавать новый скилл.** Это расширение существующего pattern-auditor.

---

## Файл 1: СОЗДАТЬ `reference/scoring_targets.md`

### Назначение

Единый справочник ВСЕХ метрик скоринга для Stage 1 (baseline) и Stage 5 (final scoring). Консолидирует информацию, которая сейчас разбросана по CLAUDE.md (Success Criteria, Stage 5, AC-правила, описания паттернов).

Используется при написании:
- `pipeline/scorer.py` (Stage 5)
- `pipeline/analyzer.py` (Stage 1 — baseline metrics)
- Score report JSON schema
- config.yaml scoring section

### Структура файла

```markdown
# Scoring Targets — Complete Metric Reference

Source of truth: CLAUDE.md. This file consolidates scoring information for quick reference.

---

## Секция 1: Primary Success Criteria

Метрики из CLAUDE.md "Primary success criteria" — в порядке приоритета.

| # | Metric | Formula | Target | Red Line | Hard/Soft | Stage |
|---|--------|---------|--------|----------|-----------|-------|
| 1 | Detection bypass rate | % outputs < 20% AI probability | ≥ 90% | < 70% | informational | Stage 5 (optional probes) |
| 2 | Coherence score | Human evaluator rating (1-5) | ≥ 4/5 | < 3/5 | soft | Manual eval |
| 3 | Naturalness score | Human evaluator rating (1-5) | ≥ 4/5 | < 3/5 | soft | Manual eval |
| 4 | Perplexity lift | output_ppl / input_ppl (GPT-2) | ≥ 1.5x | < 1.2x | soft | Stage 1 (baseline) + Stage 5 (final) |
| 5 | Sentence burstiness | CV of sentence token counts | ≥ 0.45 | < 0.30 | soft | Stage 1 + Stage 5 |
| 6 | Pattern elimination rate | 1 - (output_patterns / input_patterns) | ≥ 85% | < 70% | soft | Stage 1 (baseline) + Stage 5 (rescan) |
| 7 | Paragraph burstiness | CV of paragraph token counts | ≥ 0.50 | < 0.40 | soft | Stage 1 + Stage 5 |
| 8 | Length reduction ratio | output_words / input_words | ≤ 0.90 | > 1.0 | soft | Stage 5 |
| 9 | Announcement opener count | regex count (P9 Part B) | 0 per 500w | ≥ 1 | **hard** | Stage 1 + Stage 5 |
| 10 | Para-ending generalization count | regex + LLM (P24 Part B) | 0 per document | ≥ 1 | **hard** | Stage 1 + Stage 5 |

---

## Секция 2: Pattern-Derived Metrics

Метрики, которые вытекают из конкретных паттернов. Каждая имеет source pattern и формулу.

### 2.1 Hard Fail Metrics (любое нарушение = FAIL)

| Metric | Source | Formula / Detection | Target | Language Gate |
|--------|--------|---------------------|--------|--------------|
| Triplet count | P10 | Noun + verb + adverbial tricolons (regex) | 0 | Both EN/RU |
| Announcement opener count | P9 Part B | ANNOUNCEMENT_OPENERS_EN/RU regex | 0 per 500w | AC-6 for RU |
| Negative parallelism count | P9 Part A | NEGATIVE_PARALLELISM_EN/RU regex | 0 | AC-6 for RU |
| Para-ending generalization count | P24 Part B | PARA_END_GENERALIZATION regex + LLM | 0 | Both |
| Generic positive conclusion count | P24 Part A | GENERIC_POSITIVE_EN/RU regex | 0 | Both |
| Information-first violation count | P31 | P31_EN/RU regex + LLM | 0 | Both |
| Modal hedging on results | P32 | P32_MODAL_WITH_NUMBER regex | 0 sentences with number+modal | AC-6 for RU modals |
| Standalone definition count | P35 | P35_EN/RU regex | 0 | AC-11 |
| Chatbot artifact count | P19 | P19_ARTIFACTS regex | 0 | EN only |
| Knowledge-cutoff disclaimer count | P20 | P20_DISCLAIMERS regex | 0 | EN only |
| Superlative importance opener | P44 | P44/P44_RU regex | 0 | Both |
| Dramatic reveal count | P45 | P45/P45_RU regex | 0 per 2000w | Both |
| Meta-media commentary count | P46 | P46_MARKERS regex | 0 per document | Both |
| Binary future force projection | P47 | P47/P47_RU regex | 0 | Both |
| Binary neither wrap-up | P48 | P48/P48_RU regex | 0 | Both |
| Elegant reversal count | P49 | P49_PATTERNS regex | 0 per document | Both |
| Same-X-That-Also count | P50 | P50/P50_RU regex | 0 | Both |
| Whether-or-just closure | P51 | P51/P51_RU regex | 0 | Both |
| Mechanism attribution run-on | P52 | Sentences with 3+ "that"/"что" clauses | < 0.5 per 300w | Both |
| Participial simultaneity | P53 | P53_PATTERNS regex | 0 | Both |

### 2.2 Threshold Metrics (soft — exceeding = WARNING)

| Metric | Source | Formula | Target | Red Line | Language/Register Gate |
|--------|--------|---------|--------|----------|----------------------|
| Coherence score (auto) | Stage 5 | Embedding-based cosine similarity chain (adjacent paragraphs) | ≥ 0.70 | < 0.50 | Both |
| Paragraph CV | P25 | np.std(para_lengths) / np.mean(para_lengths) | ≥ 0.50 | < 0.40 | Both |
| Section CV | P37 | np.std(section_lengths) / np.mean(section_lengths) | ≥ 0.30 | < 0.20 | Both |
| Conclusion ratio | P37 | conclusion_words / total_body_words | < 0.20 | ≥ 0.20 | Both |
| Sentence burstiness | Success #5 | CV of sentence token counts | ≥ 0.45 | < 0.30 | Both |
| But:However ratio | P33 | but_count / max(however_count, 1) | ≥ 2.0 | < 1.0 | EN only |
| Но:Однако ratio | P33/AC-12 | но_count / max(однако_count, 1) | ≥ 2.0 | < 1.0 | RU only |
| "Also" frequency | P43 | also_count / pages | ≥ 0.08/page | 0 in ≥500w academic | EN: "Also"; RU: "Также" |
| Connector density | P40 | total_connectors / pages | 0.3–0.8/page | > 1.2/page | Both |
| Banned connector count | P29 | Count of Firstly/Secondly/Thirdly/Finally/Additionally | 0 | ≥ 1 (= hard) | AC-6 for RU equivalents |
| Furthermore count | P29 | Count of "Furthermore" | ≤ 1 per document (academic) | ≥ 2 | EN; RU: near-ban "кроме того" |
| Moreover count | P29 | Count of "Moreover" | ≤ 1 per 500w | > 1 per 500w | EN; RU: "более того"/"помимо прочего" |
| Attributive passive count | P5 | Passive constructions without named source | 0 | ≥ 3 | Both |
| Isolated modal density | P38 | Modals without attribution per 300w | < 0.5 | ≥ 1.0 | Both |
| Passive voice % | AC-4 | passive_sentences / total_sentences | See AC-4 table below | — | Language + register dependent |
| Em dash count | P13/F2 | Count of "—" | 0 (EN); ≤3/para (RU) | > 0 EN; >3/para RU | AC-1 |
| Semicolon count | F3 | Count of ";" | 0 (journ); ≤1/500w (acad) | — | Register dependent |
| Colon count (body) | F4 | Colons in body paragraphs | 0 (journ); ≤1/300w (acad) | — | Register dependent |
| Parenthesis count | F4b | Parenthetical expressions | ≤1/300w (acad); 0–1/500w (journ) | — | Register dependent |
| Bold in body text | P14 | Count of **bold** in non-heading text | ≤ 1 | > 3 | Both |
| Emoji count | P17 | Unicode emoji count | 0 (academic/professional) | ≥ 1 | Register dependent |
| Oxford comma count | F1 | ", and" patterns in 3+ item lists | 0 | — | Both |

### 2.3 Injection Metrics (must be PRESENT — absence = WARNING)

| Metric | Source | What to inject | Target count | Register Gate |
|--------|--------|----------------|-------------|---------------|
| Imperfection textures | P30 | Epistemic hedging, asides, fragments | ≥ 1 per 500w | Academic: hedging only; Journalistic: full toolkit |
| Rhetorical questions | P34 | Questions at argument pivots | Domain-dependent (see table) | AC-5 for RU academic math |
| Apostrophe drops | F5 | Missing apostrophes on possessives | 3–5 per 2000w | Journalistic EN only. Skip: academic, RU (AC-7) |
| Grammar errors | F6 | Subject-verb, comma splice, missing article | 2–3 per 2000w | Journalistic EN. Skip: academic, RU academic (AC-7). RU journ: comma only 1–2 |
| Filler words | F7 | basically, honestly, actually | 2–4 per 2000w | Journalistic/essay. Skip: academic. RU: "в общем-то", "собственно говоря" |

---

## Секция 3: Passive Voice Thresholds (AC-4)

Отдельная таблица — наиболее сложная языковая/регистровая зависимость.

| Language | Register | Passive Threshold | Config Key |
|----------|----------|-------------------|------------|
| EN | any | ≤ 0.20 (20%) | discourse.default_passive_threshold |
| RU | academic | ≤ 0.70 (70%) | discourse.academic_ru_passive_threshold |
| RU | academic-essay | ≤ 0.50 (50%) | discourse.academic_essay_ru_passive_threshold |
| RU | journalistic | ≤ 0.30 (30%) | discourse.journalistic_ru_passive_threshold |
| RU | general | ≤ 0.20 (20%) | discourse.default_passive_threshold |

---

## Секция 4: Citation Density by Domain (P42)

| Domain | Citations per 20 pages | Config key path |
|--------|------------------------|-----------------|
| law | 50+ | scoring.citation_baselines.law |
| linguistics | ~10 (8–12) | scoring.citation_baselines.linguistics |
| social_science | 5–10 | scoring.citation_baselines.social_science |
| management | 5–15 | scoring.citation_baselines.management |
| economics | 5–15 | scoring.citation_baselines.economics |
| it_cs | 2–8 | scoring.citation_baselines.it_cs |
| math | 0–3 | scoring.citation_baselines.math |

**Pass condition:** lo ≤ density ≤ hi × 1.5 (допуск +50% сверху)

---

## Секция 5: Rhetorical Question Density by Domain (P34)

| Domain | Questions per ~5000w text | Per-unit rate (if applicable) |
|--------|--------------------------|-------------------------------|
| social_science | 4–12 | — |
| management | 1–3 | — |
| it_cs | 0–1 | — |
| math | 0 | — |
| journalistic | 7–10 | 1 per 500–750w |
| general | 1–3 | — |

---

## Секция 6: Connector Density Targets per Page (P40)

250 words ≈ 1 page.

| Connector type | Target per page | Examples |
|----------------|----------------|----------|
| Informal contrast (But/Yet/Though) | 0.15–0.40 | But, Yet, Though |
| Formal contrast (However) | 0.05–0.20 | However |
| Informal addition (Also) | 0.10–0.25 | Also |
| Logical consequence (Thus/Therefore) | 0.03–0.10 | Thus, Therefore, Hence |
| Formal addition (Moreover) | 0–0.05 | Moreover |
| Furthermore | 0–0.01 | Furthermore |
| Additionally | 0 (absolute ban) | Additionally |

---

## Секция 7: Language Gates for Metrics

Какие метрики пропускаются или заменяются для русского текста.

| Metric | EN behavior | RU behavior | AC rule |
|--------|-------------|-------------|---------|
| Perplexity lift | GPT-2 computation | **SKIP** — show "N/A (Russian text)" | AC-15 |
| But:However ratio | Compute and report | **REPLACE** with Но:Однако ratio | AC-12 |
| Em dash count | Target: 0 | **Conservative**: reduce >3/para only | AC-1 |
| Apostrophe drops (F5) | 3–5 per 2000w (journ) | **SKIP entirely** | AC-7 |
| Grammar errors (F6) | 2–3 per 2000w (journ) | Academic: SKIP. Journ: comma only 1–2 | AC-7 |
| Quote format | Straight quotes " | Guillemets «» | AC-8 |
| P7 banlist | English banlist | Russian banlist (p7_russian) | AC-6/AC-14 |
| P29 connectors | English ban/rate lists | Russian equivalents (p29_russian) | AC-6 |
| Passive threshold | 20% default | 70% academic, 50% essay, 30% journ | AC-4 |

---

## Секция 8: Score Report JSON Schema

Формат выходного score_report.json для Stage 5.

```json
{
  "metadata": {
    "input_word_count": 2500,
    "output_word_count": 2200,
    "language": "en",
    "register": "journalistic",
    "domain": "economics",
    "timestamp": "2026-03-10T14:30:00Z"
  },
  "primary_criteria": {
    "perplexity_lift": {"input_ppl": 45.2, "output_ppl": 72.8, "ratio": 1.61, "target": 1.5, "pass": true},
    "sentence_burstiness": {"cv": 0.52, "target": 0.45, "pass": true},
    "pattern_elimination_rate": {"input_count": 23, "output_count": 2, "rate": 0.913, "target": 0.85, "pass": true},
    "paragraph_burstiness": {"cv": 0.58, "target": 0.50, "pass": true},
    "length_reduction": {"ratio": 0.88, "target": 0.90, "pass": true},
    "announcement_openers": {"count": 0, "target": 0, "pass": true},
    "para_ending_generalizations": {"count": 0, "target": 0, "pass": true}
  },
  "hard_fail_metrics": {
    "triplet_count": {"noun": 0, "verb": 0, "adverb": 0, "total": 0, "pass": true},
    "p9_negative_parallelism": {"count": 0, "pass": true},
    "p19_chatbot_artifacts": {"count": 0, "pass": true},
    "p20_cutoff_disclaimers": {"count": 0, "pass": true},
    "p24_generic_positive": {"count": 0, "pass": true},
    "p31_information_first": {"count": 0, "pass": true},
    "p32_modal_on_results": {"count": 0, "pass": true},
    "p35_standalone_definitions": {"count": 0, "pass": true},
    "p44_superlative_opener": {"count": 0, "pass": true},
    "p45_dramatic_reveal": {"count": 0, "pass": true},
    "p46_meta_media": {"count": 0, "pass": true},
    "p47_binary_future": {"count": 0, "pass": true},
    "p48_binary_neither": {"count": 0, "pass": true},
    "p49_elegant_reversal": {"count": 0, "pass": true},
    "p50_same_x_that_also": {"count": 0, "pass": true},
    "p51_whether_or_just": {"count": 0, "pass": true},
    "p52_mechanism_runon": {"count": 0, "density_per_300w": 0.0, "target": 0.5, "pass": true},
    "p53_participial_simultaneity": {"count": 0, "pass": true}
  },
  "threshold_metrics": {
    "coherence_auto": {"value": 0.82, "target": 0.70, "red_line": 0.50, "method": "embedding_cosine_similarity", "pass": true},
    "paragraph_cv": {"value": 0.58, "target": 0.50, "red_line": 0.40, "pass": true},
    "section_cv": {"value": 0.35, "target": 0.30, "red_line": 0.20, "pass": true},
    "conclusion_ratio": {"value": 0.12, "target_max": 0.20, "pass": true},
    "but_however_ratio": {"but": 8, "however": 3, "ratio": 2.67, "target": 2.0, "pass": true},
    "also_frequency": {"count": 5, "per_page": 0.18, "target": 0.08, "pass": true},
    "connector_density": {"per_page": 0.55, "target_range": [0.3, 0.8], "pass": true},
    "banned_connectors": {"count": 0, "pass": true},
    "furthermore_count": {"count": 0, "target_max": 1, "scope": "per_document_academic", "pass": true},
    "moreover_count": {"count": 1, "target_max_per_500w": 1, "pass": true},
    "attributive_passive": {"count": 0, "target": 0, "pass": true},
    "isolated_modal_density": {"per_300w": 0.3, "target": 0.5, "pass": true},
    "passive_voice_pct": {"value": 0.15, "threshold": 0.20, "pass": true},
    "em_dash_count": {"count": 0, "target": 0, "pass": true},
    "semicolon_count": {"count": 0, "target": 0, "pass": true},
    "colon_body_count": {"count": 0, "target": 0, "pass": true},
    "parenthesis_count": {"count": 2, "target": 4, "pass": true},
    "bold_body_count": {"count": 0, "target": 1, "pass": true},
    "emoji_count": {"count": 0, "target": 0, "pass": true},
    "oxford_comma_count": {"count": 0, "target": 0, "pass": true}
  },
  "injection_metrics": {
    "imperfection_textures": {"epistemic_hedges": 4, "parenthetical_asides": 2, "sufficient": true},
    "rhetorical_questions": {"count": 2, "domain_range": [1, 3], "pass": true},
    "apostrophe_drops": {"count": 4, "target_range": [3, 5], "pass": true},
    "grammar_errors": {"count": 2, "target_range": [2, 3], "pass": true},
    "filler_words": {"count": 3, "target_range": [2, 4], "pass": true}
  },
  "domain_specific": {
    "citation_density": {"count": 12, "per_20_pages": 8.5, "domain": "economics", "baseline": [5, 15], "pass": true}
  },
  "summary": {
    "hard_fails": 0,
    "warnings": 1,
    "total_metrics": 42,
    "overall_pass": true,
    "notes": ["F3 semicolons: 1 instance (within academic threshold)"]
  }
}
```

**Правило для RU score report:**
- Поле `perplexity_lift` → `{"status": "N/A", "reason": "Russian text (AC-15)"}`
- Поле `but_however_ratio` → заменяется на `no_odnako_ratio` с теми же полями
- Поля `apostrophe_drops`, `grammar_errors` → зависят от register (см. Секция 7)

---

## Секция 9: Visualization Count (Phase 0 only)

Считается ТОЛЬКО для текстов, прошедших Phase 0 (генерация). Не считается в humanization mode.

| stream_id | Minimum tables+figures |
|-----------|----------------------|
| vkr (bachelor) | 5–10 |
| vkr (master) | 8–15 |
| coursework | 3–6 |
| research | 3–8 |
| abstract_paper | 1–3 (desirable) |
| text | Context-dependent |
| essay | Optional |
| composition | 0 |

Score report field:
```json
"visualization_count": {
  "tables": 4,
  "figures": 3,
  "total": 7,
  "minimum_required": 5,
  "stream_id": "vkr",
  "level": "bachelor",
  "pass": true
}
```

---

## Секция 10: Metric → Pattern → Worker Traceability

Для каждой метрики: откуда она, кто её создаёт, кто её проверяет.

| Metric | Pattern | Measured by | Created/fixed by | Verified by |
|--------|---------|-------------|------------------|-------------|
| Perplexity lift | — | Stage 1 + Stage 5 (GPT-2) | All stages collectively | Stage 5 |
| Coherence (auto) | — | Stage 5 (embedding cosine similarity) | All stages collectively | Stage 5 |
| Sentence burstiness | — | Stage 1 + Stage 5 (numpy) | hm4_rhythm_shaper | Stage 5 |
| Paragraph CV | P25 | Stage 1 + Stage 5 (numpy) | hm2_scaffold_breaker + hm4_rhythm_shaper | Stage 5 |
| Section CV | P37 | Stage 1 + Stage 5 (numpy) | hm4_rhythm_shaper | Stage 5 |
| Pattern elimination % | All | Stage 1 (baseline) + Stage 5 (rescan) | All HM workers | Stage 5 |
| Length reduction | — | Stage 5 (word count) | All stages collectively | Stage 5 |
| Triplet count | P10 | Stage 1 + Stage 5 (regex) | hm2_triplet_buster | Stage 5 |
| Announcement openers | P9-B | Stage 1 + Stage 5 (regex) | hm2_scaffold_breaker | Stage 5 |
| But:However ratio | P33 | Stage 1 + Stage 5 (count) | hm2_connector_tuner | Stage 5 |
| Also frequency | P43 | Stage 1 + Stage 5 (count) | hm2_connector_tuner | Stage 5 |
| Connector density | P40 | Stage 5 (count/pages) | hm2_connector_tuner | Stage 5 |
| Citation density | P42 | Stage 5 (count/pages) | hm3_attribution_fixer | Stage 5 |
| Passive voice % | AC-4 | Stage 5 (spaCy POS) | hm4_soul_injector | Stage 5 |
| Imperfection textures | P30 | Stage 5 (heuristic) | hm4_soul_injector | Stage 5 |
| Em dash count | P13/F2 | Stage 5 (regex) | hm2_format_cleaner | Stage 5 |
```

---

## Файл 2: ОБНОВИТЬ `SKILL.md`

### Изменение 1: Добавить строку в таблицу Секции 5

В таблицу reference файлов (Секция 5: Reference файлы) добавить строку:

```
| `reference/scoring_targets.md` | Все метрики скоринга: targets, red lines, формулы, JSON schema, domain/language gates | BUILD — targets при написании scorer; AUDIT — pass/fail критерии |
```

Добавить ПОСЛЕ строки с `pattern_interactions.md`.

### Изменение 2: Обновить описание AUDIT mode

В Секции 3 (Пошаговый процесс), Режим AUDIT, Шаг 3.3 — добавить ссылку:

Текущий текст Шага 3.3:
```
**Шаг 3.3** — Дополнительно вычислить структурные метрики:
```

Заменить на:
```
**Шаг 3.3** — Дополнительно вычислить структурные метрики (targets и формулы из `reference/scoring_targets.md`):
```

### Изменение 3: Обновить описание BUILD mode

В Секции 3, Режим BUILD, после Шага 3.6 добавить:

```
**Шаг 3.7** — Если worker участвует в скоринге (scorer.py, analyzer.py), загрузить из `reference/scoring_targets.md`: metric targets, JSON schema fields, pass/fail conditions.
```

И перенумеровать текущий Шаг 3.7 (вывод отчёта) → **Шаг 3.8**.

---

## Правила создания файла

1. **НЕ дублировать описания паттернов** — scoring_targets.md содержит ТОЛЬКО метрики, targets и формулы. За описаниями паттернов → `patterns_by_category.md`. За regex детекции → `detection_patterns.md`.

2. **Ссылаться на source pattern** — каждая метрика указывает номер паттерна (P25, P33, etc.) для трассировки.

3. **Ссылаться на AC-правила** — каждый language/register gate указывает номер AC-правила.

4. **JSON schema должна быть валидной** — скопировать пример и проверить что парсится.

5. **Числовые targets берутся ТОЛЬКО из CLAUDE.md** — не выдумывать. Если target не указан явно в CLAUDE.md, поставить "—" и пометить "(not specified in CLAUDE.md)".

---

## Верификация после создания

1. Проверить что `scoring_targets.md` создан в `reference/` папке
2. Проверить что SKILL.md обновлён (таблица Секции 5 + Шаги 3.3 и 3.7/3.8)
3. Проверить что ВСЕ 10 Success Criteria из CLAUDE.md присутствуют в Секции 1
4. Проверить что ВСЕ метрики из Stage 5 box в CLAUDE.md (строки 476–489) присутствуют
5. Проверить что passive voice thresholds из AC-4 (4 строки: EN default, RU academic, RU essay, RU journalistic) все присутствуют
6. Проверить что citation density baselines из P42 (7 доменов) все присутствуют
7. Проверить что JSON schema парсится без ошибок
8. Проверить что visualization minimums из БЛОК 16.2 (8 stream_id строк) все присутствуют
9. Проверить что Language Gates таблица покрывает все AC-правила влияющие на скоринг: AC-1, AC-4, AC-6, AC-7, AC-8, AC-12, AC-14, AC-15
