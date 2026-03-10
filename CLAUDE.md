# CLAUDE.md — AI Anti-anti Plag

## Project Overview

**Goal**: Build a production-grade text humanization pipeline for a university AI-integration
competition. The system takes AI-generated text as input and outputs text that is:

- Indistinguishable from human writing by state-of-the-art AI detectors
  (GPTZero, Turnitin, Copyleaks, Originality.ai, ZeroGPT)
- Logically coherent, knowledge-rich, and structurally sound
- Aesthetically natural — reads like a skilled, opinionated human wrote it
- NOT a simple synonym-swapper or surface-level paraphraser

This is a research-grade engineering project. Quality of output is the primary metric.

The pattern knowledge base is the **Humanizer framework** (github.com/blader/humanizer):
30 empirically-grounded AI writing patterns sourced from Wikipedia's WikiProject AI Cleanup,
used as both the detection target and the transformation guide for all pipeline stages.

---

## Core Objectives and Success Criteria

### Primary success criteria (in priority order)

1. **Detection bypass rate**: >= 90% of outputs score < 20% AI probability across all major detectors when tested with 500-word samples.
2. **Coherence score**: Human evaluators rate output >= 4/5 on logical flow.
3. **Naturalness score**: Human evaluators rate output >= 4/5 on stylistic authenticity.
4. **Perplexity lift**: Output perplexity (measured against GPT-2) is >= 1.5x the input perplexity.
5. **Burstiness score**: Output achieves sentence-length variance coefficient >= 0.45 (versus typical AI output at ~0.15–0.20).
6. **Pattern elimination rate**: >= 85% of detected Humanizer patterns removed from output vs. input.
7. **Paragraph burstiness score**: Paragraph token-count coefficient of variation >= 0.50 (mix of 1-sentence paragraphs and 7+-sentence paragraphs must appear in output).
8. **Length reduction ratio**: Output word count <= 90% of input word count (conciseness is a measurable human signal; AI inflates length).
9. **Announcement opener count**: 0 instances per 500 words (hard requirement). Sentences that announce what is about to be said before saying it — "Here's the problem with X," "X deserves mention," "X is instructive about Y" — must be eliminated entirely.
10. **Paragraph-ending generalization count**: 0 per document. Paragraphs must end on their most specific, concrete data point — not on an abstract lesson extracted from the facts.

### Anti-goals

- Do not optimize purely for detector bypass at the cost of readability.
- Do not produce outputs that feel "too casual" or "too literary" — match the register of the input domain (academic, journalistic, technical, etc.).
- Do not hard-code detector-specific hacks — they decay as detectors update.
- Do not produce "sterile but technically clean" text — voiceless writing is just as detectable as raw AI slop. Personality must be actively injected.
- Do not produce structurally symmetric text — uniform paragraph lengths, mirrored argument structure, and repeated transitions are as detectable as AI vocabulary. Asymmetry is mandatory.
- Do not convert passive voice uniformly — mechanical active-voice conversion is itself a pattern. Natural passive constructions should be preserved; forced agent-naming that sounds awkward is worse.
- Do not substitute synonyms as the primary transformation — vocabulary swaps without structural and discourse changes fail modern detectors. Deep rewriting is the only durable strategy.

---

## Architecture

### Operating Modes

The system supports two end-to-end operating modes:

**Generation mode** (topic → text → humanized output):
```
[User Parameters: stream_id, topic, domain, language, level, ...]
      │
      ▼
┌──────────────────────────────────────────────┐
│ Phase 0A: SourceFinder                        │
│  - Claude generates bibliography candidates   │
│  - Optional Semantic Scholar API validation   │
│  - GOST Р 7.0.100-2018 formatting            │
│  - Output: verified source list               │
└──────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────┐
│ Phase 0B: AcademicGenerator                   │
│  - Megaprompt system prompt assembly          │
│  - Section-by-section generation              │
│  - Sources injected into text as [N] refs     │
│  - Post-generation structural check           │
└──────────────────────────────────────────────┘
      │
      ▼
[Stages 1–5 with domain_override + register_override + language]
      │
      ▼
[Output: .txt + .docx + score report]
```

**Humanization mode** (existing text → humanized output):
```
[Input Text]  →  [Stages 1–5]  →  [Output: .txt + .docx + score report]
```

---

### Phase 0: Academic Text Generation (AcademicGenerator)

`pipeline/generator.py` — implements Phase 0B.

**Entry point**: `AcademicGenerator.generate(params: GenerationParams) → GenerationResult`

**GenerationParams fields**:
- `stream_id`: vkr | coursework | research | abstract_paper | text | essay | composition
- `topic`: Full topic string (Russian or English)
- `language`: "ru" | "en" (default: "ru")
- `domain`: it_cs | law | psychology | economics | humanities | media | general
- `level`: bachelor | master | specialist | postgraduate
- `research_type`: theoretical | empirical | applied
- `university`: Optional institution name (injected into title page)
- `word_count`: Optional target word count override
- `additional_sources`: List of user-provided source strings

**Section generation order**:
- `vkr`: title_page → annotation → toc → introduction → chapter_1 → chapter_2 → chapter_3 → conclusion → references
- `coursework`: title_page → toc → introduction → chapter_1 → chapter_2 → conclusion → references
- `research`: annotation → introduction → literature_review → methodology → results → discussion → conclusion → references
- `abstract_paper`: title_page → toc → introduction → chapter_1 → conclusion → references
- `text | essay | composition`: full (single generation call)

**Structural check** (run on Phase 0 output before passing to Stage 1):
- Max announcement openers: 0
- Max triplets: 0
- Max Block 12 violations: 0
- Max Block 7 red flags: 2
- If hard failure: re-generate section (up to 2 attempts)

**Domain → pipeline mapping** (see `config.yaml: generator.domain_map`):
- it_cs → cs, law → general, psychology → social-science, economics → economics, humanities → humanities, media → journalistic, general → general

**Register → pipeline mapping** (see `config.yaml: generator.register_map`):
- vkr/coursework/research/abstract_paper → academic
- text → journalistic, essay → academic-essay, composition → general

**Megaprompt integration**: Phase 0B uses `prompts/academic_megaprompt.md` as the system prompt. It assembles the prompt dynamically based on stream_id, domain, language, and research_type. The source list from Phase 0A is injected into the prompt so the generated text can cite real sources using GOST [N] format.

---

### Phase 0A: Source Discovery (SourceFinder)

`pipeline/source_finder.py` — implements Phase 0A.

**Entry point**: `SourceFinder.find(topic, domain, language, stream_id, min_sources, additional_sources) → SourceList`

**Three-layer source discovery**:
1. **Layer 1 (always applied)**: Claude generates bibliography candidates using `prompts/source_discovery.md`. Sources Claude is confident about are returned as-is. Uncertain sources are marked `[NEEDS VERIFICATION]`.
2. **Layer 2 (optional)**: Semantic Scholar API validates title+author+year with fuzzy matching (threshold: 0.85). Confirmed sources are marked `[VERIFIED]`.
3. **Layer 3**: User-provided sources via `--sources` flag are always included as-is.

**GOST Р 7.0.100-2018 format**: All sources formatted per Russian GOST standard:
- Russian: "Фамилия И.О. Название / И.О. Фамилия. — Город: Издательство, 2023. — N с."
- English: "Author A.A. Title / A.A. Author. — City: Publisher, 2023. — N p."

**Source category ordering** (GOST requirement for Russian academic):
1. Нормативно-правовые акты (laws, regulations) — ordered by legal force
2. Монографии и учебники (monographs, textbooks)
3. Статьи в периодических изданиях (journal articles)
4. Электронные ресурсы (online resources, must include URL + access date)

**Minimum source counts** (from `config.yaml: generator.source_minimums`):
- VKR bachelor: 50, VKR master: 60, coursework: 20, research: 30, abstract_paper: 10

**Score report** (included in Stage 5 output):
```json
{
  "sources": {
    "total": 22, "verified_by_api": 18, "needs_verification": 4,
    "by_type": {"article": 9, "monograph": 7, "textbook": 4, "online": 2},
    "gost_compliant": true, "min_sources_met": true,
    "needs_verification_list": ["Source N — needs user check", ...]
  }
}
```

---

### Word (.docx) Output

`pipeline/formatter.py` — implements `export_to_docx(text, params, output_path, config)`.

**GOST 7.32-2017 formatting** (applied when `register in ['academic', 'academic-essay']`):
- Font: Times New Roman 14pt
- Line spacing: 1.5
- First-line indent: 1.25 cm
- Margins: left 3.0 cm, right 1.5 cm, top 2.0 cm, bottom 2.0 cm
- Alignment: justified
- Headings: sentence-case (not Title Case)
- Chapter headings (Heading 1): bold, UPPERCASE
- Section headings (Heading 2): bold
- Subsection headings (Heading 3): regular weight

**Free formatting** (applied when `register in ['journalistic', 'general', 'composition']`):
- Font: Calibri 11pt
- Line spacing: 1.15
- Margins: 2.5 cm all sides
- No first-line indent

**Section detection**: Parses `## Heading` → Heading 1, `### Subheading` → Heading 2, `#### Sub-sub` → Heading 3 from Stage 5 output text.

**Visualization rendering** (in addition to text):
- Tables in generated text (markdown `|` format) → GOST-compliant Word tables with caption «Таблица N — Название» above (or «Table N — Title» for English)
- Figure placeholders `[РИСУНОК N — Название]` → positioned Word image block with caption below
- Figure captions follow GOST numbering: tables numbered separately from figures, continuous across document
- Source annotations (`Источник: ...` / `Составлено автором`) rendered as small italic paragraph below table/figure

**Library**: `python-docx` (already in requirements.txt).

---

### Phase 0B: Visualization Integration

БЛОК 16 of `prompts/academic_megaprompt.md` governs all visualization decisions during Phase 0B generation. Pipeline components must enforce these rules:

**Stream-level visualization minimums** (from БЛОК 16.2):

| stream_id | Visualization | Minimum |
|---|---|---|
| `vkr` | Mandatory | 5–10 tables/figures (bachelor) · 8–15 (master) |
| `coursework` | Mandatory | 3–6 tables/figures |
| `research` | Mandatory | 3–8 (depends on subtype) |
| `abstract_paper` | Desirable | 1–3 (if data available) |
| `text` | Context-dependent | If data, statistics, or comparison present |
| `essay` | Optional | Only if it strengthens the argument |
| `composition` | None | — |

**Domain → visualization type mapping** (from БЛОК 16.6):

| domain | Typical visualizations |
|---|---|
| `it_cs` | UML diagrams, ER schemas, algorithm block diagrams (ГОСТ 19.701-90), interface screenshots, technology comparison tables with metrics |
| `law` | Norm comparison tables, legal relationship schemas, legislative change chronological tables |
| `psychology` | Result graphs (bar, scatter with confidence intervals), methodology tables, experiment schemas |
| `economics` | Linear dynamics graphs, structural diagrams, financial indicator tables, SWOT matrices |
| `humanities` | Chronological tables, concept/school relationship schemas, maps |
| `media` | Audience metric graphs, content analysis tables, business model schemas |
| `general` | Comparison tables, dynamics graphs, schemas — by topic context |

**`pipeline/generator.py` responsibilities:**
- `AcademicGenerator` tracks running table count and figure count during section-by-section generation
- After all sections generated: verify actual count >= stream minimum from БЛОК 16.2
- If minimum not met on data-heavy sections (Chapter 2 for economics/management, empirical results for psychology/research): trigger section re-generation with explicit instruction to add missing visualizations (up to 1 re-attempt)
- Generated tables are output in markdown `|` format; figure placeholders as `[РИСУНОК N — Название]`

**`pipeline/scorer.py` responsibilities (Stage 5):**
- Count tables and figures in Phase 0 output
- Flag as score report item if count < stream minimum: `{"visualization_count": {"tables": N, "figures": M, "total": N+M, "minimum_required": K, "pass": bool}}`
- For humanization-mode inputs: count tables/figures in input and verify they are preserved in Stage 5 output

**`pipeline/formatter.py` responsibilities:**
- Parse markdown tables → GOST Word tables (БЛОК 16 caption format)
- Parse `[РИСУНОК N — ...]` placeholders → Word figure blocks with caption
- Apply language gate: Russian → «Таблица N — Название» / «Рисунок N — Название»; English → «Table N — Title» / «Figure N — Title»
- Verify continuous numbering (tables numbered separately from figures)

---

### Megaprompt–Pipeline Synergy Map

Complete mapping of `prompts/academic_megaprompt.md` rules to pipeline stages:

| Megaprompt Rule | Pipeline Stage | Relationship |
|---|---|---|
| Block 7.6 Red Flags | P26 / Stage 2 | Megaprompt prevents at generation; Stage 2 catches survivors |
| Block 10.3 No vague attributions | P5+P38 / Stage 3 | Same rule; GOST [N] format preserved for Russian academic |
| Block 10.2 Forbidden phrases (Russian) | P22+P31 / Stage 3 | Russian equivalents in p7_russian config; Stage 3 applies them |
| Block 11.1 IT results with metrics | P32+P36 / Stage 3+4 | Both ban modal hedging on results with numbers |
| Block 6 Introduction elements | P9+P31 / Stage 2 | Intro declares content; AC-1 governs boundary |
| Block 9 Conclusion: specific last fact | P24+P48 / Stage 4 | Both require ending on concrete data |
| Block 8 GOST citations [N] | P42 / Stage 4 | Citation density calibrated; GOST [N] preserved (not converted) |
| Block 7.5 Logical bridges | P26+P29 / Stage 2+3 | Bridge opens with content reference, not connector (AC-2) |
| Block 12 Forbidden structural patterns | P10+P25+P29 / Stage 2 | Hard bans overlap — fully synergistic |
| Block 5 GOST macro-structure | P37 / Stage 2 | GOST order preserved; within-section asymmetry still required (AC-3) |
| Block 7 Knowledge synthesis | P31+P26 / Stages 2+4 | Information-first posture, non-default ordering |
| Block 13 Originality | P11 / Stage 3 | Paraphrase at sentence/idea level; entity names repeated identically (AC-5) |
| Block 8 Source minimums | source_finder / Phase 0A | Min counts enforced at generation; density metric in Stage 5 |
| Block 16 Visualization requirements | generator.py / formatter.py / Stage 5 | БЛОК 16 governs visualization type, placement, captions, and minimums; generator tracks counts; formatter renders; Stage 5 verifies |

---

### Anti-Conflict Rules (AC-1 through AC-15)

These rules resolve the 15 conflicts identified between `prompts/academic_megaprompt.md` and the English-centric pipeline. All pipeline code MUST respect these rules.

**AC-1 — Em Dash: Language Gate (HIGH)**
`reduce_em_dashes()` in `structural_rewriter.py` applies unconditionally. Russian grammar requires em dashes in copular sentences ("Москва — столица России"), definitions, appositives.
- `language='en'`: apply `reduce_em_dashes()` (target: 0 em dashes)
- `language='ru'`: apply `reduce_em_dashes_ru()` (conservative: reduce only AI-overuse >3 per paragraph, preserve grammatically required em dashes)

**AC-2 — Attribution Format: GOST [N] vs Author-Year (HIGH)**
Stage 3 lexical prompt instructs author-year format ("Keohane (1969) suggests..."). GOST 7.32-2017 requires numeric [N].
- `citation_format='GOST'` (when `language='ru'` and `register='academic'`): Attribution = "Как утверждает [Author] [N], ..." — NEVER convert [N] to author-year
- `citation_format='AUTHOR_YEAR'` (all other registers): "Keohane (1969) suggests..."

**AC-3 — GOST Macro-Structure Preservation (HIGH)**
Stage 2 idea-order disruptor (P26) must NOT reorder GOST section markers (Введение, Заключение, Список литературы, Глава N).
- P26 applies only to within-section micro-structure (paragraph ordering within chapters)
- Never reorder: title page, annotation, TOC, introduction, chapters (by number), conclusion, references

**AC-4 — Passive Voice Threshold for Russian Academic (HIGH)**
Stage 4 flags >20% passive voice. Russian academic text uses 50%+ passive as domain norm.
- `language='ru'` AND `register='academic'`: passive threshold = 0.70 (from `config.yaml: discourse.academic_ru_passive_threshold`)
- `language='ru'` AND `register='academic-essay'`: passive threshold = 0.50 (from `config.yaml: discourse.academic_essay_ru_passive_threshold`)
- `language='ru'` AND `register='journalistic'`: passive threshold = 0.30 (from `config.yaml: discourse.journalistic_ru_passive_threshold`)
- English or other combinations: passive threshold = 0.20 (from `config.yaml: discourse.default_passive_threshold`)

**AC-5 — Figurative Language in Russian Academic (HIGH)**
Stage 4 Pass A Op 8 injects metaphors/analogies. Russian VKR/coursework/research = no metaphors.
- Skip Op 8 when: `language='ru'` AND `register='academic'`
- Skip Op 8 for: math domain (existing rule)
- Apply otherwise (including Russian journalistic/essay)

**AC-6 — English-Only Regex for Russian Text (HIGH)**
All regex patterns (announcement openers, P29 connectors, P7 vocab, P28 substitutions) are English-only. Russian AI patterns go undetected.
- `language='ru'`: apply `_apply_russian_patterns(text, config)` using `p7_russian` and `p29_russian` config blocks
- Prompt templates include `{{LANGUAGE}}` variable; LLM handles Russian patterns not covered by regex

**AC-7 — F5/F6 in Russian/Academic Text (MEDIUM-HIGH)**
Pass B audit injects apostrophe drops (F5) and grammar errors (F6). F5 is inapplicable to Russian (apostrophes not used). F6 errors in Russian academic are too visible.
- `language='ru'`: skip F5 entirely; F6 = comma placement variation only (1-2 instances)
- `register='academic'` (any language): skip F5 and F6 entirely
- `language='en'` AND `register='journalistic'`: apply F5 (3-5 drops) + F6 (2-3 errors)

**AC-8 — Quote Normalization for Russian (MEDIUM)**
Stage 2/3 normalizes to ASCII straight quotes `"`. Russian uses guillemets «».
- `language='en'`: normalize to ASCII straight quotes `"`
- `language='ru'`: normalize to guillemets «» using `normalize_quotes_ru()`

**AC-9 — List-to-Prose Scope (MEDIUM-HIGH)**
Stage 2 list-to-prose (P15) must not convert GOST section structure.
- Never convert: numbered section markers (1.1, Глава N), bibliography entries, TOC items
- Only convert: content bullets with "**Header:** Content" body-text format

**AC-10 — Idea-Order Disruptor Gating (MEDIUM)**
Stage 2 Op 11 (idea-order disruptor) must not execute on ambiguous register.
- Assert `register in ['academic', 'academic-essay', 'journalistic', 'general']` before Op 11
- For `register='academic'`: Op 11 operates at paragraph level only, never at macro-structure level

**AC-11 — Standalone Definitions (LOW)**
Stage 3 converts "X is defined as Y" standalone sentences. Russian form is "Под X понимается Y".
- `language='en'`: convert "X is defined as Y" form
- `language='ru'`: convert "Под X понимается Y" form

**AC-12 — But:However Ratio for Russian (LOW)**
English `But:However` ratio metric applies to English text only.
- `language='ru'`: score report returns `{"but_however_ratio": None}`; reports `no_odnako_ratio` (Но:Однако) instead using `config.yaml: p29_russian.target_no_odnako_ratio`

**AC-13 — Citation Density vs. GOST Stream Minimums (LOW)**
Per-page citation density metric (Stage 5) and GOST stream source minimums (Phase 0A) are orthogonal. Both are enforced independently.

**AC-14 — Russian P7 Words Not in English Banlist (LOW)**
Russian AI patterns ("следует отметить", "является ключевым") not caught by English regex.
- Handled by `p7_russian` config block + `_apply_russian_patterns()` method + `{{LANGUAGE}}` in LLM prompts

**AC-15 — Perplexity Scoring for Russian (LOW)**
GPT-2 perplexity model is English-only; scores on Russian text are meaningless.
- `language='ru'`: set `_skip_perplexity=True` in analysis_report; Stage 5 skips perplexity metrics
- Score report shows "N/A (Russian text)" for perplexity fields

---

### Russian Language Adaptation

#### Russian P7 Banlist (from `config.yaml: p7_russian`)

**Absolute ban** (always remove): следует отметить, является ключевым, играет важную роль, необходимо подчеркнуть, представляется актуальным, в условиях современности, на сегодняшний день, в наше время, как известно, очевидно что, вышесказанное свидетельствует, немаловажно также, актуальность темы заключается в том, данная проблема является актуальной

**Importance-framing ban** (always remove): играет важную роль в, является ключевым для, имеет принципиальное значение, занимает особое место в, заслуживает особого внимания

**Announcement ban** (always remove): следует отметить что, необходимо отметить что, важно подчеркнуть что, стоит отметить что, обратим внимание на то, отметим что

#### Russian P29 Connector Rules (from `config.yaml: p29_russian`)

- **Absolute ban** (0 per document): во-первых, во-вторых, в-третьих, помимо этого
- **Near-ban** (≤ 1 per document): кроме того
- **Rate-limited** (≤ 1 per 500 words): более того, помимо прочего
- **Permitted**: также, однако, но, при этом, между тем, тем не менее, вместе с тем
- **Encouraged**: также, но
- **Target Но:Однако ratio**: ≥ 2:1 (analogous to English But:However)

#### Russian P10 (Triplet Ban)

The triplet ban (P10) applies identically in Russian. Any three-item parallel series is a hard failure regardless of language.

#### Russian P32 (Modal Hedging on Results)

Modal hedging ban on result sentences applies identically in Russian. Russian modal verbs: может, мог бы, вероятно, по-видимому, по всей видимости, можно предположить, предположительно — all banned from sentences containing numerical data.

#### Russian F-Rules Differences

- **F2** (em dashes): Conservative for Russian (AC-1). Em dashes in copular sentences preserved.
- **F3** (semicolons): Academic Russian may use semicolons in complex lists — do not apply wholesale removal.
- **F5** (apostrophes): Inapplicable to Russian — skip entirely.
- **F6** (grammar errors): Russian academic — skip entirely. Russian journalistic — comma placement variation only (1-2 instances).
- **F7** (filler words): Russian equivalents: "в общем-то", "собственно говоря" — apply sparingly in journalistic/casual only.

#### Russian spaCy Model

Primary: `ru_core_news_sm` (install: `python -m spacy download ru_core_news_sm`)
Fallback: regex-based tokenization if spaCy model unavailable.
Perplexity: skipped for Russian (GPT-2 English only). Stage 5 shows "N/A" for perplexity metrics.

---

### Pipeline Stages

The system is a sequential, multi-stage NLP pipeline. Each stage is independently testable and swappable.
Stage 1 and Stage 5 run locally (no API cost). Stages 2–4 call the Claude API.

```
[Input Text]
     │
     ▼
┌───────────────────────────────────────┐
│ Stage 1: Analysis                     │
│  - Domain + register classifier       │  Academic / journalistic / technical / casual
│  - Baseline perplexity scorer         │  GPT-2 perplexity on raw input
│  - Burstiness baseline                │  Sentence-length coefficient of variation
│  - Humanizer pattern scanner          │  Count occurrences of all 30 AI patterns
│  - Paragraph burstiness baseline      │  Paragraph token-count coefficient of variation
│  - Transition monotony score          │  % sentences starting with stock connectors
│  - Announcement opener count          │  Sentences announcing topic before stating it (target: 0)
│  - Triplet instance count             │  Noun, verb, and adverbial tricolons separately tracked
│  - Para-ending generalization count   │  Final sentences abstracting from paragraph facts (target: 0)
│  - Attributive passive count          │  "has been accused/noted/reported" without named source
│  - "genuinely [adj]" count            │  Importance-inflating intensifier (target: 0)
│  - Visualization count (Phase 0 only) │  Tables + figures in Phase 0 output vs. stream minimum (БЛОК 16.2)
│  - Output: pattern report + baseline  │  Feeds into Stage 2 prompt construction
└───────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────┐
│ Stage 2: Structural & Format Rewrite  │  Targets Humanizer patterns: 8–10, 12–16, 25–27
│  - Announcement opener remover        │  Delete sentences that announce topic before stating it (P9)
│  - Copula restoration                 │  "serves as/stands as/features/boasts" → is/are/has
│  - Parallelism breaker                │  Remove "Not only X, but also Y" constructions
│  - Triad buster                       │  Break noun, verb, and adverbial tricolons (P10)
│  - False range eliminator             │  Remove "from X to Y" on non-scalar pairs
│  - Em dash reducer                    │  Replace em dashes with commas/periods
│  - List-to-prose converter            │  Convert inline-header bullet lists to prose
│  - Heading normalizer                 │  Title Case → Sentence case in headings
│  - Sentence length variator           │  Inject short 1–4 word sentences; break long ones
│  - Paragraph length variator          │  Force para-CV >= 0.50: inject 1-sentence paras
│  - Idea-order disruptor               │  Break intro→list→explain→conclude default ordering
│  - Sentence-starter diversifier       │  Flag 3+ consecutive same-start sentences; rewrite
└───────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────┐
│ Stage 3: Lexical & Tonal Cleanup      │  Targets Humanizer patterns: 1–7, 11, 17–18, 28–29
│  - AI vocabulary eliminator           │  Remove banlist words (see Pattern Catalog §P7)
│  - Significance deflation             │  Remove "pivotal/vital/testament/underscores/genuinely [adj]/instructive/deserves mention" inflation
│  - Promotional language remover       │  Remove "vibrant/nestled/breathtaking/renowned"
│  - Vague attribution replacer         │  "Experts say" + attributive passive ("has been accused/noted") → named source or remove
│  - Elegant variation fixer            │  Stop synonym cycling; repeat the clearest noun
│  - Emoji remover                      │  Strip decorative emojis from headings/bullets
│  - Quote normalization                │  Replace curly " " with straight " "
│  - Weasel word eliminator             │  Remove "could potentially possibly be argued"
│  - Vocabulary substitution table      │  Apply P28 map: leverage→use, utilize→use, etc.
│  - Transition diversifier             │  Replace Furthermore/Moreover/Additionally (P29)
│  - Preposition micro-variator         │  Flag repeated "in terms of"/"in order to" constructions
└───────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────┐
│ Stage 4: Voice & Discourse Injection  │  Targets: soul requirement, patterns 1–6, 19–24, 30
│  - Pass A: Voice injection            │  Add opinions, reactions, first-person where appropriate
│  - Pass A: Specificity grounding      │  Replace vague claims with concrete details/examples
│  - Pass A: Sentence rhythm            │  Mix lengths: short punchy + long discursive
│  - Pass A: Chatbot artifact removal   │  Remove "I hope this helps", "Great question!", etc.
│  - Pass A: Generic ending removal     │  Remove "exciting times lie ahead" conclusions
│  - Pass A: Active/tense variation     │  Flag passive > 20% or tense monotony > 80%; rewrite
│  - Pass A: Imperfection texture       │  Add parenthetical asides, fragments, register drops (P30)
│  - Pass A: Figurative language seed   │  Insert 1-2 metaphors/analogies per section
│  - Pass A: Meaning-first rewrite      │  Internalize passage meaning; rewrite from comprehension
│  ─────────────────────────────────── │
│  - Pass B: Audit prompt               │  11-point checklist (see Two-Pass section for full list)
│  - Pass B: Audit rewrite              │  Address remaining tells identified in audit
└───────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────┐
│ Stage 5: Scoring & Feedback           │
│  - Perplexity scorer                  │  GPT-2 perplexity (target: >= 1.5x baseline)
│  - Burstiness scorer                  │  Sentence CV (target: >= 0.45)
│  - Pattern rescan                     │  Re-run Stage 1 scanner; compute % eliminated
│  - Coherence checker                  │  Embedding-based cosine similarity chain
│  - Paragraph burstiness scorer        │  Para token-count CV (target: >= 0.50)
│  - Length reduction ratio             │  Output/input word-count ratio (target: <= 0.90)
│  - Announcement opener count          │  Target: 0 per 500 words (hard requirement)
│  - Triplet instance count             │  Noun + verb + adverbial tricolons (target: 0, hard requirement)
│  - Para-ending generalization count   │  Abstract lesson wrap sentences (target: 0)
│  - Attributive passive count          │  Source-suppressed accusations/citations (target: 0)
│  - Visualization count (Phase 0 only) │  Tables + figures vs. stream minimum (БЛОК 16.2); flag if below threshold
│  - Detector probes (optional)         │  Call GPTZero/Copyleaks API if explicitly requested
│  - Output: score report               │  All metrics vs. targets, pass/fail summary
└───────────────────────────────────────┘
     │
     ▼
[Output Text + Score Report]
```

### Two-Pass Approach (Stage 4)

The two-pass audit is sourced from the Humanizer skill's core methodology:

**Pass A — Transformation**: Identify all remaining AI patterns. Rewrite problematic sections.
Inject personality: opinions, reactions, uncertainty, specificity, varied rhythm, first-person.
Preserve all factual claims — only style changes, never content.

**Pass B — Audit**: Ask: *"What still makes the below so obviously AI-generated?"*
Answer briefly with remaining tells. Then rewrite to eliminate them.
This audit pass catches the subtle tells that Pass A misses: overly smooth transitions,
uniform clause length, structurally symmetric paragraphs, absence of figurative language,
passive-voice saturation, triplet lists, and false certainty in contested claims.
Specific audit checklist:
1. Does every paragraph start with a topic sentence and end with a wrap-up? Break the pattern in at least one.
2. Are transitions varied — or does the same connector appear more than twice per page?
3. Is the structure predictably linear (introduce → list → explain → conclude)? If so, reorder one section.
4. Does the text contain at least one concrete analogy or metaphor per section? If not, add one.
5. Does the output read shorter than typical AI output on this topic?
6. Are there any triplets (X, Y, and Z series) — including verb tricolons and "partly to X, partly to Y, partly to Z" constructions? If so, break them — zero tolerance.
7. Does the text stay at one abstraction level for 3+ sentences? If so, inject a concrete example or pull back to a general claim to vary the altitude.
8. Does the text write with false certainty on estimated or contested claims? If so, add epistemic hedging: "probably," "roughly," "it seems," "as far as available data show."
9. Is >80% of the text in the same verb tense? If so, vary 2–3 sentences to a different tense where contextually natural.
10. Does any sentence announce what is about to be said, flag importance before stating content, or describe the content as "worth mentioning"? ("Here's the problem with X", "X also deserves mention", "There's also a X worth flagging", "X is instructive about Y", "I mention this because", "X is worth a brief detour"). Delete all such sentences entirely — start with the content.
11. Does any paragraph end with an abstract generalization extracted from the preceding concrete facts? ("The uneven distribution of X complicates any simple story about Y", "X repeats the same pattern across Y", constructions ending with "regardless of how Z"). End on the most specific data point instead.

### LLM Usage Patterns

- **Primary rewrite engine**: Claude API (`claude-opus-4-6` or `claude-sonnet-4-6`).
- **Scoring/analysis**: Local models (GPT-2, spaCy) — no API cost on non-rewrite steps.
- **Chunking**: 200–400 word chunks with ~1 sentence overlap between chunks.
- **Temperature**: 0.85–1.1 for rewrite stages. 0.2–0.4 for analysis/classification.
- **One transformation per prompt**: Never combine multiple stage operations in one call.
- **Prompt structure**: System prompt = register + domain context. User prompt = specific transformation instruction + text chunk.

### Technology Stack

- **Language**: Python 3.11+
- **LLM orchestration**: Claude API (anthropic SDK)
- **NLP utilities**: spaCy, NLTK, HuggingFace transformers
- **Scoring**: `transformers` (GPT-2 perplexity), `numpy` (burstiness math)
- **Testing**: `pytest`
- **Config**: `.env` for API keys, `config.yaml` for pipeline parameters

---

## AI Pattern Catalog (Humanizer Framework)

Source: github.com/blader/humanizer, based on Wikipedia's "Signs of AI writing" guide.
These 30 patterns are the core detection and transformation targets for all pipeline stages.
Install the interactive skill: `git clone https://github.com/blader/humanizer ~/.claude/skills/humanizer`
Use interactively in Claude Code with `/humanizer`.

### Category 1 — Content Patterns

**P1 · Significance & Legacy Inflation**
Watch words: `stands/serves as`, `testament/reminder`, `vital/significant/crucial/pivotal/key role`,
`underscores/highlights`, `reflects broader`, `symbolizing`, `contributing to`, `setting the stage for`,
`marking/shaping`, `represents/marks a shift`, `key turning point`, `evolving landscape`, `indelible mark`
Fix: Replace with specific facts. "Marking a pivotal moment in the evolution of..." → "was established in 1989"

**P2 · Notability & Media Coverage Emphasis**
Watch words: `independent coverage`, `local/regional/national media outlets`, `written by a leading expert`, `active social media presence`
Fix: Give actual context. "Cited in NYT, BBC, FT... 500,000 followers" → "In a 2024 NYT interview, she argued..."

**P3 · Superficial -ing Endings**
Watch words: `highlighting`, `underscoring`, `emphasizing`, `ensuring`, `reflecting`, `symbolizing`,
`contributing to`, `cultivating`, `fostering`, `encompassing`, `showcasing`
Fix: Cut the participial phrase or convert to a direct attribution. "symbolizing Texas bluebonnets, reflecting the community's deep connection" → "The architect said these were chosen to reference local bluebonnets"
Also: never stack two or more -ing participial clauses in a single sentence. "Leveraging AI tools, fostering collaboration, enhancing productivity" → "AI tools let teams work faster. Collaboration is the mechanism."

**P4 · Promotional / Advertisement Language**
Watch words: `boasts a`, `vibrant`, `rich (figurative)`, `profound`, `enhancing its`, `showcasing`,
`exemplifies`, `commitment to`, `natural beauty`, `nestled`, `in the heart of`, `groundbreaking`,
`renowned`, `breathtaking`, `must-visit`, `stunning`
Fix: Neutral factual language. "Nestled within the breathtaking region... vibrant town with rich cultural heritage" → "is a town in the Gonder region, known for its weekly market and 18th-century church"

**P5 · Vague Attributions / Weasel Words**
Watch words: `Industry reports`, `Observers have cited`, `Experts argue`, `Some critics argue`, `several sources`
Fix: Name the specific source or remove. "Experts believe it plays a crucial role" → "according to a 2019 survey by the Chinese Academy of Sciences"
When replacing vague attributions, name the source with enough specificity that a target reader would recognize it. "Researchers say" → "A 2023 MIT Media Lab study found..." — year, institution, and finding must all appear.
Also flag the **attributive-passive** form — where the source is suppressed via passive voice:
- "has been accused of..." (accused by whom? always name the accuser or rewrite as active)
- "have noted inconsistencies" (who, specifically, with which study or data?)
- "has been reported to..." (by which outlet, on what date?)
Fix: same as above — name source with year + institution + finding, or remove. "Russia's statistics agency has been accused, repeatedly, of..." → "Economists at the Kyiv School of Economics have argued (2023) that Rosstat's methodology..."

**P6 · Formulaic Challenge/Prospect Sections**
Watch words: `Despite its... faces several challenges...`, `Despite these challenges`, `Challenges and Legacy`, `Future Outlook`
Fix: Specific facts only. "Despite challenges... continues to thrive" → "Traffic congestion increased after 2015. Municipal corporation began project in 2022."

### Category 2 — Language & Grammar Patterns

**P7 · AI Vocabulary Banlist**
High-frequency post-2023 AI words that co-occur and signal AI authorship. NEVER use:
`additionally`, `align with`, `crucial`, `delve`, `emphasizing`, `enduring`, `enhance`,
`fostering`, `garner`, `highlight (verb)`, `interplay`, `intricate/intricacies`,
`key (adjective)`, `landscape (abstract noun)`, `pivotal`, `showcase`,
`tapestry (abstract noun)`, `testament`, `underscore (verb)`, `valuable`, `vibrant`

Extended banlist (second-generation AI signal words — never use):
`delve into`, `dive into`, `realm`, `harness`, `unlock`, `embark on`, `multifaceted`,
`nuanced` (when used as a generic intensifier), `cutting-edge`, `game-changer`, `seamless`,
`synergy`, `robust` (metaphorical), `leverage` (verb), `utilize`, `facilitate` (non-technical)

Importance-framing banlist (never frame importance before stating the thing itself):
`plays a crucial role`, `is central to`, `is pivotal for`, `is essential for`,
`serves as a cornerstone of`, `is key to`, `is of vital importance`, `is fundamental to`,
`is instructive [about/for]`, `deserves mention`, `is worth flagging`, `is worth a brief detour`,
`is actually remarkable`, `genuinely [adjective]` (as importance intensifier — "genuinely unprecedented", "genuinely substantial")
Fix: Delete the importance claim entirely. State what the thing does or is, directly.
"Language plays a crucial role in social integration." → "Immigrants who speak the local language are more likely to find stable work within their first year."
"The scope is genuinely substantial." → delete; the facts that follow demonstrate scope.
"Oil is the failure story, and it's instructive." → "Oil is where the sanctions failed."

Paired-abstraction banlist (AI's binary framing tell — never use):
`opportunities and challenges`, `strengths and weaknesses`, `benefits and drawbacks`,
`risks and rewards`, `pros and cons` (as section headings), `advantages and disadvantages`
Fix: Name the specific opportunity or the specific challenge. Do not balance-frame generically.

Domain exemption (context-dependent list — apply with domain check):
- "crucial", "key", "important", "significant" — acceptable in academic/policy texts WHEN: (a) used after evidence is presented (not before), (b) applied to a specific mechanism not a generic claim, (c) < 3 per 500 words. If any condition fails, replace with the specific fact.
- "leverage (v)" — acceptable ONLY when precise domain meaning is required (business strategy/finance). In general prose: always replace with "use."
- "enhance", "highlight", "valuable" — acceptable in domain-technical contexts when no plain equivalent carries the same precision. Otherwise replace per P28.
Implementation: Stage 3 must apply domain-context check before flagging any P7 word from the context-dependent list: Is the domain academic/management/policy? Is the word in an importance-framing sentence structure? Is it past the density threshold (3+ per 500 words)? Only flag when domain check AND structure check AND density check all trigger.

**P8 · Copula Avoidance**
Watch words: `serves as`, `stands as`, `marks`, `represents [a]`, `boasts`, `features`, `offers [a]`
Fix: Use is/are/has. "serves as LAAA's exhibition space... features four spaces... boasts 3,000 sq ft" → "is LAAA's exhibition space... has four rooms totaling 3,000 sq ft"

**P9 · Negative Parallelisms**
Pattern: "Not only X, but also Y" / "It's not just X, it's Y" / "Not merely X, but Y"
Fix: Collapse to the affirmative statement. "It's not just about the beat; it's part of the aggression." → "The heavy beat adds to the aggressive tone."
Also flag: sentences that announce what is about to be said ("This section will explore...", "In what follows, we examine..."). These are a variant of the same AI organizational tell. Delete and state directly.
Also explicitly flag the **negative-before-positive** structure: "not only X but also Y," "It's not just about X — it's about Y," "beyond mere X, it represents Y," "It was not just an experiment. It was a revolutionary discovery." AI uses this structure compulsively to inflate importance. Rewrite by stating what the thing IS, directly. The negative setup is always expendable.
**Announcement opener banlist** — organic-sounding variants that GPTZero flags as "Formulaic Flow." These were the #1 tell in empirical testing (8 instances in a single essay). NEVER use:
- `Here's the problem with X` → delete; open with the content: "Russia's reported 3.6% growth was almost entirely military spending."
- `X is worth a brief detour` → delete; start the detour immediately
- `There's also a X worth flagging` → delete; state the X directly
- `One thing you rarely see in [coverage] is X` → delete; present X directly
- `X also deserves mention` → delete; mention X without announcing it
- `I mention this mostly because` → delete; state the reason as a direct claim
- `X is actually [adjective]` (when framing importance, e.g., "is actually remarkable") → delete "actually [adjective]"; state what is remarkable specifically
- `X is instructive about/for Y` → delete; state the lesson as a direct claim
- `X repeats the same story across Y` → delete; state what happened in Y directly
Fix rule: If a sentence describes what it is about to do rather than doing it, delete it.

**P10 · Rule of Three Overuse**
Pattern: Ideas forced into groups of three to appear comprehensive.
Fix: Use the natural number. "keynote sessions, panel discussions, and networking opportunities... innovation, inspiration, and industry insights" → "talks and panels... informal networking between sessions"
**Zero-tolerance rule**: Exactly three items in sequence is a hard failure regardless of grammatical form. Use two items or four. If three genuine items must appear, write the third in a separate sentence. The triplet is the single strongest typographic AI signal; it must not appear anywhere in output.
"social, cultural, and linguistic factors" → "social and linguistic factors — and, in ways that are harder to isolate, cultural ones too."
**Zero tolerance extends to all grammatically parallel three-item series, not just noun lists:**
- **Verb tricolon**: "She raised the rate, required exporters to convert earnings, and imposed capital controls" → "She raised the rate to 20% and required exporters to convert earnings. Capital controls followed."
- **Adverbial tricolon**: "attributed partly to X, partly to Y, and partly to Z" → "attributed to X and Y — and, with less certainty, to Z as well"
- **Parallel negation series**: "no path to maintenance, no spare parts supply chain, no compliance with standards" — three or more consecutive "no X" constructions share the same mechanical energy as a noun triplet; break after the second with a separate sentence
Detection: flag every comma-separated or "X, Y, and Z" series in output, including verb series and "partly to X, partly to Y, partly to Z" constructions. Any triplet is a pass fail for Stage 2.
Technical enumeration exception: If exactly 3 items must appear because only 3 genuinely exist (3 research questions, 3 experimental conditions, 3 historical phases), use numbered formatting (1. X 2. Y 3. Z) to break the parallel typographic triplet. Numbered lists visually break the tricolon pattern while preserving the enumeration. Alternative: "X and Y — and, with less certainty, Z as well."

**P11 · Elegant Variation (Synonym Cycling)**
Pattern: LLM's repetition penalty causes the same entity to be called protagonist, then main character, then central figure, then hero — all in one paragraph.
Fix: Repeat the clearest noun. Never cycle synonyms just to avoid repetition.

**P12 · False Ranges**
Pattern: "from X to Y" where X and Y are not actually on a meaningful spectrum.
Fix: List directly. "from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter" → "Big Bang, star formation, and current theories about dark matter"

### Category 3 — Style Patterns

**P13 · Em Dash Overuse**
Pattern: LLMs use em dashes (—) far more than human writers.
Fix: Replace with comma, period, or parentheses. "institutions—not by people—yet continues—even in documents" → "institutions, not by people, yet continues in documents"

**P14 · Excessive Boldface**
Pattern: Mechanical emphasis of key phrases throughout body text.
Fix: Remove bold from body text. Reserve for genuinely critical warnings only.

**P15 · Inline-Header Vertical Lists**
Pattern: Bullet lists where each item starts with a bolded header and colon.
Fix: Convert to prose. "- **User Experience:** The user experience has been significantly improved..." → "The update improves the interface..."

**P16 · Title Case Headings**
Pattern: All main words capitalized in headings.
Fix: Sentence case. "## Strategic Negotiations And Global Partnerships" → "## Strategic negotiations and global partnerships"

**P17 · Decorative Emojis**
Pattern: Emojis on headings and bullets (🚀, 💡, ✅).
Fix: Remove entirely from professional/academic text.

**P18 · Curly Quotation Marks**
Pattern: ChatGPT uses typographic curly quotes (" ") instead of straight quotes (" ").
Fix: Replace all curly quotes with straight ASCII quotes.

### Category 4 — Communication Patterns

**P19 · Chatbot Correspondence Artifacts**
Watch words: `I hope this helps`, `Of course!`, `Certainly!`, `You're absolutely right!`,
`Would you like...`, `let me know`, `Here is a...`, `Great question!`
Fix: Delete entirely. These must never appear in finalized output.

**P20 · Knowledge-Cutoff Disclaimers**
Watch words: `as of [date]`, `Up to my last training update`, `While specific details are limited/scarce`, `based on available information`
Fix: Replace with specific sourced facts or remove. "While specific details are not extensively documented..." → "The company was founded in 1994, according to its registration documents."
Also replace: "in recent years", "recently", "in the modern era", "contemporary" — replace with the specific year or event. "In recent years, adoption has grown" → "Between 2020 and 2024, adoption grew 340%, according to the IDC."

**P21 · Sycophantic / Servile Tone**
Pattern: Overly positive, people-pleasing language throughout.
Fix: Neutral or direct language. "Great question! You're absolutely right..." → "The economic factors you mentioned are relevant here."

### Category 5 — Filler & Hedging Patterns

**P22 · Filler Phrases**
Common conversions:
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that" → "Because"
- "At this point in time" → "Now"
- "In the event that" → "If"
- "Has the ability to" → "Can"
- "It is important to note that" → (delete, state directly)

Also delete meta-commentary openers: "It is worth noting that", "It should be mentioned that", "One might argue that", "Needless to say" — state the content directly.

**P23 · Excessive Hedging**
Pattern: Over-qualifying statements with stacked qualifiers.
Fix: One qualifier maximum. "could potentially possibly be argued that the policy might have some effect" → "The policy may affect outcomes."

**P24 · Generic Positive Conclusions**
Watch words: `The future looks bright`, `Exciting times lie ahead`, `major step in the right direction`, `journey toward excellence`
Fix: End with a specific, concrete fact about what actually happens next. "The future looks bright..." → "The company plans to open two more locations next year."
Do not end sections with a summary sentence that mirrors the opening. If the paragraph opened with a general claim, end it with a specific detail — not a restatement. Mirrored structure is an AI signal even when word choice is varied.
**Paragraph-ending generalization wrap** — AI extracts an abstract lesson as the final sentence of a paragraph, restating the paragraph's implicit thesis in broader terms. Human writers end on the most specific data point.
Detection: flag final sentences of paragraphs that contain these constructions:
- "complicates any [adjective] story about X"
- "repeats the same [noun] across X"
- "[verb] regardless of how X"
- "[verb] any simple [noun] about X"
- abstract generalizations that broaden from the paragraph's concrete facts rather than landing on them
Fix: Delete or replace the generalization wrap with the paragraph's most specific fact.
"The uneven distribution of pain complicates any simple story about sanctions hurting everyone." → delete; end on: "Defense workers in some Urals plants were reportedly earning 2–3x prewar wages by mid-2023. Pensioners were not."

### Category 6 — Structural & Discourse Patterns

**P25 · Paragraph-Level Uniformity**
Pattern: All paragraphs have similar length (4–6 sentences), similar structure (topic sentence → evidence → wrap-up), and similar opening constructions. Additionally, all sections within a document are approximately equal in word count — every section is ~700–1,000 words and ~4–6 paragraphs. Both paragraph uniformity and section uniformity are strong AI signals.
Fix:
- Paragraph level: Deliberately vary paragraph size. Insert single-sentence paragraphs for emphasis. Allow some paragraphs to run 8+ sentences when the argument needs sustained development. In at least one paragraph per section, break the topic-sentence rule — start mid-thought or with a concrete example before stating the claim.
- Section level: Sections within a document must be different lengths. Some sections should be notably shorter (200–300 words) and some notably longer (1,200+ words) depending on the content's natural depth. Equal-length sections are a structural AI fingerprint.
Detection signal: Para token-count CV < 0.40 flags paragraph uniformity. Section token-count CV < 0.30 flags section uniformity.

**P26 · Default Structural Ordering**
Register restriction: This pattern applies to journalistic, essay, and general writing. Academic writing follows Introduction → Literature → Methodology → Results → Conclusion by epistemological necessity — not AI default. In academic register: P26 applies ONLY to within-section micro-structure (paragraph ordering within sections), not to macro-structure. Stage 2 idea-order disruptor operates at paragraph level only for academic register.
Pattern: AI defaults to: introduce concept → list components → explain each → summarize. This predictable scaffold produces Wikipedia-style text regardless of content domain.
Fix: Reorder sections so the argument is non-linear. Start with the conclusion and work backward. Open with a concrete case before the abstraction. Present the counterargument before the argument. Omit the explicit summary when the content is self-evident.
Also: human writing oscillates between abstraction levels. After stating an abstract claim, drop to a concrete example. After the example, pull back to the principle. Extended runs of pure abstraction (3+ sentences of general claims without a specific example) are an AI signal. Extended runs of pure concrete detail with no generalization are also unusual. Vary the altitude.
Also: allow occasional abrupt topic shifts without explicit transition words. Not every paragraph needs a signpost connector to the previous one. Sometimes the connection is implied, and the reader bridges the gap — this is normal in human writing. AI always explains the connection; humans sometimes trust the reader to see it.
Note: This is a paragraph- and section-level concern. The Stage 2 idea-order disruptor targets this pattern.

**P27 · Sentence-Starter Monotony**
Pattern: Multiple consecutive sentences begin with the same grammatical construction — typically "The [noun]...", "This [noun]...", or "[Subject] [verb]s..." — producing mechanical rhythm.
Fix: No more than two consecutive sentences may share the same sentence-opening grammatical category. Vary openers: prepositional phrase, subordinate clause, participle, direct object, or a one-word sentence. "The policy was introduced in 2019. The policy was contested immediately. The policy failed by 2021." → "Introduced in 2019, the policy was contested immediately. It failed within two years."
Detection signal: Flag runs of 3+ sentences sharing the same first word or grammatical category.

**P28 · Formal Register Inflation (Vocabulary Substitution)**
Pattern: AI defaults to formal latinate vocabulary even when plain words communicate identically. This creates unnatural register elevation that detectors associate with machine authorship.
Core substitution table (apply mechanically in Stages 3–4):
- leverage (v) → use
- utilize → use
- facilitate → help / enable
- implement → do / carry out
- demonstrate → show
- indicate → show / suggest
- commence → start
- terminate → end / stop
- endeavor → try
- ascertain → find out
- in terms of → for / about (context-dependent)
- in order to → to
- with regard to → on / about
- it is important to → (delete, state directly)
- as a result of → because of
Exception: technical terms with no accurate plain substitute must be preserved (e.g., "facilitate" in pharmacology means something specific — keep it there).

**P29 · Connector Monotony**
Pattern: AI uses a small set of additive connectors repeatedly — "Furthermore", "Moreover", "Additionally" — and imposes mechanical enumeration scaffolds ("Firstly... Secondly... Thirdly... Finally...") that signal AI organizational structure. AI also inverts the natural But:However ratio: human academic text uses "But" 2–4× more than "However"; AI produces the opposite (However:But ≈ 3:1 to 5:1). Human corpus data: But/but appears 33–101× per thesis; However appears 8–46×; Also appears 29–63×.
Absolute ban (zero instances): `Firstly`, `Secondly`, `Thirdly`, `Finally` (as enumeration openers), `Additionally`, `In addition to this`, `It is worth noting that` (when used as preamble, not as methodological aside)
Near-ban (≤ 1 per full document in academic; ≤ 1 per 500 words in other registers): `Furthermore`
Rate-limited (≤ 1 per 500 words): `Moreover`
Permitted (not banned): `However`, `Thus`, `Therefore`, `But`, `Yet`, `Also`, `That said`, `Granted`, `To be fair`, `Meanwhile`, `Then`, `Next`
Actively encouraged (increase frequency in humanized output): `But` (sentence-initial), `Also`, `Yet`, `Meanwhile`
Target But:However ratio in output: ≥ 2:1
Fix: If the next sentence genuinely adds to the previous, run together with a comma or semicolon, or start the sentence directly with its subject. For contrast: use "But", "Yet", "That said". For concession: use "Granted" or "To be fair". For sequence: use "Then", "Next", or a time marker. Reserve "However" for genuine reversal — not mild hedging. Prefer "Also" for simple addition over "Moreover". When writing sequential steps or arguments, use concrete identifiers ("The second issue is...") rather than enumeration adverbs.
Detection signal: More than 2 uses of any single banned connector in a 300-word passage; But:However ratio < 1:1.

**P30 · Imperfection Absence (Over-Polished Texture)**
Pattern: Human writers naturally include parenthetical asides, self-corrections, sentence fragments used for emphasis, register drops between formal and informal, occasional discourse markers that signal thought process, and minor punctuation inconsistencies. AI text is uniformly polished — no roughness, no fragments, no hedging, no register shifts.
Register-dependent application (critical — do not conflate registers):
Academic register — apply ONLY these P30 techniques: epistemic hedging on contested claims ("probably", "roughly", "appears to", "it seems", "as far as available data show"), methodological transparency asides ("which, admittedly, required manual tuning"), mild evaluative language in conclusions ("alarming", "surprising", "I find this unconvincing"), explicit limitation statements, source evaluation comments. DO NOT apply to academic text: colloquial register drops ("look", "honestly", "basically", "I mean"), deliberate sentence fragments, Oxford comma inconsistency, discourse markers in body text, self-corrections mid-text.
Journalistic/essay/casual register — apply full P30 toolkit: parenthetical personality asides, deliberate fragments for emphasis, colloquial register drops, discourse markers, minor punctuation inconsistency.
Corpus evidence: Academic papers show 49–116 parenthetical asides per 20 pages — but these are definitional and methodological (source attributions, scope clarifications), NOT personality-driven. Injecting journalistic P30 textures into academic text creates obvious register violation.
Fix (Stage 4 Pass A — apply with judgment, not mechanically, using register-appropriate mode above):
- Journalistic/casual: Add one parenthetical aside per section: "(which, admittedly, is harder to verify)"
- Journalistic/casual: Allow one deliberate fragment per page for emphasis: "Remarkable, given the constraints."
- Journalistic/casual: Allow one register drop per section — a colloquial phrase signals authorship: "That is to say, it did not work."
- Journalistic/casual: Include discourse markers sparingly (1–2 per section max): "actually," "honestly," "look," "basically," "I mean"
- All registers: Include epistemic hedging where genuine uncertainty exists: "probably," "it seems," "roughly," "as far as I can tell," "my sense is that," "I'd estimate." AI writes with false certainty; humans qualify claims naturally.
- Journalistic/casual: Allow minor punctuation variation: inconsistent Oxford comma, occasional dash where a comma would also work. Do NOT introduce grammatical errors.
- All registers: Include mild evaluative language where authorial judgment applies: "alarming," "surprising," "striking," "remarkably," "I find this unconvincing."
- Do NOT apply all techniques in the same paragraph — the effect must feel accidental, not designed.
Rate limit: No more than 2 imperfection textures per 300-word passage.
Note: This is an injection pattern (Stage 4 only), not a removal pattern. Regex scanners cannot reliably detect its absence; LLM judgment is required.

### Category 7 — Extended Patterns (Corpus-Validated, 56 HSE Diploma Works)

These patterns were identified by analyzing 56 HSE Russia diploma works rated 8–10/10, covering Economics, IT, Management, Politics, Social Science, Math, and Law. All are empirically grounded in authentic human academic writing.

**P31 · Information-First Posture Violation**
What AI does: Announces importance before stating content. "Resource optimization is pivotal in modern logistics." Then states the content.
What humans do: State the content directly; importance is demonstrated by the facts, never announced.
Corpus evidence: Zero instances of P7 importance-framing patterns in any of 56 analyzed papers. Confirmed absolute signal.
Fix: Delete any sentence that describes what the following content is about or how important it is. Begin with the content itself. "Resource optimization is crucial" → delete; write "Warehouse managers face uneven demand patterns that create staffing conflicts."
Stage assignment: Stage 1 detects (structure: "X is [importance claim] for Y"), Stage 2 removes (announcement opener remover), Stage 4 Pass B audits (checklist item 12).

**P32 · Modal Hedging on Empirical Facts**
What AI does: Hedges measured results uniformly. "The model may achieve 95% accuracy." "Results suggest the approach could show improvement."
What humans do: State results directly with numerical evidence. Hedge on methodology limits and interpretation scope — never on confirmed, measured findings.
Human examples: "CatBoost achieved the best performance (RMSE: 0.096–0.109)." / "The results show 1% statistical significance for the 30-minute rebalancing."
Pattern rule: If a sentence contains a measured metric/number/statistic/percentage AND a modal verb → remove the modal. Confidence is expressed through numerical precision, not through "may/might/could/appears to".
Corpus evidence: Zero modal verbs in result sentences containing numerical data across all 56 papers.
Fix: For any sentence with [number/statistic/metric] + [may/might/could/appears/suggests/indicates] → remove the modal, state directly.
Stage assignment: Stage 1 counts "modal hedging on result sentences", Stage 3 modal hedging auditor removes them, Stage 4 Pass B audits (item 13), Stage 5 measures modal hedging on results ratio (target: 0%).

**P33 · But:However Ratio Inversion**
Critical discriminator: The ratio of "But" to "However" is a highly reliable discriminator between human and AI academic writing.
Human baseline (from 56 papers): But/but: 33–101 per thesis. However: 8–46 per thesis. Ratio: 2:1 to 4:1.
AI baseline: However used frequently as "safe formal alternative". But avoided in body text (considered informal). However:But ratio ≈ 3:1 to 5:1 (inverted).
Fix: In humanized output, "But" should appear at sentence beginnings at least twice as often as "However". Convert excess "However" to "But" or direct continuation.
Stage assignment: Stage 1 computes ratio, Stage 2 connector rebalancer enforces ≥ 2:1, Stage 4 Pass B audits (item 14), Stage 5 measures ratio (target: ≥ 2:1, red line: < 1:1).

**P34 · Rhetorical Questions as Argument Pivot Markers**
Corpus evidence: Present in social science (4–12 per text), rare in management (1–3), absent in math/IT.
Function: Signal a conceptual shift; invite reader to think; disrupt uniform declarative flow.
Domain distribution: Sociology/political science: 1–2 per 750 words at argument pivot points. IT/math/technical: 0–1 per entire document. Journalistic: 1 per 500–750 words.
Fix: At argument pivot points, convert the pivot's opening declaration into a rhetorical question if domain allows. "This raises the question of what constitutes authentic engagement." → "But what constitutes authentic engagement in this context?"
Stage assignment: Stage 4 Pass A injects domain-appropriate rhetorical questions at topic-shift points.

**P35 · Jargon Definition Pattern — Parenthetical Embedding**
What AI does: Creates standalone definition sentences. "X is defined as...", "By X we mean...", "It is important to note that X refers to..."
What humans do: Embed definitions in parentheticals or functional descriptions. "Google Colab (full name – Google Colaboratory) is a development environment..." / "the replicating portfolio [which converts to real market orders]"
Corpus evidence: Zero standalone "X is defined as..." sentences across all 56 papers. Every definition is embedded in use.
Fix: Find sentences matching "X is defined as [definition]." → take the term, embed the definition in parenthetical inside the first sentence that uses the term, delete the standalone definition sentence.
Stage assignment: Stage 3 detects and converts standalone definitions. Stage 5 measures standalone definition count (target: 0).

**P36 · Results Presentation Without Evaluative Praise**
What AI does: States results + evaluative praise. "CatBoost showed remarkable performance, demonstrating the power of ensemble methods."
What humans do: Result + comparison to baseline + mechanism. No praise. "CatBoost achieved the best performance (RMSE: 0.096–0.109). Hybrid models improved medium-term accuracy by capturing seasonality."
Pattern template for human result presentation: (1) What achieved (direct statement, no modal), (2) Numerical evidence if available, (3) Compared to what (baseline or prior approach), (4) By what mechanism. NEVER: evaluative adjectives on results; "demonstrates the X of Y" generalizations.
Fix: Convert praise-wrapped results to fact + mechanism format. "achieved remarkable results" → "achieved 0.096 RMSE (vs 0.15 baseline)"
Stage assignment: Stage 4 Pass A converts, Stage 4 Pass B audit asks: "Do any result sentences use evaluative adjectives (remarkable, impressive, exceptional, outstanding)? Replace with the mechanism."

**P37 · Section-Level Asymmetry**
Corpus data (representative thesis): Introduction ~3,500 words. Literature Review ~8,000 words (2.3× intro). Framework chapter ~2,500 words (shorter than intro). Cases chapter ~4,500 words. Conclusion ~800 words.
Pattern: Literature/theory section is 2–4× the length of any other section. Conclusion is consistently the shortest. Methodology is brief and dense. AI produces roughly equal sections (~700–1,000 words each).
Fix: Sections within a document must be different lengths. Flag if conclusion > 20% of body length (AI equalizes; humans compress conclusions).
Detection: Section token-count CV (target: ≥ 0.30, red line: < 0.20).
Stage assignment: Stage 1 computes section CV, Stage 2 section asymmetry enforcer flags imbalances, Stage 5 measures CV.

**P38 · Attribution-Based Hedging**
What AI does: Hedges claims with isolated modal verbs. "This may suggest that small states tend to seek alliances." "The data could indicate an upward trend."
What humans do: Hedge by naming the source; the attribution carries the epistemic weight. "According to Keohane (1969), small states can be shadows of their larger counterparts." "Gvalia et al. (2013) suggest this could tip the scales." (Attribution + one modal is acceptable; isolated modals without attribution are the signal.)
Fix: When a hedged claim has no attribution — either (a) add source attribution in format [Year] [Author/Institution] [verb] [finding], or (b) if no source exists, remove the hedge and state directly.
Stage assignment: Stage 3 attribution-based hedging converter. Stage 5 isolated modal density metric (target: < 0.5 per 300 words without attribution).

**P39 · Counter-Argument Integration**
What AI does: Creates isolated "Counter-argument" or "Limitations" section with anonymous attribution ("Some critics argue...").
What humans do: Name opposing scholars and weave counter-arguments into analytical prose. "Keohane (1969) argues X. Höll (1983) notes that small states minimize risks by..." — contention surfaced through named attribution.
Fix: If a paragraph begins "Some critics argue..." or "However, opponents..." → convert to named attribution: "[Author, Year] contests this, arguing that..." If no specific author available, convert to acknowledged limitation instead of anonymous counter-argument.
Stage assignment: Stage 4 Pass A counter-argument weaving. Stage 4 Pass B audit: "Are all counter-arguments attributed to named scholars?"

**P40 · Connector Scarcity as Baseline**
Corpus measurement: Technical/IT papers: 0.36 explicit connectors per page (human). AI baseline: 0.8–1.2 per page. Management/Politics/Social Science: 0.5–1.2 per page (higher for humanities due to argumentative nature). "Also" used 29–63 times per text — equivalent to 0.15–0.35 per page. "Also" is not a formal connector; it reads naturally. AI rarely uses "Also."
Target connector mix per page: But/Yet/Though (informal contrast): 0.15–0.40. However (formal contrast): 0.05–0.20. Also (informal addition): 0.10–0.25. Thus/Therefore (logical consequence): 0.03–0.10. Moreover (formal addition): 0–0.05. Furthermore: 0–0.01. Additionally: 0 (absolute ban).
Stage assignment: Stage 2 connector audit classifies all connectors by type and replaces banned ones. Stage 5 connector density per page metric with target ranges.

**P41 · Domain Epistemological Norm Adherence (Meta-Pattern)**
The most profound finding from corpus analysis: Human writing follows its domain's epistemological conventions. AI generalizes across domains. This is the deepest discriminator between authentic human and AI academic writing.
Domain-specific norms confirmed by corpus:
- Mathematics: "we" used 52–94 times (collaborative proof voice, always). Zero hedging on proven results (theorems are true, not "probably true"). Citation density: 0–3 per 20 pages.
- IT/Computer Science: Heavy passive voice is STANDARD ("the model is trained", "parameters are tuned"). Algorithm names used as proper nouns. Results with confidence intervals and comparison baselines. Citation density: 2–8 per 20 pages.
- Economics: Named identification strategy (gravity model, IV regression, DiD). Empirical strategy with explicit causal reasoning. Hypothesis statements numbered and testable. Citation density: 5–15 per 20 pages.
- Management: "Key", "crucial", "important" appear frequently in business context — acceptable. Case study parallel structure is domain convention, not AI tell. Citation density: 5–15 per 20 pages.
- Social Science: Hedging density is HIGH (11–37 per text) — appropriate for empirical claims. Rhetorical questions used for engagement (4–12 per text). Citation density: 5–10 per 20 pages.
- Linguistics/Humanities: Parenthetical asides VERY high (49–116 per 20 pages) — definitional and methodological. Long sentences for concept explanation (avg 34 words). Citation density: ~10 per 20 pages.
Implementation: Stage 1 domain classifier output gates all downstream stage operations. New config parameter: domain_mode.

**P42 · Citation Density Calibration by Domain**
Corpus data: Law/Urban Studies: 50+ citations per 20 pages. Linguistics: ~10. Social Science: 5–10. Management/Economics: 5–15. IT/CS: 2–8. Pure Mathematics: 0–3.
AI behavior: Roughly uniform citation density across domains, or over-citing general claims.
Human behavior: Citation density reflects domain epistemology. Math needs no citations for proofs. Law needs citations for every claim. AI's uniform density is a structural tell.
Fix: After domain classification, check citation density. If in high-citation domain and citations are sparse → add attribution to key claims. If in low-citation domain and citations are dense → remove redundant ones.
Stage assignment: Stage 4 Pass A citation density adjustment. Stage 5 citation density metric checked against domain baseline.

**P43 · "Also" as Natural Additive Connector**
Corpus discovery: "Also" appears 29–63 times per text in Management and Politics papers — MORE frequent than "Moreover" (1–25) or "Additionally" (0–13). Yet "Also" is not in any detection banlist.
Why "Also" signals human writing: AI avoids "Also" for addition because it considers it too informal. AI defaults to "Moreover", "Furthermore", "Additionally" as formal alternatives. Humans use "Also" freely as it flows naturally in academic prose without sounding stiff.
Rule: In academic and semi-formal outputs, "Also" should be a primary additive connector. Target: 0.10–0.25 per page. If output has 0 instances of "Also" → inject at appropriate points.
Stage assignment: Stage 2 connector rebalancer includes "Also" as a target output connector. Stage 4 Pass A "Also" injection when count is 0. Stage 5 "Also" frequency metric (target: ≥ 0.08 per page in academic text; red line: 0 in ≥ 500-word academic text).

---

## File Structure

```
ai-anti-plag/
├── CLAUDE.md                  # This file
├── README.md                  # Human-facing overview
├── config.yaml                # Pipeline parameters (thresholds, model names)
├── .env                       # API keys — NEVER commit this
├── pipeline/
│   ├── __init__.py            # Pipeline orchestrator; run() + run_from_params()
│   ├── analyzer.py            # Stage 1: analysis + pattern scan
│   ├── structural_rewriter.py # Stage 2: patterns 8–10, 12–16 + language gates
│   ├── lexical_enricher.py    # Stage 3: patterns 1–7, 11, 17–18 + language gates
│   ├── discourse_shaper.py    # Stage 4: two-pass voice injection + language gates
│   ├── scorer.py              # Stage 5: scoring + pattern rescan
│   ├── generator.py           # Phase 0B: AcademicGenerator (megaprompt-based)
│   ├── source_finder.py       # Phase 0A: SourceFinder (GOST bibliography + API validation)
│   ├── formatter.py           # Word (.docx) export (GOST + free formatting)
│   └── example_loader.py      # Few-shot human example loader for Stage 4
├── prompts/
│   ├── domain_classifier.md   # Stage 1 domain classification prompt
│   ├── structural_rewrite.md  # Stage 2 prompt template
│   ├── lexical_enrichment.md  # Stage 3 prompt template
│   ├── voice_injection.md     # Stage 4 Pass A prompt template
│   ├── audit.md               # Stage 4 Pass B audit prompt
│   ├── modal_hedging_audit.md # Stage 3 modal hedging sub-prompt
│   ├── result_presentation.md # Stage 4 result format sub-prompt
│   ├── connector_rebalancer.md # Stage 2 connector rebalancing sub-prompt
│   ├── source_discovery.md    # Phase 0A source generation prompt
│   └── academic_megaprompt.md # Phase 0B full academic writing system prompt
├── skills/                    # GitHub-imported skill modules
│   └── humanizer/             # git clone https://github.com/blader/humanizer
├── tests/
│   ├── test_pipeline.py       # Full unit + integration tests (87 + 22 new)
│   ├── fixtures/              # Sample AI-generated texts for testing
│   └── expected/              # Gold-standard humanized outputs for regression tests
├── scripts/
│   ├── benchmark.py           # Runs full pipeline on fixture set, prints score table
│   └── generate_and_humanize.py  # CLI entry point (generation + humanization)
└── outputs/                   # Per-run output directory (auto-created)
    └── [timestamp]_[topic]/
        ├── 01_sources.json    # Source list with verification status
        ├── 02_generated.txt   # Phase 0 raw output
        ├── 03_analyzed.json   # Stage 1 report
        ├── 04_structural.txt  # Stage 2 output
        ├── 05_lexical.txt     # Stage 3 output
        ├── 06_humanized.txt   # Stage 4 final text
        ├── result.docx        # Word file (GOST or free formatting)
        ├── score_report.json  # Stage 5 metrics (machine-readable)
        └── score_report.txt   # Stage 5 Rich table (human-readable)
```

---

## Development Conventions

- Python type hints on all function signatures.
- Each pipeline stage is a class implementing a `transform(text: str) -> str` interface.
- Configuration values come from `config.yaml`, never hardcoded.
- Each stage must have a `score(text: str) -> dict` method returning its relevant metrics.
- No side effects in transform functions — pure text-in, text-out.
- Prompt templates live in `/prompts/`, never inline in Python files.
- Use `loguru` for logging. Each stage logs: input length, output length, elapsed time, patterns found/eliminated.

### Testing

Run tests: `pytest tests/`
Run benchmark: `python scripts/benchmark.py`

New pipeline stages require:
1. A unit test in `tests/test_pipeline.py`
2. At minimum 3 fixture inputs in `tests/fixtures/`
3. Scores logged to stdout with `--verbose` flag

### Environment Setup

```bash
pip install -r requirements.txt
# Set ANTHROPIC_API_KEY in .env
# Install Humanizer skill for interactive use:
git clone https://github.com/blader/humanizer ~/.claude/skills/humanizer
```

Never commit `.env` or any file containing API keys.

---

## Domain Terminology

| Term | Definition |
|---|---|
| **Perplexity** | Measure of how "surprised" a language model is by a text. Higher = more unexpected word choices = more human-like. Measured with GPT-2. |
| **Burstiness** | Variance in sentence length. High burstiness mimics human writing rhythm. Measured as coefficient of variation of sentence token counts. Target: >= 0.45. |
| **Statistical fingerprint** | The token transition probability distribution that detectors model. Surface rewrites preserve it; deep rewrites change it. |
| **Register** | The formality level and stylistic conventions of a domain (academic, journalistic, casual). Must be preserved through the pipeline. |
| **Humanization** | The full transformation process: structural + lexical + discourse rewrites to make AI text indistinguishable from human writing. |
| **Soul requirement** | The explicit requirement to inject personality — opinions, reactions, uncertainty, specificity — beyond just removing AI patterns. Voiceless writing is as detectable as raw AI output. |
| **Two-pass audit** | Humanizer's core method: Pass A removes patterns + injects voice; Pass B asks "what still makes this obviously AI?" and rewrites remaining tells. |
| **Copula avoidance** | AI tendency to replace "is/are/has" with elaborate constructions ("serves as", "stands as", "boasts"). A strong AI signal. |
| **Elegant variation** | AI tendency to cycle synonyms for the same entity to avoid repetition (protagonist → main character → central figure). Creates unnatural rhythm. |
| **AI vocabulary** | The 21 high-frequency post-2023 words that strongly co-occur in AI writing (additionally, crucial, pivotal, vibrant, etc.). See Pattern P7. |
| **Bypass rate** | Percentage of outputs that score below a detector's AI classification threshold (typically 20%). |
| **Chunking** | Splitting input text into overlapping 200–400 word segments for LLM processing while maintaining coherence. |
| **Detector probe** | Calling a detection API (GPTZero, Copyleaks, etc.) programmatically. Use sparingly to avoid rate limits. |
| **Paragraph burstiness** | Variance in paragraph length (token count per paragraph). Target CV >= 0.50. Companion to sentence-level burstiness. |
| **Connector monotony** | Repeated use of additive transition words (Furthermore, Moreover, Additionally). Detected by connector frequency per 300 words. See P29. |
| **Register inflation** | AI tendency to default to formal latinate vocabulary (utilize, facilitate, leverage) when plain equivalents exist. See P28 substitution table. |
| **Imperfection texture** | Deliberate roughness in output: parenthetical asides, fragments, register drops, discourse markers, epistemic hedging. Signals human authorship. See P30. |
| **Structural asymmetry** | Deliberate variation in paragraph size, argument order, and section structure. Opposite of AI's default symmetric scaffold. |
| **Announcement pattern** | AI tendency to state what it is about to say before saying it ("This section will explore..."). Sub-pattern of P9 and P22; always delete. |
| **Epistemic hedging** | Natural human qualification of uncertain claims: "probably," "roughly," "it seems," "as far as I can tell." AI writes with false certainty; hedging is a positive human signal. See P30. |
| **Abstraction altitude** | The level of specificity in a claim — from abstract generalizations to concrete examples. Human writing oscillates; AI text tends to stay at one level. See P26. |
| **Importance-framing** | AI tendency to preface statements with claims about their importance ("plays a crucial role") before stating the actual content. Always delete the framing; state the content directly. See P7 importance-framing banlist. |
| **But:However ratio** | The ratio of "But" to "However" as sentence-initial contrast connectors. Human academic text: ≥ 2:1. AI text: ≤ 1:1 (inverted). The ratio is a highly reliable discriminator. See P33. |
| **Modal hedging on results** | AI tendency to hedge measured, empirical findings with modal verbs ("may achieve", "could indicate"). Human writers state results directly when numbers are present; modals appear only on interpretation and methodology. See P32. |
| **Domain epistemological norms** | The writing conventions specific to an academic discipline: math uses collaborative "we" and zero hedging on proofs; CS preserves passive voice; management accepts P7 words in context. AI generalizes across domains; humans follow their discipline's standards. See P41. |
| **Section asymmetry** | Natural variation in section length within a document. Human baseline: literature/theory sections are 2–4× longer than methodology sections; conclusion is the shortest. AI produces roughly equal sections. See P37. |
| **Citation density calibration** | Domain-appropriate frequency of citations per page. Law: 50+ per 20 pages. Pure math: 0–3. AI produces uniform density across domains. See P42. |
| **"Also" frequency** | The natural additive connector "Also" appears 29–63 times per thesis in human academic text but is avoided by AI (which prefers "Moreover"/"Additionally"). Absence of "Also" in academic text is an AI signal. See P43. |
| **Attribution-based hedging** | Human writers hedge uncertain claims by naming the source ("[Year] [Author] suggests..."), not by stacking modal verbs. The attribution carries epistemic weight; isolated modals without attribution are an AI signal. See P38. |
| **Information-first posture** | Human writing states content directly; importance is demonstrated by the facts. AI announces importance before stating content. Zero instances of importance-framing found in 56 analyzed human papers. See P31. |

---

## Working with Claude on This Project

### Prompt Design Principles

When drafting LLM prompts for pipeline stages:
- Always specify the **register** and **target reader profile** in the system prompt (e.g., "second-year PhD student in economics", not just "academic").
- Instruct the model to **preserve all factual claims** — only rewrite style, not content.
- Explicitly forbid the full AI vocabulary banlist: P7 original 21 words + P7 extended list + P7 importance-framing banlist + P7 paired-abstraction banlist + P28 substitution table.
- Forbid generic transitions: the full P29 banned connector list (Furthermore, Moreover, Additionally, Firstly, Secondly, Thirdly, Finally, etc.).
- Ask for **one specific transformation per prompt call** — do not combine stages.
- Include a **negative constraint example** in the prompt when introducing a new stage.
- For Stage 4 prompts: require the two-pass audit structure (Pass A transform, Pass B 9-point checklist).
- Require personality: opinions, acknowledgment of uncertainty, first-person where appropriate.
- **Require structural asymmetry**: output must NOT have uniform paragraph lengths or symmetric argument structure. Instruct the model to produce paragraphs of visibly different sizes.
- **Require conciseness**: target <= 90% of input word count. Padding is an AI signal; cutting is human.
- **Forbid announcement patterns**: "This section will...", "In what follows...", "We will now examine..." must never appear in output.
- **Require the auditory test instruction** in Stage 4 prompts: "Read this aloud mentally. Flag any sentence that sounds like a robot reading from a script."
- **Require figurative language check** in Pass B: "Does this text contain at least one concrete analogy or metaphor per section? If not, add one that fits naturally."
- **Require active voice as default**: flag any passage where passive constructions exceed 20% of sentences; rewrite with named agents unless awkward.
- **HARD BAN on triplets**: every rewrite stage prompt must include: "Never produce exactly three items in any list or series — noun list, verb series, or adverbial parallel ('partly to X, partly to Y, partly to Z'). Use two or four. Any three-item parallel structure is a hard failure." This is the single strongest typographic AI signal.
- **HARD BAN on announcement openers**: every rewrite stage prompt must include: "The following constructions must never appear in output — 'Here's the problem with X', 'There's also a X worth flagging', 'X is worth a brief detour', 'One thing you rarely see is X', 'X also deserves mention', 'X is instructive about Y', 'I mention this mostly because'. Delete and state the content directly."
- **HARD BAN on 'genuinely [adjective]' constructions**: "'Genuinely unprecedented', 'genuinely substantial', 'genuinely important' are AI signals. Delete 'genuinely' and replace the vague adjective with a specific fact or figure."
- **Paragraph-ending rule**: every rewrite stage prompt must include: "Every paragraph must end on its most specific, concrete data point — not an abstract lesson or generalization extracted from the facts. If the final sentence of a paragraph generalizes or broadens the paragraph's implicit thesis, delete it."
- **Require meaning-first rewriting**: Stage 4 prompts must instruct the model — "Before rewriting any passage, read 2–3 sentences, internalize what they mean, set the original aside mentally, and write from your understanding of the meaning. Do NOT edit word-by-word. Surface editing preserves the AI structural mold even when vocabulary changes. Deep meaning-first rewriting breaks it."
- **Require epistemic hedging audit** in Pass B: "Does the text write with false certainty on estimated or contested claims? If so, add appropriate hedging: 'probably,' 'roughly,' 'it seems,' 'as far as available data show.' Humans hedge naturally; AI writes with false precision."
- **Require tense variation check**: flag any passage where >80% of verbs share the same tense. Mix at least one past-tense historical claim, one present-tense general principle, and — where context allows — one conditional or future projection per major section.
- **23. HARD RULE — Information-First**: "Every sentence must do something, not announce it. Delete any sentence that describes what the following sentence will do or how important it is. Begin with the content. 'Resource optimization is crucial' → delete; write 'Warehouse managers face uneven demand that creates staffing conflicts.' The data demonstrates importance; the sentence must not announce it."
- **24. HARD RULE — No modal hedging on results**: "If a sentence contains a number, statistic, measured metric, percentage, or reported finding — remove all modal verbs (may, might, could, appears to, suggests, indicates). State the result directly. Express confidence through numerical precision, not through 'may achieve'. Hedge on: methodology limits, interpretation scope, contested claims. Never hedge on: measured outcomes."
- **25. REPEAT KEY TERMS — Never synonym-cycle**: "Identify the 5 most important technical or analytical terms in this text. Repeat them identically every time they appear. Do NOT substitute synonyms. If you wrote 'entry mode' 15 times, keep writing 'entry mode'. Synonym cycling is the primary signal of AI repetition-penalty behavior."
- **26. BUT:HOWEVER RATIO — Target 2:1 or higher**: "For every formal 'However' at sentence start, you must use 'But' or 'Yet' at least twice. 'But' is the primary human contrast connector; 'However' is the primary AI contrast connector. The ratio is diagnostic."
- **27. ATTRIBUTION-BASED HEDGING**: "For uncertain or contested claims, hedge by naming the source, not by stacking modal verbs. '[Year] [Author] suggests...' not '[Claim] may suggest...'. The attribution carries the epistemic weight. Isolated 'may/might/could' on contested claims without attribution is an AI signal."
- **28. SOURCE EVALUATION**: "After every 2 citations, add one sentence explaining specifically why that finding matters for THIS argument. Not 'This shows the importance of X generally' but 'Smith's 2019 cohort matches our sample structure exactly, making their findings directly applicable.' Connect the source to the argument explicitly."
- **29. RESULTS PRESENTATION FORMAT**: "For empirical results: (a) state directly with no modal, (b) provide comparison to baseline, (c) state the mechanism that produced the result. Never: evaluative praise (remarkable, exceptional). Template: '[Result achieved]. [Baseline comparison]. [Mechanism — by capturing / because / which captures].'"
- **30. DOMAIN CONVENTIONS**: "Before transforming any text, identify its domain (CS, economics, management, linguistics, math, social science). Apply domain-appropriate rules: math uses 'we' throughout and zero hedging on proofs; CS preserves passive voice; management accepts 'crucial' and 'key' in context; social science requires epistemic hedging on empirical claims; linguistics uses parenthetical asides extensively."

### Claude's Role

- Claude writes and reviews all pipeline stage code.
- Claude drafts and refines all prompt templates in `/prompts/`.
- Claude runs benchmarks and interprets score tables.
- Claude does NOT call external detector APIs unless explicitly asked.
- Claude should flag if a proposed technique is known to be ineffective (e.g., simple synonym swapping, surface-level paraphrase without voice injection).
- Claude can use `/humanizer` interactively to test humanization of sample text before implementing a stage in Python.

### Context Management

Use `/clear` between working on separate pipeline stages to prevent context bleed. Each stage is independent.

Before writing any new pipeline stage: ask Claude to design the class interface, identify edge cases, and propose the prompt template first — before implementation.

---

## Skills and Modules

| Skill / Module | Source | Status | Purpose |
|---|---|---|---|
| `humanizer` | github.com/blader/humanizer | Active — install to `~/.claude/skills/` | Interactive two-pass humanization; 30-pattern knowledge base |

Installation:
```bash
git clone https://github.com/blader/humanizer ~/.claude/skills/humanizer
```
Usage in Claude Code: `/humanizer` — paste text to humanize interactively.

The Humanizer skill is the **interactive companion** to the automated pipeline. Use it to:
1. Quickly test how a piece of text reads after humanization before building the pipeline stage
2. Verify that a pipeline stage's output still has remaining tells (compare with skill output)
3. Generate "expected" gold-standard outputs for `tests/expected/` fixtures

When additional skills are added from GitHub:
1. Place them in `skills/[skill-name]/`.
2. Add an entry to this table with source URL and purpose.
3. Write a wrapper in the relevant pipeline stage conforming to `transform(text: str) -> str`.
4. Add tests in `tests/test_pipeline.py`.

---

## Category 8 — GPTZero Scaffold Patterns (Live-Test Validated)

These patterns were identified through live GPTZero testing (February 2026). They represent argumentative **scaffold signals** — structural and rhetorical constructions that detectors flag even when all vocabulary patterns are clean. Two rounds of testing reduced AI probability from 100% → 87%; these patterns account for the remaining 87% detection.

**Critical insight**: GPTZero 2026 detects the *way arguments move*, not just word choices. Thesis→evidence→synthesis applied consistently is a scaffold fingerprint regardless of vocabulary. The fix is not more paraphrasing — it is destroying the scaffold architecture itself.

---

**P44 · Superlative Importance Opener**
Pattern: Opening sentences that use superlative framing to establish a claim's significance: "The most consequential economic decision since X", "The biggest shift in Y in a generation", "The most significant X since Y."
Why detected: GPTZero specifically flags superlative-importance construction at sentence-initial position. This is distinct from P1 (which covers body-text significance inflation) — openers carrying superlative claims are a separate, stronger signal because human journalists rarely open with explicit importance ranking.
Fix: NEVER open a piece with a superlative claim about significance. Open with a specific mundane fact, a mid-argument observation, or a named person/event in media-res. "The most consequential economic decision in the Middle East since October 2023" → "Saudi Arabia pumped 9.7 million barrels a day in January. That number has barely moved in four months."
Stage assignment: Stage 4 Pass B checklist item (ask: does the opening sentence rank importance? If so, replace with a flat specific fact).

**P45 · Two-Sentence Dramatic Reveal**
Pattern: A short, declarative sentence followed immediately by a reversal or reveal: "X wasn't made in Riyadh or Washington. It was made in Tehran." / "This isn't about oil supply. It's about leverage." / "China didn't choose sides. It doesn't have to."
Why detected: The constructed pause between sentences mimics a rhetorical device that AI applies compulsively at dramatic moments. Human writers do use this occasionally, but AI uses it at every section pivot.
Fix: Collapse dramatic reveals into single sentences. "X wasn't A. It was B." → "X was B." Or rewrite as flowing exposition without the pause. Rate limit: 0 per 2000-word document in journalistic register. If the reveal structure is genuinely needed, use it at most once — never at the opening.
Stage assignment: Stage 2 detects (two consecutive short sentences ≤ 8 words where second contradicts first). Stage 4 Pass B audits. Stage 5 counts dramatic reveal structures (target: 0 per 2000 words).

**P46 · Meta-Media Commentary**
Pattern: AI commenting on how the topic is covered, how it appears in the news, or why it's underappreciated: "What did happen is harder to write headlines about", "This gets less attention than it deserves", "It rarely makes front pages but...", "The story that never quite gets told is...", "Beneath the geopolitical drama..."
Why detected: Human journalists write about the topic; they rarely write about their own writing or media coverage patterns. AI's meta-commentary signals that it is performing journalistic voice rather than actually exercising it.
Fix: Delete entirely. Never comment on coverage, headline-ability, or media attention. State the content directly without framing it as underreported or overlooked.
Stage assignment: Stage 3 detects meta-media phrases. Stage 4 Pass B checklist (ask: does any sentence reference how the topic is covered in media?). Target: 0 per document.

**P47 · Binary Future Force Projection**
Pattern: "Will eventually force either A or B", "The choice will be between X and Y", "Sooner or later, X will have to decide between A and B."
Why detected: Binary forced-choice future projections are an AI analytical posturing pattern. Human analysts hedge on future states and rarely construct neat either/or scenarios. The combination of certainty ("will") and binary structure ("either A or B") is a compound signal.
Fix: Hedge the future claim and break the binary. "Will eventually force either A or B" → "Could push toward A — or something messier that doesn't map neatly onto either." Rate limit: 0 clean binary future projections per document.
Stage assignment: Stage 4 Pass A (flag "will [eventually/ultimately] [force/require/demand/mean] either"). Stage 4 Pass B audit item. Stage 5 measures binary-future count (target: 0).

**P48 · Binary Neither Wrap-up**
Pattern: "Neither outcome is good for anyone relying on X", "Neither side benefits from Y", "Neither of these is a reassuring scenario."
Why detected: The "neither X nor Y" conclusion formula is an AI synthesis pattern — it creates the appearance of analytical balance by rejecting both poles simultaneously. Human writers land on the specific implication; AI summarizes with symmetrical rejection.
Fix: Delete the neither-wrap. End the paragraph on the most specific concrete data point instead of a symmetrical rejection of both scenarios. "Neither outcome is good for anyone relying on stable energy prices" → delete; end on the specific current metric that demonstrates instability.
Stage assignment: Stage 2 (remove neither-wrap as variant of P24). Stage 5 counts neither-wrap instances (target: 0).

**P49 · Elegant Reversal in Analytical Position**
Pattern: "What X is doing is A rather than B", "The question isn't X — it's Y", "Gulf states aren't switching allegiances; they're hedging them."
Why detected: AI uses reversal framing to signal analytical sophistication — presenting the naive interpretation, then correcting it. This is structurally identical to P9 (negative parallelism) but operates at the analytical-claim level rather than the sentence level. Detectors flag both the construction AND the regularity with which it appears.
Fix: State the analytical position directly without the "it's not X, it's Y" frame. "What Gulf states are doing is hedging rather than switching" → "Gulf states are hedging." Then explain the specific mechanism. The reversal frame is always expendable.
Stage assignment: Stage 2 (flag "What X is doing is A rather than B" constructions). Stage 4 Pass B audit. Target: 0 per document.

**P50 · Same-X-That-Also Construction**
Pattern: "The same geography that makes Gulf states capable of A also gives them B", "The same dynamic that X also creates Y", "The same relationship that A is also the reason B."
Why detected: This parallel causal attribution structure is a syntactic AI tell — it creates apparent analytical depth by linking two effects to one cause, but the construction itself is mechanical. Human writers typically separate the two claims into distinct sentences.
Fix: Split into two independent sentences. "The same geography that makes Gulf states capable of [A] also gives them [B]" → "Gulf states can [A] for geographic reasons. The same location also means [B]."
Stage assignment: Stage 2 detects "The same X that [clause] also [clause]" construction. Stage 5 counts instances (target: 0).

**P51 · Whether-Or-Just Closure**
Pattern: "Whether that creates durable deterrence or just a more complicated incentive structure", "Whether this represents genuine diversification or merely a hedge", "Whether X is a turning point or just a temporary adjustment."
Why detected: AI closes analytical sections with a "whether A or just more complicated B" formula that performs epistemic humility while actually providing no new information. The construction signals AI's inability to land on a conclusion — it retreats into a framing question rather than stating the most defensible position.
Fix: State the most defensible position directly, with hedging if warranted. "Whether X or just Y" → "Probably Y. X would require [specific condition that hasn't happened]." Or simply end on the concrete fact and let the reader draw the inference.
Stage assignment: Stage 4 Pass B (flag "whether [clause] or just [clause]" at section endings). Stage 5 counts instances (target: 0).

**P52 · Mechanism Attribution Run-on**
Pattern: Complex nested mechanism sentences: "[Subject] is a mechanism of [abstract domain] that [entity] is reshaping through [Y decisions] that [condition Z] rather than [alternative V]."
Why detected: AI constructs elaborate nested attribution sentences to demonstrate analytical complexity. These sentences are syntactically unusual — multiple dependent clauses chaining through a single subject. Human analysts break these into 2-3 sentences.
Fix: Break into component sentences. "[Subject] functions as [mechanism]. [Entity] is reshaping it through [Y decisions]. The effect is [condition Z], not [alternative V]."
Stage assignment: Stage 2 (flag sentences with 3+ nested "that" clauses). Stage 4 Pass B. Stage 5 measures nested-clause density (target: < 0.5 per 300 words).

**P53 · Participial Simultaneity**
Pattern: "while simultaneously managing", "while also navigating", "even as it simultaneously pursues", "managing X while simultaneously Y-ing Z."
Why detected: The "while simultaneously" construction is overused by AI to suggest multi-factor complexity. Human writers either separate the simultaneous actions ("Saudi Arabia is managing X. It is also navigating Y.") or use "while" alone without "simultaneously" (which is redundant).
Fix: Delete "simultaneously." If "while" construction remains, verify it doesn't appear more than twice per 500 words. Prefer two separate sentences when the two actions are genuinely distinct.
Stage assignment: Stage 3 (delete "simultaneously" after "while"; flag "while also" density). Stage 5 counts participial simultaneity constructions (target: 0).

---

## Formatting Fingerprint Rules (F1–F8)

These rules govern surface-level formatting signals that AI detectors use as secondary discriminators. They were validated through live GPTZero testing and reflect patterns distinct from the 43 structural/lexical patterns above. Apply to ALL registers unless stated otherwise.

**F1 · No Oxford Comma**
Rule: In lists of three or more items, omit the comma before "and" or "or" in the final item.
Before: "freight, fertilizer, and plastics"
After: "freight, fertilizer and plastics"
Exception: When omitting the comma creates genuine ambiguity. In that case, rewrite the sentence to avoid the list structure rather than adding the Oxford comma.
Stage assignment: Stage 2 and Stage 3 list-processing; Stage 4 Pass B formatting audit.

**F2 · Em Dash Limit**
Rule: 0 em dashes in ALL registers (academic, journalistic, essay). Replace every em dash with a comma, period, or restructured sentence. Em dashes are among the strongest single-character AI signals across all detector systems.
Rationale: GPTZero, Turnitin, and Copyleaks all flag em dash density. Human academic writers almost never use em dashes in body text; human journalists use them occasionally but far below AI output rates. The safest rule is complete elimination.
Fix: "The three-phase program produces results only if someone owns execution — not a technical problem but an organizational one." → "The three-phase program produces results only if someone owns execution. That is an organizational problem, not a technical one."
Stage assignment: Stage 2 (replace all em dashes; 0 remaining is the hard target).

**F3 · Semicolon Near-Ban (All Registers)**
Rule: 0 semicolons in journalistic, essay, and general writing. Near-zero in academic register: maximum 1 per 500 words, only when a period would genuinely misread (e.g., separating complex list items that themselves contain commas). Replace all other semicolons with periods.
Rationale: Semicolons are an AI formality signal across all registers. Human journalists never use them. Human academic writers use them sparingly; AI uses them structurally as a default clause connector. The "permitted in academic" exception has proven too permissive in practice.
Fix: "Chery operates eight global R&D centres, so the operational template already exists; expected effect: reduction of 30%." → "Chery operates eight global R&D centres, so the operational template already exists. Expected reduction: 30%." — or better, restructure to eliminate the colon too.
Stage assignment: Stage 2 (replace all semicolons with periods; flag any remaining for manual review; academic target is ≤ 1 per 500 words).

**F4 · Colon Reduction (All Registers)**
Rule: 0 colons in body paragraphs of journalistic/essay text. In academic register: maximum 1 colon per 300 words in body text, and never to introduce a prose list. Permitted in all registers: colons in numbered list items, table captions, figure captions, and section headers.
Rationale: Colons introducing inline lists ("four workstreams: routes and logistics, inventory...") are a strong AI structural signal in both journalistic and academic text. The "AI appearance" of colons was confirmed through user feedback and live GPTZero testing.
Fix (journalistic): "There are three reasons: X, Y, and Z." → "X is the first factor. Y and Z compound it."
Fix (academic): "The PMO coordinates four workstreams: routes and logistics, inventory and warehouse infrastructure, digitalization, and localization." → "The PMO coordinates four workstreams. These are routes and logistics, inventory and warehouse infrastructure, digitalization, and localization." — or restructure to prose without enumeration.
Stage assignment: Stage 2 (detect all colons in body sentences; in journalistic replace 100%; in academic replace >1 per 300 words and all that introduce prose lists; convert to prose).

**F4b · Parenthesis Minimization (All Registers)**
Rule: Maximum 1 parenthetical per 300 words in academic register. 0–1 per 500 words in journalistic/essay register. Never use parentheses when a comma, em-dash-free rewrite, or inline clause would work equally well.
Rationale: Frequent parenthetical brackets are an AI polish signal. AI uses them liberally to embed definitions, caveats, and abbreviation expansions mid-sentence. Human writers either integrate the information into the sentence flow or omit it entirely. Live user feedback confirmed parenthesis overuse is an AI-detectable marker.
Permitted uses: (a) Introducing an abbreviation on first use when the abbreviation appears 3+ more times in the document — place immediately after the term, once only. (b) P30-compliant parenthetical personality asides in journalistic register ("which, admittedly, is harder to verify") — maximum 1 per section.
Fix: "Below that, a Program Management Office (PMO) coordinates four workstreams: routes and logistics..." — if PMO is used 4+ more times, "(PMO)" at first use is permitted; the colon must still be removed per F4. Definition parentheticals like "(a government instrument through which a company commits to localization targets...)" → move the definition to a standalone sentence before or after, or integrate into the sentence: "companies commit to localization targets in exchange for tax preferences under a Special Investment Contract, or SPIC."
Stage assignment: Stage 3 (count parenthetical constructions; flag and convert excess to inline prose or separate sentences; Stage 4 Pass B checks parenthesis density).

**F5 · Missing Apostrophes (Controlled)**
Rule: In journalistic register, 3–5 instances per 2000 words where apostrophes are intentionally dropped on proper noun possessives and common contractions. Target: proper noun possessives first (Tehrans, Irans, Beijings, Russias), then occasional contractions (Theres, Irans, PIFs, Im).
Rationale: Perfect apostrophe use on every word is itself a machine-polish signal. Human writers miss apostrophes on long proper noun possessives and occasionally on contractions.
Rules: (a) Never drop apostrophes in ways that create real ambiguity. (b) Never drop from common short words where the error would be jarring (its/it's is too visible; avoid). (c) Spread across the document — not clustered.
Stage assignment: Stage 4 Pass A injects 3–5 controlled apostrophe drops; Stage 4 Pass B checks for clustering.

**F6 · Minor Grammar Errors (Controlled)**
Rule: 2–3 minor grammatical errors per 2000 words. Permitted types: (a) subject-verb agreement on compound noun phrases; (b) comma splice between closely related independent clauses; (c) missing article before a noun that technically requires one. Forbidden types: (d) wrong tense (too visible); (e) pronoun errors (too visible); (f) dangling modifier (too jarring).
Rationale: Perfect grammar across 2000 words is a machine-polish signal. The specific error types above mimic the real-world errors that educated human writers occasionally produce.
Rule: Never introduce errors that change meaning or make the sentence confusing on first read.
Stage assignment: Stage 4 Pass A injects 2–3 controlled errors of types (a)–(c); Stage 4 Pass B verifies no meaning degradation.

**F7 · Filler Words (Controlled)**
Rule: 2–4 filler words per 2000 words. Permitted: basically, honestly, actually (in P30-appropriate positions only). Not permitted: literally, totally, definitely, clearly (too visible as insertion artifacts).
Rationale: Filler words signal real-time thought. AI text has none because it produces polished output. Adding 2–4 authentic-feeling fillers lowers the machine-polish signal.
Placement rules: (a) At the start of a sentence expressing mild uncertainty or casualness. (b) Mid-sentence before an evaluative claim: "which is basically what happened." (c) Never in topic sentences or thesis statements. (d) Never stacked (two fillers in the same sentence).
Stage assignment: Stage 4 Pass A injects; Stage 4 Pass B checks for stacking and placement.

**F8 · No Hyphenated Creative Compounds**
Rule: 0 writer-invented hyphenated compounds per document in journalistic register. Convert to phrase form.
Before: "post-oil economy", "state-directed growth", "dollar-denominated trade"
After: "economy after oil", "growth directed by the state", "trade denominated in dollars" OR "trade settled in dollars"
Permitted: Standard dictionary hyphenated words (well-known, short-term, long-term when used as attributive adjectives).
Rationale: Invented hyphenated compounds are an AI register-elevation signal in journalistic prose.
Stage assignment: Stage 3 (flag hyphenated compounds not in a standard dictionary list; convert to phrase form).

---

## Prompt Design Principles — Continued (31–38)

**31. OPEN FLAT, NOT CLEVER**: "The first sentence must be a flat specific fact or mid-argument observation. Never open with a superlative importance claim ('the most consequential X since Y'), a dramatic two-sentence reveal, or a meta-media comment ('harder to write headlines about'). The opening sentence earns no special rhetorical weight — it simply starts."

**32. DESTROY THE SCAFFOLD**: "Do not apply thesis→evidence→synthesis in more than one section. For at least half the sections, either: (a) open with the conclusion and work backward, (b) open with a concrete case and never state the explicit generalization, or (c) present the complicating fact before the main claim. Consistent scaffold architecture is as detectable as vocabulary."

**33. NO DRAMATIC REVEALS**: "Never write a two-sentence dramatic reveal ('X wasn't A. It was B.'). Collapse to one sentence or rewrite as flowing prose. Rate: 0 per 2000-word document."

**34. NO META-MEDIA COMMENTARY**: "Never comment on how the topic is covered, how it appears in news, or why it's underappreciated. State the content directly. 'This gets less attention than it deserves' → delete and state what it is."

**35. NO BINARY FORCE PROJECTIONS**: "Never write 'will eventually force either A or B' or equivalent. Hedge the future: 'probably,' 'could,' 'might.' Break the binary: 'or something messier.' Clean binary forced-choice futures are an AI analytical posturing signal."

**36. NO ELEGANT REVERSALS**: "Never use 'What X is doing is A rather than B' or 'It's not about X — it's about Y.' State the position directly: 'X is A.' The reversal frame is always expendable."

**37. FORMATTING COMPLIANCE CHECKLIST**: "Before finalizing output, run this checklist: (a) Oxford comma present? Remove. (b) Em dashes: more than 2 per 500 words? Replace excess. (c) Semicolons present in journalistic text? Replace with periods. (d) Body-text colons present? Convert to prose. (e) Apostrophes: 3–5 controlled drops on proper noun possessives? Add if missing. (f) Grammar errors: 2–3 controlled types added? (g) Filler words: 2–4 present? (h) Invented hyphenated compounds present? Convert to phrase form."

**38. GREEN-SENTENCE PATTERN — INCREASE**: "In GPTZero testing, these sentence types were consistently NOT flagged: (a) data-dense factual sentences with no evaluative language; (b) first-person uncertainty statements ('I'm fairly confident that', 'my read is', 'I'd estimate'); (c) messy uncertain short paragraphs that resist clean summarization; (d) short choppy factual statements under 10 words. Increase frequency of these patterns to at least 20% of sentences per section."

---

## Key Constraints and Risks

- **Detector arms race**: GPTZero and Turnitin update frequently. Design for reconfigurability — not hardcoded hacks. Pattern-based removal is more durable than detector-specific bypasses.
- **Voiceless text trap**: Removing all 30 patterns without injecting personality produces sterile, robotic-but-clean text that is equally detectable. The soul requirement is mandatory.
- **Coherence degradation**: Aggressive structural rewriting can break logical flow. The scoring stage must catch this.
- **Register drift**: Lexical enrichment can shift register (e.g., making academic text sound casual). Enforce register constraints in all prompts.
- **Chunk boundary artifacts**: Overlapping chunks can create repetition at join points. Final pass must detect and remove duplicate sentences at boundaries.
- **Rate limits**: Claude API has rate limits. Build retry logic with exponential backoff into every API call.
- **Evaluation bias**: Automated scores (perplexity, burstiness, pattern count) are proxies — periodically run human evaluation on a sample of outputs.
- **Structural symmetry trap**: Even after vocabulary and pattern cleanup, text with uniform paragraph lengths and predictable argument ordering still scores high on AI detectors. Stage 2's structural operations must verify paragraph-CV >= 0.50 before passing to Stage 3.
- **Over-imperfection backfire**: Injecting too many parenthetical asides, fragments, and colloquialisms in Stage 4 risks register drift and coherence degradation. Apply P30 at a rate of no more than 2 imperfection textures per 300-word passage; the scoring stage must catch coherence drops below 4/5.
