# AC Rules Full Reference (AC-1 — AC-15)

Source: CLAUDE.md — "Anti-Conflict Rules (AC-1 through AC-15)"
These rules resolve conflicts between `prompts/academic_megaprompt.md` (Russian-centric) and the English-centric pipeline (Stages 1–5).

---

## AC-1 — Em Dash: Language Gate

**Priority: HIGH**

**Conflict:** `reduce_em_dashes()` in `structural_rewriter.py` applies unconditionally. Russian grammar requires em dashes in copular sentences ("Москва — столица России"), definitions, appositives.

**Decision Tree:**
```
IF language == 'en':
    target = 0 em dashes
    method = reduce_em_dashes()

ELIF language == 'ru':
    target = preserve grammatically required em dashes
    rule = reduce AI-overuse only (>3 per paragraph)
    method = reduce_em_dashes_ru()
    preserve:
        - [Сущ.] — [Сущ./Прил.] (copular: "Москва — столица России")
        - [Term] — это [definition]
        - [Appositive] — [qualifier]
    remove (excess):
        - em dashes beyond 3 per paragraph
        - em dashes in mid-sentence asides where comma/parens would work
```

**Affected Stages:** Stage 2 (`structural_rewriter.py`), Stage 5 (`scorer.py` — em_dash_count metric)

**Config Parameter:** `structural.em_dash_ru_max_per_paragraph: 3`

**BUILD check:** `reduce_em_dashes_ru()` method exists in structural_rewriter.py + `if language == 'ru'` gate before `reduce_em_dashes()` call

**RUNTIME check:** Count em dashes per paragraph; flag paragraphs with >3 that lack copular context; flag 0 em dashes in Russian text with copular constructions

---

## AC-2 — Attribution Format: GOST [N] vs Author-Year

**Priority: HIGH**

**Conflict:** Stage 3 lexical prompt instructs author-year format ("Keohane (1969) suggests..."). GOST 7.32-2017 requires numeric [N] for Russian academic texts.

**Decision Tree:**
```
IF language == 'ru' AND register == 'academic':
    citation_format = 'GOST'
    NEVER convert [N] to author-year
    NEVER produce "Петров (2019)" format
    Correct: "Как утверждает [Автор] [N], ..."
    Correct: "по мнению Иванова [4], ..."
    Incorrect: "Петров (2019) утверждает" ← FAIL
    Incorrect: "Петров (2019) [4]" ← FAIL (author-year is redundant even with [N])

ELIF language == 'ru' AND register != 'academic':
    citation_format = 'AUTHOR_YEAR' or flexible
    [N] optional but acceptable

ELIF language == 'en':
    citation_format = 'AUTHOR_YEAR'
    Format: "Keohane (1969) suggests..."
    [N] acceptable in GOST contexts only
```

**Affected Stages:** Stage 3 (`lexical_enricher.py`), Stage 4 (`discourse_shaper.py`), Stage 5 (validation)

**Config Parameter:** No config key — hardcoded gate on `language + register` combination

**BUILD check:** `citation_format` parameter/variable exists in lexical_enricher.py and discourse_shaper.py; conditional logic present for language='ru' + register='academic'

**RUNTIME check:** Regex `[А-Я][а-я]+\s*\(\d{4}\)` for author-year patterns in Russian text; any match in academic register = FAIL

---

## AC-3 — GOST Macro-Structure Preservation

**Priority: HIGH**

**Conflict:** Stage 2 idea-order disruptor (P26/Op 11) might reorder GOST section markers (Введение, Заключение, Список литературы, Глава N).

**Decision Tree:**
```
protected_sections_ru = [
    'title_page', 'annotation', 'toc', 'введение',
    'глава 1', 'глава 2', 'глава 3', 'глава 4',
    'заключение', 'список литературы',
    'список использованных источников', 'приложение'
]
protected_sections_en = [
    'title_page', 'annotation', 'toc', 'introduction',
    'chapter 1', 'chapter 2', 'chapter 3', 'chapter 4',
    'conclusion', 'references', 'bibliography', 'appendix'
]

IF register == 'academic':
    P26 (Op 11) applies ONLY at paragraph level (within sections)
    NEVER reorder section markers from protected_sections list
    NEVER move: title_page, annotation, toc, introduction,
                chapters (by number), conclusion, references

ELSE (journalistic, essay, general):
    P26 applies at section + paragraph level
    No protected sections
```

**Affected Stages:** Stage 2 (`structural_rewriter.py`), Phase 0B (`generator.py`), Stage 5 (section order validation)

**Config Parameter:** No config key — hardcoded protected_sections list in structural_rewriter.py

**BUILD check:** `protected_sections` list exists in structural_rewriter.py; Op 11 scope restriction for academic register

**RUNTIME check:** Verify section order: Введение/Introduction appears before Глава 1/Chapter 1; Заключение/Conclusion appears after last chapter; Список литературы/References is last

---

## AC-4 — Passive Voice Threshold for Russian Academic

**Priority: HIGH**

**Conflict:** Stage 4 flags >20% passive voice as AI signal. Russian academic text uses 50%+ passive as domain norm.

**Decision Tree:**
```
IF language == 'ru' AND register == 'academic':
    passive_threshold = 0.70  # from config: discourse.academic_ru_passive_threshold
    Flag only if passive_voice_pct > 0.70
    Do NOT flag passive voice below 70%
    Reason: Russian academic domain norm is 50%+

ELIF language == 'ru' AND register == 'academic-essay':
    passive_threshold = 0.50  # moderate

ELSE (English, or Russian journalistic/general):
    passive_threshold = 0.20  # default
    Flag if passive_voice_pct > 0.20
```

**Affected Stages:** Stage 4 (`discourse_shaper.py`), Stage 5 (`scorer.py` — passive_voice_pct metric)

**Config Parameter:** `discourse.academic_ru_passive_threshold: 0.70` ✅ exists in config.yaml

**BUILD check:** Threshold read from `config.yaml: discourse.academic_ru_passive_threshold` (not hardcoded); language + register gate present before passive voice flagging

**RUNTIME check:** `passive_voice_pct` computed; compared against correct threshold for language+register combination; <40% in RU+academic → WARN (pipeline may have over-converted to active)

---

## AC-5 — Figurative Language in Russian Academic

**Priority: HIGH**

**Conflict:** Stage 4 Pass A Op 8 injects metaphors/analogies (1-2 per section). Russian VKR/coursework/research prohibits metaphors.

**Decision Tree:**
```
IF language == 'ru' AND register == 'academic':
    SKIP Op 8 entirely
    Reason: Russian VKR/coursework/research = zero metaphors (domain norm)

ELIF domain == 'math':
    SKIP Op 8 entirely
    Reason: Math does not use figurative language regardless of language/register

ELIF language == 'ru' AND register in ['journalistic', 'essay', 'general']:
    APPLY Op 8 normally (1-2 metaphors per section)
    Russian journalistic allows metaphors

ELIF language == 'en':
    APPLY Op 8 normally (1-2 metaphors per section)
    Exception: math domain (see above)
```

**Affected Stages:** Stage 4 (`discourse_shaper.py`)

**Config Parameter:** No config key — hardcoded gate on language + register + domain

**BUILD check:** Op 8 skip condition `if language == 'ru' and register == 'academic'` or `if domain == 'math'` present in discourse_shaper.py

**RUNTIME check:** Detect metaphor markers in Russian academic text; presence → WARN (Op 8 gate may have failed); Russian metaphor markers: `подобно`, `словно`, `как будто`, `своего рода`, `является своеобразным`, `напоминает`, `сродни`, `можно сравнить с`, `аналогично тому как`

---

## AC-6 — English-Only Regex for Russian Text

**Priority: HIGH**

**Conflict:** All regex patterns (announcement openers, P29 connectors, P7 vocab, P28 substitutions) are English-only. Russian AI patterns go undetected without Russian-specific handling.

**Decision Tree:**
```
IF language == 'ru':
    APPLY _apply_russian_patterns(text, config) using:
        - p7_russian config block (absolute_ban, importance_framing_ban, announcement_ban)
        - p29_russian config block (absolute_ban, near_ban, rate_limited, target ratio)
    Prompt templates: include {{LANGUAGE}} variable
    LLM handles Russian patterns not covered by regex

ELIF language == 'en':
    APPLY standard English regex patterns from p7 and p29 config blocks
    English announcement patterns, connector monotony, vocabulary substitution
```

**Affected Stages:** ALL stages (Stage 1–5), Phase 0B (`generator.py`)

**Config Parameters:**
- `p7_russian.absolute_ban` ✅ (17 phrases)
- `p7_russian.importance_framing_ban` ✅ (7 phrases)
- `p7_russian.announcement_ban` ✅ (8 phrases)
- `p29_russian.absolute_ban` ✅
- `p29_russian.near_ban_max_per_doc` ✅
- `p29_russian.rate_limited_per_500w` ✅
- `p29_russian.target_no_odnako_ratio: 2.0` ✅

**BUILD check:** `_apply_russian_patterns()` method exists in all Stage files; `{{LANGUAGE}}` variable present in all Stage 2–4 prompt templates; p7_russian + p29_russian blocks exist in config.yaml

**RUNTIME check:** Scan text for all phrases in p7_russian banlist; scan for p29_russian absolute_ban connectors; any match → FAIL

---

## AC-7 — F5/F6 in Russian/Academic Text

**Priority: MEDIUM-HIGH**

**Conflict:** Pass B audit (Stage 4) injects apostrophe drops (F5) and grammar errors (F6) as "imperfection texture." F5 is inapplicable to Russian (apostrophes not used). F6 errors in Russian academic are too visible and break credibility.

**Decision Tree:**
```
IF register == 'academic' (ANY language):
    SKIP F5 entirely
    SKIP F6 entirely
    Reason: academic register requires grammatical perfection

ELIF language == 'ru' (any non-academic register):
    SKIP F5 entirely (apostrophes don't exist in Russian)
    F6 = comma placement variation ONLY (1-2 instances)
    NOT: subject-verb agreement errors, article errors

ELIF language == 'en' AND register == 'journalistic':
    APPLY F5 (3-5 apostrophe drops on proper noun possessives)
    APPLY F6 (2-3 grammar errors of types a-c)

ELIF language == 'en' AND register in ['essay', 'general', 'casual']:
    APPLY F5 + F6 per P30 rules
```

**Affected Stages:** Stage 4 (`discourse_shaper.py`)

**Config Parameter:** `p30_mode.academic: "limited"` ✅ (implies F5/F6 skip for academic)

**BUILD check:** F5 injection function has `if language == 'ru': skip` gate; F6 injection function has `if register == 'academic': skip` gate

**RUNTIME check:** Detect apostrophe drops in Russian text (inapplicable so any = FAIL if academic); detect deliberate grammar errors in academic text (any F6-type error = FAIL)

---

## AC-8 — Quote Normalization for Russian

**Priority: MEDIUM**

**Conflict:** Stage 2/3 normalizes quotes to ASCII straight quotes `"`. Russian typography uses guillemets «».

**Decision Tree:**
```
IF language == 'en':
    normalize to ASCII straight quotes "
    method = normalize_quotes()

ELIF language == 'ru':
    normalize to guillemets «»
    method = normalize_quotes_ru()
    Convert: " → «» (opening/closing context)
    Do NOT convert: «» → " (they are already correct)
```

**Affected Stages:** Stage 2 (`structural_rewriter.py`), Stage 3 (`lexical_enricher.py`)

**Config Parameter:** No config key — hardcoded gate on language

**BUILD check:** `normalize_quotes_ru()` method exists; language gate present before quote normalization

**RUNTIME check:** Count ASCII `"` characters in Russian text; >3 per document → WARN

---

## AC-9 — List-to-Prose Scope

**Priority: MEDIUM-HIGH**

**Conflict:** Stage 2 list-to-prose converter (P15) must not convert GOST section structure items.

**Decision Tree:**
```
NEVER convert to prose:
    - Numbered section markers: "1.1 Название", "Глава 2", "Chapter 3"
    - Bibliography entries: any item in reference list section
    - TOC items: any item in Оглавление/Table of Contents section
    - Numbered lists in technical context (algorithm steps, legal articles)

ONLY convert to prose:
    - Content bullets with "**Header:** Content body text" format in body paragraphs
    - Inline-header vertical lists (Pattern P15) in non-TOC, non-bibliography context
```

**Affected Stages:** Stage 2 (`structural_rewriter.py`)

**Config Parameter:** No config key — hardcoded protected patterns list

**BUILD check:** Protected patterns list present before P15 list-to-prose call; TOC detection regex present; bibliography section detection present

**RUNTIME check:** Check that numbered section markers remain as headers/numbered items (not converted to prose sentences); check that bibliography entries retain their structure

---

## AC-10 — Idea-Order Disruptor Gating

**Priority: MEDIUM**

**Conflict:** Stage 2 Op 11 (idea-order disruptor / P26) must not execute on ambiguous register, and must not reorder macro-structure in academic texts.

**Decision Tree:**
```
ASSERT register in ['academic', 'academic-essay', 'journalistic', 'general']
IF register not in this list:
    SKIP Op 11 entirely (unknown register = safe mode)

IF register == 'academic':
    Op 11 operates at PARAGRAPH level ONLY
    Scope: paragraph ordering within a single chapter/section
    NEVER reorder chapters, sections, or major structural divisions

ELIF register in ['journalistic', 'essay', 'general', 'academic-essay']:
    Op 11 operates at paragraph + section level
    Can reorder sections for narrative impact
```

**Affected Stages:** Stage 2 (`structural_rewriter.py`)

**Config Parameter:** No config key — hardcoded register assertion + scope restriction

**BUILD check:** `assert register in [...]` statement present before Op 11 call; scope restriction (paragraph-only) enforced for academic register

**RUNTIME check:** Macro-structure preserved (chapters in numerical order, conclusion after chapters)

---

## AC-11 — Standalone Definitions

**Priority: LOW**

**Conflict:** Stage 3 converts standalone definition sentences. English form differs from Russian form.

**Decision Tree:**
```
IF language == 'en':
    Detect pattern: "X is defined as [definition]."
    Convert to: embed definition in parenthetical in first usage of X

ELIF language == 'ru':
    Detect pattern: "Под X понимается [definition]."
    Also detect: "X — это [definition]."
    Convert to: embed in parenthetical in first usage of X
```

**Affected Stages:** Stage 3 (`lexical_enricher.py`)

**Config Parameter:** No config key

**BUILD check:** Language-conditional definition detection patterns present

**RUNTIME check:** Count standalone definition sentences per pattern; target = 0 per document

---

## AC-12 — But:However Ratio for Russian

**Priority: LOW**

**Conflict:** English `But:However` ratio metric (target ≥ 2:1) is English-specific. Russian equivalent is `Но:Однако`.

**Decision Tree:**
```
IF language == 'ru':
    Score report returns: {"but_however_ratio": null}
    Report INSTEAD: no_odnako_ratio (Но:Однако)
    Target Но:Однако ≥ 2:1 (from config: p29_russian.target_no_odnako_ratio)
    Count "Но" + "но" at sentence-initial positions vs "Однако"

ELIF language == 'en':
    Score report returns: {"but_however_ratio": X}
    Target But:However ≥ 2:1
    Count "But" + "but" at sentence-initial positions vs "However"
```

**Affected Stages:** Stage 5 (`scorer.py`)

**Config Parameters:**
- `p29_russian.target_no_odnako_ratio: 2.0` ✅
- `scoring.ru_no_odnako_ratio_target: 2.0` (required in scoring block)

**BUILD check:** `if language == 'ru': but_however_ratio = None` branch in scorer; `no_odnako_ratio` computed for Russian

**RUNTIME check:** Verify score report structure matches language; check ratio against 2.0 target

---

## AC-13 — Citation Density vs. GOST Stream Minimums

**Priority: LOW**

**Conflict:** Per-page citation density metric (Stage 5 quality check) and GOST stream source minimums (Phase 0A quantity requirement) are different metrics and must be enforced independently.

**Decision Tree:**
```
BOTH metrics are always enforced independently:

Metric 1 — Per-page citation density (Stage 5):
    Compare citations/page against domain baseline from citation_density_by_domain
    Flag if density is outside domain range

Metric 2 — Stream source minimums (Phase 0A):
    vkr_bachelor: ≥ 50 sources
    vkr_master: ≥ 60 sources
    coursework: ≥ 20 sources
    research: ≥ 30 sources
    abstract_paper: ≥ 10 sources
    Flag if total source count < minimum for stream_id

Score report includes BOTH metrics as separate fields.
```

**Affected Stages:** Phase 0A (`source_finder.py`), Stage 5 (`scorer.py`)

**Config Parameters:**
- `citation_density_by_domain` ✅ (full domain map)
- `generator.source_minimums` ✅ (all stream minimums)

**BUILD check:** Both metrics computed independently in scorer.py; both appear in score_report output

**RUNTIME check:** Verify score report has both `citation_density` and `source_count` fields

---

## AC-14 — Russian P7 Words Not in English Banlist

**Priority: LOW**

**Conflict:** Russian AI patterns ("следует отметить", "является ключевым") not caught by English regex.

**Decision Tree:**
```
IF language == 'ru':
    APPLY _apply_russian_patterns(text, config) using p7_russian config block
    Scan for:
        - p7_russian.absolute_ban (17 phrases)
        - p7_russian.importance_framing_ban (7 phrases)
        - p7_russian.announcement_ban (8 phrases)
    Also use {{LANGUAGE}} in LLM prompts for patterns not covered by regex

ELIF language == 'en':
    APPLY English p7 banlist patterns
    Russian p7_russian block not applicable
```

**Affected Stages:** Stage 1 (`analyzer.py`), Stage 3 (`lexical_enricher.py`), Stage 5 (`scorer.py`)

**Config Parameters:**
- `p7_russian.absolute_ban` ✅ (17 phrases including в рамках данной работы, подводя итог вышесказанному)
- `p7_russian.importance_framing_ban` ✅ (7 phrases)
- `p7_russian.announcement_ban` ✅ (8 phrases)

**BUILD check:** `_apply_russian_patterns()` method references p7_russian config blocks; `{{LANGUAGE}}` present in Stage 3 prompt

**RUNTIME check:** Full scan of all p7_russian banlist phrases; any found → FAIL

---

## AC-15 — Perplexity Scoring for Russian

**Priority: LOW**

**Conflict:** GPT-2 perplexity model is English-only; perplexity scores on Russian text are meaningless (GPT-2 is trained on English data).

**Decision Tree:**
```
IF language == 'ru':
    _skip_perplexity = True
    Stage 5 skips perplexity computation
    Score report: "N/A (Russian text)" for perplexity fields
    Reason: GPT-2 (gpt2) is English-only; Russian text scores are invalid

ELIF language == 'en':
    Compute perplexity normally using local_models.perplexity_model ("gpt2")
    Target: output_perplexity / input_perplexity ≥ 1.5
    Score report: numeric perplexity lift value
```

**Affected Stages:** Stage 1 (`analyzer.py`), Stage 5 (`scorer.py`)

**Config Parameters:**
- `local_models.perplexity_model_ru: null` ✅ (null signals skip)
- `local_models.perplexity_model: "gpt2"` ✅ (English only)
- `scoring.skip_perplexity_for_russian: true` (required in scoring block)

**BUILD check:** `if language == 'ru': _skip_perplexity = True` or equivalent in analyzer.py and scorer.py; `perplexity_model_ru: null` checked before perplexity computation

**RUNTIME check:** For Russian text: verify score report shows "N/A (Russian text)" for perplexity fields, not a numeric score
