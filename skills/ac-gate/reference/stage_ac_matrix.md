# Stage × AC Rule Matrix

Each cell contains the specific function, parameter, or prompt variable to verify for that AC rule in that pipeline component.
`—` = not applicable. `✓` = applies (see details column).

## Matrix

| AC Rule | Priority | Stage 1 `analyzer.py` | Stage 2 `structural_rewriter.py` | Stage 3 `lexical_enricher.py` | Stage 4 `discourse_shaper.py` | Stage 5 `scorer.py` | Phase 0A `source_finder.py` | Phase 0B `generator.py` | `config.yaml` | `prompts/` |
|---------|----------|----------------------|----------------------------------|-------------------------------|-------------------------------|---------------------|----------------------------|------------------------|---------------|------------|
| **AC-1** | HIGH | — | `reduce_em_dashes_ru()` + `if language == 'ru'` gate | — | — | `em_dash_count` metric in score report | — | — | `structural.em_dash_ru_max_per_paragraph: 3` | Stage 2 prompt: `{{LANGUAGE}}` |
| **AC-2** | HIGH | — | — | `citation_format` gate: GOST [N] for RU+academic | `citation_format` gate enforced | GOST [N] validation; no author-year in RU+academic | GOST [N] formatting for all sources | GOST [N] in generated text | — | Stage 3+4 prompts: `{{LANGUAGE}}` + `{{REGISTER}}` |
| **AC-3** | HIGH | — | `protected_sections` list; P26/Op 11 paragraph-level only for academic | — | — | `section_order_validation` in score report | — | GOST section generation order: Введение → Глава N → Заключение → Список | — | Stage 2 prompt: no section reordering instruction |
| **AC-4** | HIGH | — | — | — | `passive_threshold` from config; `if language == 'ru' and register == 'academic': threshold = 0.70` | `passive_voice_pct` metric vs correct threshold | — | — | `discourse.academic_ru_passive_threshold: 0.70` | Stage 4 prompt: `{{LANGUAGE}}` + `{{REGISTER}}`; no passive conversion without gate |
| **AC-5** | HIGH | — | — | — | Op 8 skip gate: `if (language == 'ru' and register == 'academic') or domain == 'math': skip Op 8` | — | — | No metaphors in Russian academic generation | — | Stage 4 `voice_injection.md`: `{{LANGUAGE}}` + `{{REGISTER}}`; skip metaphors for RU+academic |
| **AC-6** | HIGH | `_apply_russian_patterns(text, config)` for language='ru'; uses `p7_russian` + `p29_russian` | `_apply_russian_patterns()` called when language='ru' | `_apply_russian_patterns()` called when language='ru' | `_apply_russian_patterns()` called when language='ru' | Russian pattern rescan uses `p7_russian` block | — | `{{LANGUAGE}}` in megaprompt | `p7_russian` block ✅; `p29_russian` block ✅ | ALL prompts stages 2–4: `{{LANGUAGE}}` variable present |
| **AC-7** | MED-HIGH | — | — | — | `if register == 'academic': skip F5 and F6 entirely`; `if language == 'ru': skip F5, F6 = comma only` | — | — | — | `p30_mode.academic: "limited"` ✅ | Stage 4 `voice_injection.md` + `audit.md`: no F5/F6 for academic; `{{REGISTER}}` present |
| **AC-8** | MEDIUM | — | `normalize_quotes_ru()` for language='ru'; `normalize_quotes()` for language='en'; language gate present | `normalize_quotes_ru()` called for language='ru' | — | — | — | — | — | — |
| **AC-9** | MED-HIGH | — | P15 list-to-prose: `protected_list_patterns = [numbered sections, bibliography entries, TOC items]`; only convert content bullets | — | — | — | — | — | — | Stage 2 `structural_rewrite.md`: no TOC/bibliography conversion |
| **AC-10** | MEDIUM | — | Op 11: `assert register in ['academic', 'academic-essay', 'journalistic', 'general']`; for academic: paragraph level only | — | — | — | — | — | — | Stage 2 prompt: `{{REGISTER}}`; no macro-structure reordering for academic |
| **AC-11** | LOW | — | — | `if language == 'en': convert "X is defined as Y"` form; `if language == 'ru': convert "Под X понимается Y"` form | — | `standalone_definition_count` metric | — | — | — | Stage 3 `lexical_enrichment.md`: `{{LANGUAGE}}` for definition form |
| **AC-12** | LOW | — | — | — | — | `if language == 'ru': but_however_ratio = None; report no_odnako_ratio`; `if language == 'en': report but_however_ratio` | — | — | `p29_russian.target_no_odnako_ratio: 2.0` ✅ | — |
| **AC-13** | LOW | — | — | — | — | Citation density metric (per-page) enforced independently from source count minimum | Source count minimum enforced (from `generator.source_minimums`) | — | `citation_density_by_domain` ✅; `generator.source_minimums` ✅ | — |
| **AC-14** | LOW | Pattern scan includes Russian P7 phrases from `p7_russian` config | — | Russian P7 banlist application via `_apply_russian_patterns()` using `p7_russian` | — | Russian P7 rescan in pattern elimination metric | — | `{{LANGUAGE}}` in megaprompt guards Russian P7 generation | `p7_russian.absolute_ban` ✅ (17); `importance_framing_ban` ✅ (7); `announcement_ban` ✅ (8) | Stage 3 `lexical_enrichment.md`: `{{LANGUAGE}}`; Russian P7 banlist injected |
| **AC-15** | LOW | `if language == 'ru': _skip_perplexity = True`; baseline perplexity not computed for Russian | — | — | — | `if language == 'ru': perplexity = "N/A (Russian text)"`; skip perplexity lift computation | — | — | `local_models.perplexity_model_ru: null` ✅ | — |

---

## Quick Reference: By Stage

### Stage 1 (`analyzer.py`)
Applicable AC rules: **AC-6, AC-14, AC-15**

| Check | What to verify |
|-------|----------------|
| AC-6 | `_apply_russian_patterns()` method present; called when `language == 'ru'` |
| AC-14 | Pattern scanner references `p7_russian` config blocks, not just English p7 |
| AC-15 | `if language == 'ru': skip perplexity` logic present; baseline returns N/A for Russian |

---

### Stage 2 (`structural_rewriter.py`)
Applicable AC rules: **AC-1, AC-3, AC-6, AC-8, AC-9, AC-10**

| Check | What to verify |
|-------|----------------|
| AC-1 | `reduce_em_dashes_ru()` exists; `if language == 'ru'` gate before any em dash removal |
| AC-3 | `protected_sections` list defined; Op 11 scope = paragraph-level only for academic |
| AC-6 | `_apply_russian_patterns()` called for language='ru' |
| AC-8 | `normalize_quotes_ru()` exists; language gate before quote normalization |
| AC-9 | Protected list before P15 conversion; TOC/bibliography patterns in exclusion list |
| AC-10 | `assert register in [...]` before Op 11; scope restriction for academic |

---

### Stage 3 (`lexical_enricher.py`)
Applicable AC rules: **AC-2, AC-6, AC-8, AC-11, AC-14**

| Check | What to verify |
|-------|----------------|
| AC-2 | `citation_format` parameter; `if language == 'ru' and register == 'academic': GOST` |
| AC-6 | `_apply_russian_patterns()` called for language='ru' |
| AC-8 | `normalize_quotes_ru()` called for language='ru' |
| AC-11 | Language-conditional definition form detection |
| AC-14 | `p7_russian` blocks used in pattern scan |

---

### Stage 4 (`discourse_shaper.py`)
Applicable AC rules: **AC-2, AC-4, AC-5, AC-6, AC-7**

| Check | What to verify |
|-------|----------------|
| AC-2 | Citation format gate enforced in attribution generation |
| AC-4 | `passive_threshold` read from config; language+register gate present |
| AC-5 | Op 8 skip: `if (language == 'ru' and register == 'academic') or domain == 'math'` |
| AC-6 | `_apply_russian_patterns()` called; `{{LANGUAGE}}` in prompt templates |
| AC-7 | F5 skip: `if language == 'ru' or register == 'academic'`; F6 skip: `if register == 'academic'` |

---

### Stage 5 (`scorer.py`)
Applicable AC rules: **AC-1, AC-3, AC-6, AC-12, AC-13, AC-14, AC-15**

| Check | What to verify |
|-------|----------------|
| AC-1 | `em_dash_count` in score report; copular dash detection for Russian |
| AC-3 | `section_order_validation` checks GOST order |
| AC-6 | Russian pattern rescan uses `p7_russian` + `p29_russian` blocks |
| AC-12 | `if language == 'ru': but_however_ratio = None; report no_odnako_ratio` |
| AC-13 | Both `citation_density` and `source_count` metrics present independently |
| AC-14 | Pattern elimination rate computed against Russian P7 banlist for Russian text |
| AC-15 | `if language == 'ru': perplexity = "N/A (Russian text)"` |

---

### Phase 0A (`source_finder.py`)
Applicable AC rules: **AC-2, AC-13**

| Check | What to verify |
|-------|----------------|
| AC-2 | All sources formatted in GOST [N] style for Russian academic |
| AC-13 | Source count minimum enforced per stream (from `generator.source_minimums`) |

---

### Phase 0B (`generator.py`)
Applicable AC rules: **AC-3, AC-5, AC-6**

| Check | What to verify |
|-------|----------------|
| AC-3 | Section generation order follows GOST: Введение → Глава N → Заключение → Список |
| AC-5 | No metaphor generation for language='ru' AND register='academic' |
| AC-6 | `{{LANGUAGE}}` injected into megaprompt; Russian P7 banlist in megaprompt context |

---

### `config.yaml`
Required AC-relevant parameters:

| Parameter | AC Rule | Current Status |
|-----------|---------|---------------|
| `discourse.academic_ru_passive_threshold: 0.70` | AC-4 | ✅ exists |
| `p7_russian.absolute_ban` | AC-6, AC-14 | ✅ exists (17 phrases) |
| `p7_russian.importance_framing_ban` | AC-6, AC-14 | ✅ exists (7 phrases) |
| `p7_russian.announcement_ban` | AC-6, AC-14 | ✅ exists (8 phrases) |
| `p29_russian.absolute_ban` | AC-6 | ✅ exists |
| `p29_russian.near_ban_max_per_doc` | AC-6 | ✅ exists |
| `p29_russian.rate_limited_per_500w` | AC-6 | ✅ exists |
| `p29_russian.target_no_odnako_ratio: 2.0` | AC-12 | ✅ exists |
| `p30_mode.academic: "limited"` | AC-7 | ✅ exists |
| `local_models.perplexity_model_ru: null` | AC-15 | ✅ exists |
| `local_models.spacy_model_ru: "ru_core_news_sm"` | AC-6 | ✅ exists |
| `structural.em_dash_ru_max_per_paragraph: 3` | AC-1 | ✅ exists |
| `scoring.skip_perplexity_for_russian: true` | AC-15 | ✅ exists |
| `scoring.ru_no_odnako_ratio_target: 2.0` | AC-12 | ✅ exists |
| `discourse.default_passive_threshold: 0.20` | AC-4 | ✅ exists |
| `discourse.academic_essay_ru_passive_threshold: 0.50` | AC-4 | ✅ exists |
| `discourse.journalistic_ru_passive_threshold: 0.30` | AC-4 | ✅ exists |
