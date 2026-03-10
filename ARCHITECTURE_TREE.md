# AI Anti-Anti Plag — Архитектура агентной системы v3.1 FINAL (82 компонента)

```
CEO Agent (agents/ceo.py)
│
│   mode == "generation"  → Content Manager → Handoff Gate → Humanizer Manager → Export
│   mode == "humanization" → Humanizer Manager → Export
│   Escalation: HM-5 fail после 2 итераций → CEO решает
│
├── Content Manager (agents/content/manager.py)
│   │
│   │   1. SourceFinderService.find() — ПЕРВЫЙ вызов
│   │   2. state.source_list = source_list
│   │   3. mm = _get_micro_manager(stream_id)
│   │   4. state = mm.execute(state)
│   │
│   ├── MM VKR (agents/content/micro_managers/mm_vkr.py)
│   │   │   SECTION_ORDER: title_page → annotation → toc → intro → ch1 → ch2 → ch3 → conclusion → references
│   │   │   VIZ_MINIMUMS: bachelor=5, master=8
│   │   │
│   │   ├── vkr_title_page.py
│   │   ├── vkr_annotation.py
│   │   ├── vkr_toc.py              ← 2-pass: placeholder → update after all sections
│   │   ├── vkr_introduction.py
│   │   ├── vkr_chapter_1.py
│   │   ├── vkr_chapter_2.py
│   │   ├── vkr_chapter_3.py
│   │   ├── vkr_conclusion.py
│   │   └── vkr_references.py       ← форматирует source_list в ГОСТ
│   │
│   ├── MM Coursework (agents/content/micro_managers/mm_coursework.py)
│   │   │   SECTION_ORDER: title_page → toc → intro → ch1 → ch2 → conclusion → references
│   │   │   VIZ_MINIMUMS: 3-6
│   │   │
│   │   ├── cw_title_page.py
│   │   ├── cw_toc.py
│   │   ├── cw_introduction.py
│   │   ├── cw_chapter_1.py
│   │   ├── cw_chapter_2.py
│   │   ├── cw_conclusion.py
│   │   └── cw_references.py
│   │
│   ├── MM Research (agents/content/micro_managers/mm_research.py)
│   │   │   SECTION_ORDER: annotation → intro → lit_review → methodology → results → discussion → conclusion → references
│   │   │   VIZ_MINIMUMS: 3-8
│   │   │
│   │   ├── res_annotation.py
│   │   ├── res_introduction.py
│   │   ├── res_literature_review.py
│   │   ├── res_methodology.py
│   │   ├── res_results.py
│   │   ├── res_discussion.py
│   │   ├── res_conclusion.py
│   │   └── res_references.py
│   │
│   ├── MM Abstract Paper (agents/content/micro_managers/mm_abstract_paper.py)
│   │   │   SECTION_ORDER: title_page → toc → intro → ch1 → conclusion → references
│   │   │   VIZ_MINIMUMS: 1-3
│   │   │
│   │   ├── ap_title_page.py
│   │   ├── ap_toc.py
│   │   ├── ap_introduction.py
│   │   ├── ap_chapter_1.py
│   │   ├── ap_conclusion.py
│   │   └── ap_references.py
│   │
│   ├── MM Text (agents/content/micro_managers/mm_text.py)
│   │   │   SECTION_ORDER: ["full"] — single generation
│   │   │   Выбирает подтип по state.text_subtype
│   │   │
│   │   ├── text_analytical.py
│   │   ├── text_journalistic.py
│   │   ├── text_review.py
│   │   └── text_descriptive.py
│   │
│   ├── MM Essay (agents/content/micro_managers/mm_essay.py)
│   │   │   SECTION_ORDER: ["full"] — single generation
│   │   │
│   │   └── essay_full.py
│   │
│   └── MM Composition (agents/content/micro_managers/mm_composition.py)
│       │   SECTION_ORDER: ["full"] — single generation
│       │
│       └── comp_full.py
│
├── [Handoff Gate] (agents/gates/handoff_gate.py)
│       Передаёт: text + domain + register + language + source_list + viz_count
│       Content Manager → Humanizer Manager
│
├── Humanizer Manager (agents/humanizer/manager.py)
│   │
│   │   Pipeline: HM-1 → HM-2 → QA → HM-3 → QA → HM-4 → QA → HM-5
│   │   Feedback: HM-5 → route to HM-2/HM-3/HM-4 (max 2 iterations)
│   │   Smart Worker Skip: HM-1 analysis → skip workers с 0 violations
│   │
│   ├── HM-1 Diagnostician (agents/humanizer/stages/hm1_diagnostician.py)
│   │   │   Wraps: analyzer.score() → 20 метрик + pattern scan
│   │   │   Модель: LOCAL (без API)
│   │   │
│   │   ├── hm1_pattern_scanner.py     ← P1-P53 сканер (via Pattern Scanner SS)
│   │   ├── hm1_metrics_engine.py      ← Perplexity, CV, ratios (local)
│   │   └── hm1_domain_classifier.py   ← domain + register → Domain Gate
│   │
│   ├── HM-2 Architect (agents/humanizer/stages/hm2_architect.py)
│   │   │   Wraps: structural_rewriter.transform()
│   │   │   Модель: Sonnet | ~83 chunks × 4 workers
│   │   │
│   │   ├── hm2_scaffold_breaker.py    ← P9, P12, P25-P27, P44-P53
│   │   ├── hm2_format_cleaner.py      ← P13-P18, F1-F4b (NEVER skip)
│   │   ├── hm2_connector_tuner.py     ← P29, P33, P40, P43
│   │   └── hm2_triplet_buster.py      ← P10 (zero tolerance)
│   │
│   ├── [QA Gate post-HM-2] (agents/gates/qa_gate_post_hm2.py)
│   │       Coherence check: cosine similarity ≥ 0.85
│   │
│   ├── HM-3 Lexicographer (agents/humanizer/stages/hm3_lexicographer.py)
│   │   │   Wraps: lexical_enricher.transform()
│   │   │   Модель: Sonnet | ~83 chunks × 4 workers
│   │   │
│   │   ├── hm3_vocab_eliminator.py    ← P7, P28, P8, P11, F8
│   │   ├── hm3_hedging_auditor.py     ← P32, P38, P23
│   │   ├── hm3_attribution_fixer.py   ← P5, P39, P42
│   │   └── hm3_result_formatter.py    ← P36, P31
│   │
│   ├── [QA Gate post-HM-3] (agents/gates/qa_gate_post_hm3.py)
│   │       Coherence + Register drift check
│   │
│   ├── HM-4 Voice (agents/humanizer/stages/hm4_voice.py)
│   │   │   Two-pass: Pass A (transform) + Pass B (14-point audit)
│   │   │   Модель: Sonnet | ~83 chunks × 2 passes
│   │   │   AC-gates: AC-4 (passive RU 70%), AC-5 (skip figurative RU), AC-7 (skip F5/F6 RU)
│   │   │
│   │   ├── hm4_soul_injector.py       ← P30, F5, F6, F7, Pass A
│   │   ├── hm4_rhythm_shaper.py       ← P25, P37
│   │   ├── hm4_pass_b_auditor.py      ← 14-пунктовый чеклист (P44-P53 included)
│   │   └── hm4_example_loader.py      ← Few-shot ВШЭ корпус (56 дипломов)
│   │
│   ├── [QA Gate post-HM-4] (agents/gates/qa_gate_post_hm4.py)
│   │       Coherence post-voice (over-imperfection guard)
│   │
│   └── HM-5 Controller (agents/humanizer/stages/hm5_controller.py)
│       │   Wraps: scorer.score() + feedback routing
│       │   Модель: LOCAL (без API)
│       │
│       ├── hm5_score_engine.py        ← 20 метрик, METRIC_THRESHOLDS (7 hard + 10 soft)
│       ├── hm5_detector_probe.py      ← GPTZero, Turnitin (optional, по запросу)
│       ├── hm5_feedback_router.py     ← → HM-2/3/4 или CEO escalation
│       └── hm5_report_builder.py      ← score_report.json + score_report.txt
│
├── [Content QA Gate] (agents/gates/content_qa.py)
│       Проверяет Phase 0 output: announcement_openers=0, triplets=0, Block12=0, viz≥minimum
│
└── Export Manager (agents/export_manager.py)
        .txt + .docx (ГОСТ 7.32-2017 или free) + score_report.json + score_report.txt


═══════════════════════════════════════════════════════════
SHARED SERVICES (agents/services/) — Singleton, используются всеми агентами
═══════════════════════════════════════════════════════════

├── Language Gate Service (language_gate.py)
│       LanguageConfig (23 поля) → AC-1–AC-15 gating
│       get_config(language, register, domain) → LanguageConfig
│       validate_ac_compliance(text, config) → list[ACViolation]
│
├── Domain Gate Service (domain_gate.py)
│       P41 epistemological norms per domain
│       get_domain_norms(domain) → DomainConfig
│
├── Source Finder Service (source_finder_service.py)
│       Wraps: pipeline/source_finder.py
│       find(topic, domain, language, stream_id) → SourceList
│       ГОСТ Р 7.0.100-2018 formatting
│
├── DOCX Formatter Service (docx_formatter_service.py)
│       Wraps: pipeline/formatter.py
│       export_to_docx(text, params, path) → .docx
│       ГОСТ 7.32-2017 (academic) / Free (journalistic)
│
├── Chunk Manager (chunk_manager.py)
│       200-400 слов, ~1 sentence overlap
│       Boundary dedup на выходе
│
├── Pattern Scanner (pattern_scanner.py)
│       P1-P53 единый движок
│       Используется: HM-1, HM-5, Content QA Gate
│
└── API Gateway (api_gateway.py)
        Claude API: rate limiter, retry (exponential backoff), token budget
        Prompt Caching: cache_control=ephemeral на system prompts
        Cost tracking → CostReport dataclass
        Batch API (optional): anthropic.Batch.create() для эконом-тарифа


═══════════════════════════════════════════════════════════
EXISTING PIPELINE (pipeline/) — НЕ ИЗМЕНЯЕМ, оборачиваем
═══════════════════════════════════════════════════════════

├── pipeline/__init__.py          ← orchestrator (call_claude, load_config, chunk_text)
├── pipeline/analyzer.py          ← Stage 1 → HM-1 wraps
├── pipeline/structural_rewriter.py ← Stage 2 → HM-2 wraps
├── pipeline/lexical_enricher.py  ← Stage 3 → HM-3 wraps
├── pipeline/discourse_shaper.py  ← Stage 4 → HM-4 wraps
├── pipeline/scorer.py            ← Stage 5 → HM-5 wraps
├── pipeline/generator.py         ← Phase 0B → Content Workers wrap
├── pipeline/source_finder.py     ← Phase 0A → SourceFinder Service wraps
├── pipeline/formatter.py         ← DOCX → Formatter Service wraps
└── pipeline/example_loader.py    ← Few-shot → HM-4 Example Loader wraps


═══════════════════════════════════════════════════════════
COMPONENT COUNT
═══════════════════════════════════════════════════════════

CEO:                          1
Managers:                     2  (Content + Humanizer)
Micro Managers:               7  (VKR, Coursework, Research, Abstract, Text, Essay, Composition)
Content Workers:             36  (9+7+8+6+4+1+1)
HM Workers:                  19  (3+4+4+4+4)
HM Stages:                    5  (HM-1, HM-2, HM-3, HM-4, HM-5)
Gates:                        5  (Handoff, ContentQA, QA×3)
Shared Services:              7  (LangGate, DomainGate, SourceFinder, DocxFormatter, ChunkMgr, PatternScanner, APIGateway)
Export:                       1
───────────────────────────────
TOTAL:                       82 + 1 CLI entry point (agents/__main__.py)
```
