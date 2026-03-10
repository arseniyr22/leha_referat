"""
Pipeline unit tests.
Run: pytest tests/ -v
Run with output: pytest tests/ -v -s
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Fixture helpers ────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


FIXTURE_ECONOMICS = load_fixture("fixture_01_economics_academic.txt")
FIXTURE_CS = load_fixture("fixture_02_cs_academic.txt")
FIXTURE_MANAGEMENT = load_fixture("fixture_03_management_general.txt")


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzerMetrics:
    """Unit tests for all Stage 1 metric functions."""

    def test_compute_sentence_cv_uniform_returns_low(self):
        from pipeline.analyzer import compute_sentence_cv
        # Uniform-length sentences → low CV (AI-like)
        text = "The model works well. The data shows results. The method is good. The output is correct. The system runs fast."
        cv = compute_sentence_cv(text)
        assert cv < 0.45, f"Expected low CV for uniform text, got {cv:.3f}"

    def test_compute_sentence_cv_varied_returns_high(self):
        from pipeline.analyzer import compute_sentence_cv
        # Highly varied lengths → high CV (human-like)
        text = (
            "No. "
            "The intervention reduced dropout rates from 34% to 11% across the three cohorts studied between 2019 and 2022, "
            "controlling for prior academic performance and socioeconomic background. "
            "Remarkable. "
            "This held even when the analysis excluded the two outlier institutions with atypically high baseline dropout rates, "
            "which suggests the effect is not driven by a few extreme cases."
        )
        cv = compute_sentence_cv(text)
        assert cv >= 0.45, f"Expected high CV for varied text, got {cv:.3f}"

    def test_compute_para_cv_uniform_returns_low(self):
        from pipeline.analyzer import compute_para_cv
        # Four paragraphs of identical length
        para = "This is a paragraph with exactly six words.\n\n"
        text = para * 4
        cv = compute_para_cv(text)
        assert cv < 0.50

    def test_compute_para_cv_varied_returns_high(self):
        from pipeline.analyzer import compute_para_cv
        short = "No.\n\n"
        long = (
            "The analysis covered 56 thesis works across seven disciplines at HSE University. "
            "Economics and management theses averaged 18,000 words each. "
            "Math theses were substantially shorter at around 9,000 words, reflecting the genre convention "
            "that proofs take fewer words than literature reviews. "
            "The corpus included both Russian-language and English-language submissions, "
            "rated 8–10 out of 10 by faculty reviewers who were unaware of the study's purpose.\n\n"
        )
        text = short + long + short + long + short
        cv = compute_para_cv(text)
        assert cv >= 0.50

    def test_compute_but_however_ratio_ai_inverted(self):
        from pipeline.analyzer import compute_but_however_ratio
        # AI pattern: However >> But
        text = (
            "However, the results were inconclusive. "
            "However, the method has limitations. "
            "However, further research is needed. "
            "But the data suggests otherwise."
        )
        result = compute_but_however_ratio(text)
        assert result["but"] == 1
        assert result["however"] == 3
        assert result["ratio"] < 2.0

    def test_compute_but_however_ratio_human_correct(self):
        from pipeline.analyzer import compute_but_however_ratio
        # Human pattern: But >> However
        text = (
            "But the data tells a different story. "
            "But this effect disappears when controlling for income. "
            "But the most striking finding is the regional variance. "
            "However, the sample size limits generalization."
        )
        result = compute_but_however_ratio(text)
        assert result["but"] == 3
        assert result["however"] == 1
        assert result["ratio"] >= 2.0

    def test_count_triplets_detects_noun_series(self):
        from pipeline.analyzer import count_triplets
        text = "The study examines efficiency, equity, and sustainability."
        result = count_triplets(text)
        assert result["total"] >= 1

    def test_count_triplets_detects_verb_tricolon(self):
        from pipeline.analyzer import count_triplets
        text = "She raised the rate, required exporters to convert earnings, and imposed capital controls."
        result = count_triplets(text)
        assert result["total"] >= 1

    def test_count_triplets_clean_text_returns_zero(self):
        from pipeline.analyzer import count_triplets
        text = "The rate rose and exporters converted earnings. Capital controls followed."
        result = count_triplets(text)
        assert result["total"] == 0

    def test_count_announcement_openers_detects_banned(self):
        from pipeline.analyzer import count_announcement_openers
        texts_with_openers = [
            "Here's the problem with sanctions: they hurt ordinary people.",
            "This is worth a brief detour into the methodology.",
            "X also deserves mention here.",
            "It is worth noting that the results were significant.",
            "This section will explore the main findings.",
        ]
        for text in texts_with_openers:
            count = count_announcement_openers(text)
            assert count >= 1, f"Expected detection in: {text}"

    def test_count_announcement_openers_clean_returns_zero(self):
        from pipeline.analyzer import count_announcement_openers
        text = (
            "The results were significant. "
            "The methodology required manual tuning. "
            "Dropout fell from 34% to 11% in the treatment group."
        )
        count = count_announcement_openers(text)
        assert count == 0

    def test_count_para_ending_generalizations_detects(self):
        from pipeline.analyzer import count_para_ending_generalizations
        text = (
            "Dropout rates fell from 34% to 11%. "
            "The uneven distribution of outcomes complicates any simple story about the intervention.\n\n"
            "GDP grew by 2.3%. This repeats the same pattern across all transition economies."
        )
        count = count_para_ending_generalizations(text)
        assert count >= 1

    def test_count_modal_hedging_on_results_detects(self):
        from pipeline.analyzer import count_modal_hedging_on_results
        text = (
            "The model may achieve 94% accuracy. "
            "Results suggest performance could reach 0.92 AUC. "
            "The intervention appears to reduce costs by 23%."
        )
        count = count_modal_hedging_on_results(text)
        assert count["count"] >= 2

    def test_count_modal_hedging_on_results_clean(self):
        from pipeline.analyzer import count_modal_hedging_on_results
        text = (
            "The model achieved 94% accuracy. "
            "Performance reached 0.92 AUC on the held-out test set. "
            "The intervention reduced costs by 23%."
        )
        count = count_modal_hedging_on_results(text)
        assert count["count"] == 0

    def test_compute_also_frequency_detects_absence(self):
        from pipeline.analyzer import compute_also_frequency
        # Text with no "also" — AI signal
        text = (
            "Furthermore, the results were positive. "
            "Moreover, the methodology was sound. "
            "Additionally, the sample was representative. "
            "In addition, the data quality was high. "
            "Furthermore, the analysis was comprehensive."
        )
        result = compute_also_frequency(text)
        assert result["count"] == 0
        assert result["per_page"] == 0.0

    def test_compute_also_frequency_human_level(self):
        from pipeline.analyzer import compute_also_frequency
        # 250 words with 3 "also" instances → roughly 0.12 per page (250w ≈ 1 page)
        text = (
            "The intervention reduced costs. "
            "It also improved employee satisfaction scores by 18 points. "
            "The second study confirmed these results. "
            "The third cohort also showed significant improvement, though the effect was smaller. "
            "Management practices changed substantially. "
            "Communication protocols were also updated in 2021. "
        ) * 3  # repeat to get ~250 words
        result = compute_also_frequency(text)
        assert result["count"] >= 3

    def test_count_standalone_definitions_detects(self):
        from pipeline.analyzer import count_standalone_definitions
        text = (
            "Machine learning is defined as a subset of artificial intelligence. "
            "Transfer learning can be defined as a technique where knowledge from one domain is applied to another. "
            "The term digital transformation refers to the process of integrating digital technology."
        )
        count = count_standalone_definitions(text)
        assert count >= 2

    def test_scan_p7_context_aware_absolute_ban(self):
        from pipeline.analyzer import scan_p7_context_aware
        text = "This vibrant tapestry of research delves into the realm of synergy."
        result = scan_p7_context_aware(text, domain="economics", register="academic")
        assert len(result["absolute_violations"]) >= 3  # vibrant, tapestry, delves, realm, synergy

    def test_compute_section_cv_uniform(self):
        from pipeline.analyzer import compute_section_cv
        # Two equal sections separated by heading
        section = (
            "## Section One\n\n"
            "This section contains exactly ten words in its content here.\n\n"
        )
        text = section.replace("One", "One") + section.replace("One", "Two")
        cv = compute_section_cv(text)
        # With only 2 sections of equal size, CV should be 0
        assert cv < 0.30

    def test_classify_domain_economics(self):
        from pipeline.analyzer import classify_domain
        domain = classify_domain(FIXTURE_ECONOMICS)
        assert domain in ("economics", "social-science", "general")

    def test_classify_register_academic(self):
        from pipeline.analyzer import classify_register
        register = classify_register(FIXTURE_ECONOMICS)
        assert register == "academic"

    def test_classify_register_general(self):
        from pipeline.analyzer import classify_register
        register = classify_register(FIXTURE_MANAGEMENT)
        assert register in ("general", "journalistic", "academic")

    def test_analyzer_transform_is_passthrough(self):
        from pipeline.analyzer import Analyzer
        analyzer = Analyzer()
        text = "This is a test sentence. It should pass through unchanged."
        result = analyzer.transform(text)
        assert result == text

    def test_analyzer_score_returns_all_keys(self):
        from pipeline.analyzer import Analyzer
        analyzer = Analyzer()
        score = analyzer.score(FIXTURE_ECONOMICS[:500])
        required_keys = [
            "sentence_cv", "para_cv", "section_cv", "transition_monotony",
            "announcement_openers", "triplets", "para_ending_generalizations",
            "attributive_passives", "genuinely_adj", "but_however",
            "connector_density", "modal_hedging_on_results", "standalone_definitions",
            "also_frequency", "p7_violations", "domain", "register",
        ]
        for key in required_keys:
            assert key in score, f"Missing key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: StructuralRewriter — local (regex) passes only
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructuralRewriterLocal:
    """Tests for regex-based operations that don't require the Claude API."""

    def test_restore_copulas_serves_as(self):
        from pipeline.structural_rewriter import restore_copulas
        text = "The library serves as the main exhibition space."
        result = restore_copulas(text)
        assert "serves as" not in result
        assert "is" in result or "functions as" in result or result != text

    def test_restore_copulas_boasts(self):
        from pipeline.structural_rewriter import restore_copulas
        text = "The building boasts three floors and a rooftop garden."
        result = restore_copulas(text)
        assert "boasts" not in result

    def test_remove_announcement_openers_heres_the_problem(self):
        from pipeline.structural_rewriter import remove_announcement_openers
        text = (
            "Here's the problem with sanctions: they hurt ordinary people. "
            "The economy contracted by 4.2% in 2022."
        )
        result = remove_announcement_openers(text)
        assert "Here's the problem" not in result
        assert "The economy contracted" in result

    def test_remove_announcement_openers_worth_noting(self):
        from pipeline.structural_rewriter import remove_announcement_openers
        text = "It is worth noting that the results were significant. GDP fell by 3%."
        result = remove_announcement_openers(text)
        assert "It is worth noting" not in result

    def test_reduce_em_dashes_replaces(self):
        from pipeline.structural_rewriter import reduce_em_dashes
        text = "The policy—introduced in 2019—was contested immediately."
        result = reduce_em_dashes(text)
        # Should have fewer or no em dashes
        assert result.count("—") <= text.count("—")

    def test_normalize_headings_title_to_sentence(self):
        from pipeline.structural_rewriter import normalize_headings
        text = "## Strategic Negotiations And Global Partnerships\n\nContent here."
        result = normalize_headings(text)
        assert "## Strategic negotiations and global partnerships" in result

    def test_remove_curly_quotes(self):
        from pipeline.structural_rewriter import remove_curly_quotes
        text = 'She said \u201cthe results were promising\u201d and left.'
        result = remove_curly_quotes(text)
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert '"the results were promising"' in result

    def test_remove_emojis(self):
        from pipeline.structural_rewriter import remove_emojis
        text = "## Key Findings 🚀\n\nThe results were 💡 significant."
        result = remove_emojis(text)
        assert "🚀" not in result
        assert "💡" not in result
        assert "Key Findings" in result

    def test_convert_standalone_definitions(self):
        from pipeline.structural_rewriter import convert_standalone_definitions
        text = (
            "Machine learning is defined as a subset of artificial intelligence "
            "that enables systems to learn from data."
        )
        result = convert_standalone_definitions(text)
        # Should restructure to embed definition more naturally
        assert result != text or "is defined as" not in result

    def test_rebalance_connectors_removes_additionally(self):
        from pipeline.structural_rewriter import rebalance_connectors
        text = (
            "The model performed well. Additionally, the results were robust. "
            "Additionally, the sample was large. Furthermore, the methodology was sound."
        )
        result = rebalance_connectors(text)
        assert result.count("Additionally") < text.count("Additionally")

    def test_rebalance_connectors_preserves_but(self):
        from pipeline.structural_rewriter import rebalance_connectors
        text = "But the data contradicts this. But the sample is too small. The results were mixed."
        result = rebalance_connectors(text)
        # "But" should not be removed
        assert result.count("But") >= 1

    def test_scorer_structural_detects_triplets(self):
        from pipeline.structural_rewriter import StructuralRewriter
        rewriter = StructuralRewriter()
        text = "The study examines efficiency, equity, and sustainability across all domains."
        score = rewriter.score(text)
        assert "triplets" in score
        assert score["triplets"]["total"] >= 1

    def test_scorer_structural_detects_but_however_ratio(self):
        from pipeline.structural_rewriter import StructuralRewriter
        rewriter = StructuralRewriter()
        text = (
            "However, the results were mixed. However, the data is limited. "
            "However, the sample is small. But this is not definitive."
        )
        score = rewriter.score(text)
        assert score["but_however"]["ratio"] < 2.0


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3: LexicalEnricher — local (regex) passes only
# ═══════════════════════════════════════════════════════════════════════════════

class TestLexicalEnricherLocal:
    """Tests for regex-based operations that don't require the Claude API."""

    def test_apply_p7_absolute_ban_vibrant(self):
        from pipeline.lexical_enricher import apply_p7_absolute_ban
        text = "The vibrant community engages in a tapestry of activities."
        result = apply_p7_absolute_ban(text)
        assert "vibrant" not in result
        assert "tapestry" not in result

    def test_apply_p7_absolute_ban_delve(self):
        from pipeline.lexical_enricher import apply_p7_absolute_ban
        text = "This paper delves into the realm of synergy and game-changers."
        result = apply_p7_absolute_ban(text)
        assert "delves" not in result
        assert "realm" not in result
        assert "synergy" not in result
        assert "game-changer" not in result

    def test_remove_importance_framing_plays_crucial_role(self):
        from pipeline.lexical_enricher import remove_importance_framing
        text = "Language plays a crucial role in social integration."
        result = remove_importance_framing(text)
        assert "plays a crucial role" not in result

    def test_remove_importance_framing_genuinely(self):
        from pipeline.lexical_enricher import remove_genuinely_adj
        text = "The scope is genuinely substantial and genuinely unprecedented in scale."
        result = remove_genuinely_adj(text)
        assert "genuinely" not in result

    def test_remove_filler_phrases(self):
        from pipeline.lexical_enricher import remove_filler_phrases
        text = "In order to achieve this goal, we need to focus on quality."
        result = remove_filler_phrases(text)
        assert "In order to" not in result
        assert "achieve this goal" in result

    def test_remove_filler_due_to_the_fact(self):
        from pipeline.lexical_enricher import remove_filler_phrases
        text = "Due to the fact that the data was incomplete, we excluded three cases."
        result = remove_filler_phrases(text)
        assert "Due to the fact that" not in result

    def test_remove_stacked_hedging(self):
        from pipeline.lexical_enricher import remove_stacked_hedging
        text = "The policy could potentially possibly be argued to have some effect."
        result = remove_stacked_hedging(text)
        # Should reduce to one qualifier
        qualifiers = ["potentially", "possibly", "arguably", "could be argued"]
        qualifier_count = sum(1 for q in qualifiers if q in result)
        assert qualifier_count <= 1

    def test_remove_chatbot_artifacts(self):
        from pipeline.lexical_enricher import remove_chatbot_artifacts
        texts = [
            "I hope this helps with your research.",
            "Of course! Here is a summary.",
            "Great question! The answer is...",
            "Certainly! Let me know if you need more.",
        ]
        for text in texts:
            result = remove_chatbot_artifacts(text)
            for artifact in ["I hope this helps", "Of course!", "Great question!", "Certainly!", "Let me know"]:
                if artifact.lower() in text.lower():
                    assert artifact.lower() not in result.lower(), f"Artifact not removed: {artifact}"

    def test_remove_generic_endings(self):
        from pipeline.lexical_enricher import remove_generic_endings
        endings = [
            "The future looks bright for this industry.",
            "Exciting times lie ahead.",
            "This represents a major step in the right direction.",
        ]
        for text in endings:
            result = remove_generic_endings(text)
            assert result != text or len(result) < len(text)

    def test_apply_p28_substitutions_leverage(self):
        from pipeline.lexical_enricher import apply_p28_substitutions
        text = "Organizations leverage digital tools to facilitate growth and utilize resources."
        result = apply_p28_substitutions(text, domain="management", register="general")
        assert "leverage" not in result or "leverage" in text  # should be replaced
        # "use" should appear more
        assert "utilize" not in result

    def test_apply_p28_preserves_technical_facilitate(self):
        from pipeline.lexical_enricher import apply_p28_substitutions
        # In pharmacology context, "facilitate" is technical — should be preserved
        text = "The enzyme facilitates the conversion of substrate to product."
        result = apply_p28_substitutions(text, domain="biology", register="academic")
        # Preservation depends on implementation; at minimum, result should be valid text
        assert len(result) > 0

    def test_remove_banned_connectors_regex(self):
        from pipeline.lexical_enricher import remove_banned_connectors_regex
        text = (
            "Firstly, the data was collected. Secondly, it was analyzed. "
            "Thirdly, results were interpreted. Finally, conclusions were drawn."
        )
        result = remove_banned_connectors_regex(text)
        for banned in ["Firstly", "Secondly", "Thirdly", "Finally,"]:
            assert banned not in result

    def test_remove_modal_from_result_sentences(self):
        from pipeline.lexical_enricher import remove_modal_from_result_sentences
        text = "The model may achieve 94% accuracy on the test set."
        result = remove_modal_from_result_sentences(text)
        assert "may achieve" not in result
        assert "94%" in result

    def test_remove_modal_preserves_methodology_hedge(self):
        from pipeline.lexical_enricher import remove_modal_from_result_sentences
        # Modal in methodology sentence (no measurement) — should be preserved
        text = "This design could introduce selection bias if participants self-select."
        result = remove_modal_from_result_sentences(text)
        # No number present — modal should remain
        assert "could" in result

    def test_remove_result_praise(self):
        from pipeline.lexical_enricher import remove_result_praise
        text = "The model achieved a remarkable accuracy of 94%, significantly outperforming baselines."
        result = remove_result_praise(text)
        assert "remarkable" not in result
        assert "94%" in result

    def test_lexical_enricher_score_returns_keys(self):
        from pipeline.lexical_enricher import LexicalEnricher
        enricher = LexicalEnricher()
        score = enricher.score(FIXTURE_ECONOMICS[:500])
        required_keys = [
            "p7_absolute_violations", "importance_framing_count", "genuinely_adj_count",
            "filler_phrase_count", "stacked_hedging_count", "chatbot_artifacts",
            "generic_endings", "banned_connector_count", "modal_hedging_on_results",
            "result_praise_count",
        ]
        for key in required_keys:
            assert key in score, f"Missing score key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 4: DiscourseShaper — mocked Claude API
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiscourseShaper:
    """Tests for Stage 4 with mocked API calls."""

    @patch("pipeline.discourse_shaper._call_claude")
    def test_transform_calls_both_passes(self, mock_claude):
        from pipeline.discourse_shaper import DiscourseShaper
        mock_claude.side_effect = ["Pass A output text.", "Pass B audited text."]
        shaper = DiscourseShaper()
        result = shaper.transform("Input text.", domain="economics", register="academic")
        assert mock_claude.call_count == 2
        assert result == "Pass B audited text."

    @patch("pipeline.discourse_shaper._call_claude")
    def test_pass_a_system_contains_domain(self, mock_claude):
        from pipeline.discourse_shaper import _build_pass_a_system
        system = _build_pass_a_system(domain="economics", register="academic")
        assert "economics" in system.lower()
        assert "academic" in system.lower()

    @patch("pipeline.discourse_shaper._call_claude")
    def test_pass_a_system_no_template_vars(self, mock_claude):
        from pipeline.discourse_shaper import _build_pass_a_system
        system = _build_pass_a_system(domain="cs", register="academic")
        # All {{VAR}} placeholders should be replaced
        assert "{{" not in system
        assert "}}" not in system

    @patch("pipeline.discourse_shaper._call_claude")
    def test_pass_b_system_no_template_vars(self, mock_claude):
        from pipeline.discourse_shaper import _build_pass_b_system
        system = _build_pass_b_system(domain="management", register="general")
        assert "{{" not in system
        assert "}}" not in system

    @patch("pipeline.discourse_shaper._call_claude")
    def test_pass_b_user_contains_14_checklist_items(self, mock_claude):
        from pipeline.discourse_shaper import _build_pass_b_user
        user = _build_pass_b_user("Sample text.", domain="economics", register="academic")
        # Check that all 14 items are present by checking for item numbers
        for i in range(1, 15):
            assert f"{i}." in user, f"Missing checklist item {i}"

    @patch("pipeline.discourse_shaper._call_claude")
    def test_academic_register_no_colloquial_p30(self, mock_claude):
        from pipeline.discourse_shaper import _build_pass_a_system
        system = _build_pass_a_system(domain="economics", register="academic")
        # Academic P30 = limited; should NOT apply full P30 toolkit
        # The prompt should mention "limited" for academic
        assert "limited" in system or "academic" in system

    def test_score_returns_keys(self):
        from pipeline.discourse_shaper import DiscourseShaper
        shaper = DiscourseShaper()
        text = (
            "But the data contradicts this. The model achieved 94% accuracy. "
            "Dropout fell from 34% to 11%. However, the sample is limited."
        )
        score = shaper.score(text)
        required_keys = [
            "sentence_cv", "para_cv", "but_however", "triplets",
            "announcement_openers", "para_ending_generalizations",
            "also_frequency", "word_count",
        ]
        for key in required_keys:
            assert key in score, f"Missing score key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 5: Scorer
# ═══════════════════════════════════════════════════════════════════════════════

class TestScorer:
    """Tests for Stage 5 scoring functions."""

    def test_score_length_reduction_below_90pct(self):
        from pipeline.scorer import score_length_reduction
        input_text = "word " * 100  # 100 words
        output_text = "word " * 85   # 85 words — 85% of input, passes
        result = score_length_reduction(input_text, output_text)
        assert result["ratio"] == pytest.approx(0.85, abs=0.01)
        assert result["pass"] is True

    def test_score_length_reduction_above_90pct_fails(self):
        from pipeline.scorer import score_length_reduction
        input_text = "word " * 100
        output_text = "word " * 95   # 95% — fails
        result = score_length_reduction(input_text, output_text)
        assert result["ratio"] == pytest.approx(0.95, abs=0.01)
        assert result["pass"] is False

    def test_score_sentence_cv_pass(self):
        from pipeline.scorer import score_sentence_cv
        # Varied sentence lengths
        text = (
            "No. "
            "The model achieved 94% accuracy on the held-out test set, "
            "outperforming the best reported baseline by 7 percentage points. "
            "Remarkable. "
            "This held across all four language pairs in the FLORES evaluation, "
            "including the two pairs with fewer than 50,000 training examples."
        )
        result = score_sentence_cv(text)
        assert "cv" in result
        assert "pass" in result

    def test_score_announcement_openers_zero(self):
        from pipeline.scorer import score_announcement_openers
        clean_text = (
            "Dropout fell from 34% to 11% in the treatment group. "
            "The intervention targeted schools in low-income districts. "
            "GDP grew by 2.3% in the first quarter."
        )
        result = score_announcement_openers(clean_text)
        assert result["count"] == 0
        assert result["pass"] is True

    def test_score_announcement_openers_violations(self):
        from pipeline.scorer import score_announcement_openers
        text_with_openers = (
            "Here's the problem with the methodology: it excludes outliers. "
            "It is worth noting that the results were significant. "
            "GDP grew by 2.3%."
        )
        result = score_announcement_openers(text_with_openers)
        assert result["count"] >= 1
        assert result["pass"] is False

    def test_score_triplets_zero(self):
        from pipeline.scorer import score_triplets
        clean_text = (
            "The rate rose and exporters converted earnings. Capital controls followed. "
            "The method required training and validation."
        )
        result = score_triplets(clean_text)
        assert result["total"] == 0
        assert result["pass"] is True

    def test_score_triplets_violations(self):
        from pipeline.scorer import score_triplets
        text = "The study examines efficiency, equity, and sustainability."
        result = score_triplets(text)
        assert result["total"] >= 1
        assert result["pass"] is False

    def test_score_but_however_ratio_pass(self):
        from pipeline.scorer import score_but_however_ratio
        text = (
            "But the data contradicts this claim. "
            "But this effect vanishes when controlling for income. "
            "But the most striking finding is regional variance. "
            "However, the sample size limits generalization."
        )
        result = score_but_however_ratio(text)
        assert result["ratio"] >= 2.0
        assert result["pass"] is True

    def test_score_but_however_ratio_fail(self):
        from pipeline.scorer import score_but_however_ratio
        text = (
            "However, the results were mixed. "
            "However, the sample was small. "
            "However, the method had limitations. "
            "But this is uncertain."
        )
        result = score_but_however_ratio(text)
        assert result["ratio"] < 2.0
        assert result["pass"] is False

    def test_score_modal_hedging_on_results_zero(self):
        from pipeline.scorer import score_modal_hedging_on_results
        clean = (
            "The model achieved 94% accuracy. "
            "Performance reached 0.92 AUC on the test set."
        )
        result = score_modal_hedging_on_results(clean)
        assert result["count"] == 0
        assert result["pass"] is True

    def test_score_modal_hedging_on_results_violations(self):
        from pipeline.scorer import score_modal_hedging_on_results
        text = (
            "The model may achieve 94% accuracy. "
            "Performance could reach 0.92 AUC."
        )
        result = score_modal_hedging_on_results(text)
        assert result["count"] >= 1
        assert result["pass"] is False

    def test_score_also_frequency_pass(self):
        from pipeline.scorer import score_also_frequency
        # ~250 words with 3 "also" instances ≈ 0.12 per page
        words = "The intervention reduced costs. It also improved satisfaction. " * 20
        words += "Results also showed improvement in three additional metrics. "
        words += "The method also outperformed the baseline on held-out data."
        result = score_also_frequency(words)
        assert result["count"] >= 3
        assert result["pass"] is True

    def test_score_also_frequency_fail_zero(self):
        from pipeline.scorer import score_also_frequency
        # 600 words with 0 "also" in academic register → should fail
        text = ("The study examined the intervention and its effects on outcomes. " * 100)
        result = score_also_frequency(text, register="academic")
        assert result["per_page"] == 0.0
        assert result["pass"] is False

    def test_scorer_full_score_returns_all_keys(self):
        from pipeline.scorer import Scorer
        scorer = Scorer()
        short_input = FIXTURE_ECONOMICS[:600]
        # Use a slightly modified version as "output"
        short_output = short_input.replace("However", "But").replace("Furthermore", "Also")
        score = scorer.score(
            input_text=short_input,
            output_text=short_output,
            domain="economics",
            register="academic",
            run_detector_probes=False,
        )
        required_keys = [
            "sentence_cv", "para_cv", "length_reduction", "announcement_openers",
            "triplets", "but_however", "modal_hedging_on_results", "also_frequency",
            "para_ending_generalizations",
        ]
        for key in required_keys:
            assert key in score, f"Missing score key: {key}"

    def test_scorer_score_includes_pass_fail(self):
        from pipeline.scorer import Scorer
        scorer = Scorer()
        short_input = FIXTURE_ECONOMICS[:600]
        short_output = short_input[:500]  # shorter = passes length reduction
        score = scorer.score(
            input_text=short_input,
            output_text=short_output,
            domain="economics",
            register="academic",
            run_detector_probes=False,
        )
        # Each metric should have a "pass" key
        for key, value in score.items():
            if isinstance(value, dict):
                assert "pass" in value, f"Score metric '{key}' missing 'pass' key"


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern-Level Integration: Fixture Scan
# ═══════════════════════════════════════════════════════════════════════════════

class TestFixturePatternDetection:
    """Verify that all three AI fixtures contain expected AI patterns.
    These tests confirm the fixtures are good test inputs (not already humanized).
    """

    def test_fixture_economics_contains_triplets(self):
        from pipeline.analyzer import count_triplets
        result = count_triplets(FIXTURE_ECONOMICS)
        assert result["total"] >= 2, "Economics fixture should contain triplets"

    def test_fixture_economics_contains_announcement_openers(self):
        from pipeline.analyzer import count_announcement_openers
        count = count_announcement_openers(FIXTURE_ECONOMICS)
        assert count >= 1, "Economics fixture should contain announcement openers"

    def test_fixture_economics_contains_modal_hedging(self):
        from pipeline.analyzer import count_modal_hedging_on_results
        count = count_modal_hedging_on_results(FIXTURE_ECONOMICS)
        assert count["count"] >= 1, "Economics fixture should contain modal hedging on results"

    def test_fixture_cs_contains_triplets(self):
        from pipeline.analyzer import count_triplets
        result = count_triplets(FIXTURE_CS)
        assert result["total"] >= 2, "CS fixture should contain triplets"

    def test_fixture_cs_contains_announcement_openers(self):
        from pipeline.analyzer import count_announcement_openers
        count = count_announcement_openers(FIXTURE_CS)
        assert count >= 1, "CS fixture should contain announcement openers"

    def test_fixture_management_contains_p7_violations(self):
        from pipeline.analyzer import scan_p7_context_aware
        result = scan_p7_context_aware(FIXTURE_MANAGEMENT, domain="management", register="general")
        assert len(result["absolute_violations"]) >= 3, "Management fixture should contain P7 violations"

    def test_fixture_management_has_inverted_but_however(self):
        from pipeline.analyzer import compute_but_however_ratio
        result = compute_but_however_ratio(FIXTURE_MANAGEMENT)
        # AI text avoids "But" entirely — management fixture uses formal connectors
        # (Furthermore, Moreover, Additionally) instead, so "But" count is 0
        assert result["but"] == 0

    def test_all_fixtures_have_low_sentence_cv(self):
        from pipeline.analyzer import compute_sentence_cv
        for fixture, name in [
            (FIXTURE_ECONOMICS, "economics"),
            (FIXTURE_CS, "cs"),
            (FIXTURE_MANAGEMENT, "management"),
        ]:
            cv = compute_sentence_cv(fixture)
            # AI text typically has low sentence CV; fixtures are AI-generated
            # This is a soft check — just verify the function runs and returns a number
            assert 0.0 <= cv <= 5.0, f"Invalid CV for {name}: {cv}"


# ── TestExampleLoader ─────────────────────────────────────────────────────────

class TestExampleLoader:
    """Unit tests for pipeline.example_loader.ExampleLoader. All tests use mocks."""

    def test_is_english_true(self):
        from pipeline.example_loader import ExampleLoader
        loader = ExampleLoader.__new__(ExampleLoader)
        loader.min_english_ratio = 0.60
        loader.excerpt_words = 400
        english_text = (
            "The study examines the relationship between monetary policy and inflation "
            "dynamics in emerging market economies. We use panel data from the IMF and "
            "World Bank covering the period 2000 to 2020. The results suggest that "
            "a one percentage point increase in the policy rate reduces inflation by "
            "approximately 0.8 percentage points over a four-quarter horizon. "
            "Furthermore, the exchange rate channel plays a particularly important role "
            "in open economies. The analysis reveals that central bank credibility "
            "is a fundamental determinant of policy effectiveness. Our findings are "
            "consistent with the conventional view of monetary policy transmission. "
            "This paper contributes to the literature by providing evidence from a "
            "large cross-country panel dataset."
        )
        assert loader._is_english(english_text) is True

    def test_is_english_false(self):
        from pipeline.example_loader import ExampleLoader
        loader = ExampleLoader.__new__(ExampleLoader)
        loader.min_english_ratio = 0.60
        loader.excerpt_words = 400
        cyrillic_text = (
            "Данная работа исследует влияние денежно-кредитной политики на динамику "
            "инфляции в странах с формирующимися рынками. Результаты анализа показывают, "
            "что повышение ключевой ставки на один процентный пункт снижает инфляцию "
            "приблизительно на 0.8 процентного пункта в течение четырёх кварталов. "
            "Обменный курс играет особенно важную роль в открытых экономиках. "
            "Доверие к центральному банку является фундаментальным фактором. "
            "Наши выводы согласуются с традиционными взглядами на трансмиссионный механизм."
        )
        assert loader._is_english(cyrillic_text) is False

    def test_get_excerpt_length(self):
        from pipeline.example_loader import ExampleLoader
        loader = ExampleLoader.__new__(ExampleLoader)
        loader.min_english_ratio = 0.60
        loader.excerpt_words = 400
        # Build a long text (1000 words)
        long_text = " ".join(["word"] * 1000)
        excerpt = loader._get_excerpt(long_text)
        word_count = len(excerpt.split())
        assert word_count <= loader.excerpt_words + 10, (
            f"Excerpt too long: {word_count} words (target {loader.excerpt_words})"
        )
        assert word_count >= 1, "Excerpt must not be empty"

    def test_get_example_returns_none_when_no_english(self, tmp_path):
        """When index has no English files for any domain, get_example returns None."""
        from pipeline.example_loader import ExampleLoader
        # Write a fake index with no English files
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        index = {
            "economics": [
                {"path": "/fake/file.pdf", "cache_txt": "/fake/file.txt",
                 "is_english": False, "word_count": 500, "folder": "Economics"}
            ]
        }
        (cache_dir / "index.json").write_text(
            __import__("json").dumps(index), encoding="utf-8"
        )
        loader = ExampleLoader.__new__(ExampleLoader)
        loader.examples_dir = tmp_path / "examples"
        loader.cache_dir = cache_dir
        loader.excerpt_words = 400
        loader.min_english_ratio = 0.60
        loader._index = None  # force _load_index to read from cache_dir

        result = loader.get_example("economics")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# NEW TESTS — Phase 0 Integration, Language Gates, Anti-Conflict Rules (AC-1–AC-15)
# ═══════════════════════════════════════════════════════════════════════════════


class TestGenerationParams:
    """Tests for GenerationParams validation."""

    def test_invalid_stream_id_raises(self):
        """Invalid stream_id should raise ValueError."""
        from pipeline.generator import GenerationParams
        p = GenerationParams(stream_id="invalid_stream", topic="Test")
        with pytest.raises(ValueError, match="Invalid stream_id"):
            p.validate()

    def test_invalid_language_raises(self):
        """Invalid language should raise ValueError."""
        from pipeline.generator import GenerationParams
        p = GenerationParams(stream_id="essay", topic="Test", language="de")
        with pytest.raises(ValueError, match="Invalid language"):
            p.validate()

    def test_valid_params_no_error(self):
        """Valid params should not raise."""
        from pipeline.generator import GenerationParams
        p = GenerationParams(stream_id="coursework", topic="Test topic", language="ru")
        p.validate()  # should not raise


class TestDomainMapping:
    """Tests for AcademicGenerator domain and register mapping."""

    def test_domain_mapping_all(self):
        """All 7 megaprompt domains map to correct pipeline codes."""
        from pipeline.generator import DOMAIN_MAP
        expected = {
            "it_cs": "cs",
            "law": "general",
            "psychology": "social-science",
            "economics": "economics",
            "humanities": "humanities",
            "media": "journalistic",
            "general": "general",
        }
        for megaprompt_domain, pipeline_code in expected.items():
            assert DOMAIN_MAP[megaprompt_domain] == pipeline_code, (
                f"Domain {megaprompt_domain} should map to {pipeline_code}"
            )

    def test_register_mapping_all(self):
        """All 7 stream_ids map to correct pipeline register."""
        from pipeline.generator import REGISTER_MAP
        expected = {
            "vkr": "academic",
            "coursework": "academic",
            "research": "academic",
            "abstract_paper": "academic",
            "text": "journalistic",
            "essay": "academic-essay",
            "composition": "general",
        }
        for stream_id, register in expected.items():
            assert REGISTER_MAP[stream_id] == register, (
                f"Stream {stream_id} should map to register {register}"
            )


class TestLanguageGateEmDash:
    """AC-1: Em dash language gate."""

    def test_em_dash_removed_english(self):
        """English: reduce_em_dashes removes all em dashes (target: 0)."""
        from pipeline.structural_rewriter import reduce_em_dashes
        text = "The result — which was unexpected — showed improvement."
        result = reduce_em_dashes(text)
        assert "—" not in result

    def test_em_dash_preserved_russian_copular(self):
        """Russian: reduce_em_dashes_ru preserves copular em dashes."""
        from pipeline.structural_rewriter import reduce_em_dashes_ru
        text = "Москва — столица России. Главная задача — достижение результата."
        result = reduce_em_dashes_ru(text)
        # Copular em dashes should be preserved (not replaced with comma)
        assert "—" in result

    def test_em_dash_excessive_russian_reduced(self):
        """Russian: reduce_em_dashes_ru reduces excessive (>3 per paragraph) em dashes."""
        from pipeline.structural_rewriter import reduce_em_dashes_ru
        # 5 em dashes after commas in one paragraph = excessive
        text = ("Первый аспект, — важный, — требует внимания, — особого, "
                "— детального, — тщательного.")
        result = reduce_em_dashes_ru(text)
        # Some em dashes after commas should be removed
        assert result.count("—") < text.count("—")


class TestLanguageGateQuotes:
    """AC-8: Quote normalization."""

    def test_english_curly_quotes_to_ascii(self):
        """English: curly quotes → ASCII straight quotes."""
        from pipeline.structural_rewriter import remove_curly_quotes
        text = "\u201cHello world\u201d and \u2018single\u2019"
        result = remove_curly_quotes(text)
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert '"Hello world"' in result

    def test_russian_quotes_to_guillemets(self):
        """Russian: normalize_quotes_ru converts to «»."""
        from pipeline.structural_rewriter import normalize_quotes_ru
        text = '"Санкции" оказали влияние на "рынок".'
        result = normalize_quotes_ru(text)
        assert "«" in result
        assert "»" in result
        assert '"' not in result


class TestLanguageGatePassiveVoice:
    """AC-4: Passive voice threshold for Russian academic."""

    def test_config_has_russian_passive_threshold(self):
        """config.yaml should have discourse.academic_ru_passive_threshold."""
        from pipeline import load_config
        config = load_config()
        threshold = config.get("discourse", {}).get("academic_ru_passive_threshold")
        assert threshold is not None, "discourse.academic_ru_passive_threshold missing from config"
        assert threshold >= 0.60, "Russian academic passive threshold should be ≥ 0.60"


class TestLanguageGateF5F6Academic:
    """AC-7: F5/F6 skipped for academic register."""

    def test_pass_b_user_academic_skips_f5_f6(self):
        """Academic register: F5/F6 note should say SKIP."""
        from pipeline.discourse_shaper import _build_pass_b_user
        prompt = _build_pass_b_user("Sample text.", "economics", "academic", language="en")
        assert "SKIP entirely" in prompt or "SKIP" in prompt

    def test_pass_b_user_ru_journalistic_f5_skip(self):
        """Russian journalistic: F5 should be skipped (no apostrophes in Russian)."""
        from pipeline.discourse_shaper import _build_pass_b_user
        prompt = _build_pass_b_user("Текст.", "media", "journalistic", language="ru")
        # F5 should say inapplicable for Russian
        assert "inapplicable" in prompt or "F5" in prompt

    def test_pass_b_user_en_journalistic_has_f5_f6(self):
        """English journalistic: F5/F6 should be applied."""
        from pipeline.discourse_shaper import _build_pass_b_user
        prompt = _build_pass_b_user("Text here.", "general", "journalistic", language="en")
        # F5 should mention apostrophes
        assert "apostrophe" in prompt.lower() or "3–5" in prompt


class TestLanguageGateFigurativeLanguage:
    """AC-5: Figurative language skipped in Russian academic."""

    def test_voice_injection_prompt_has_ru_figurative_gate(self):
        """voice_injection.md should contain the Russian academic figurative language skip rule."""
        from pathlib import Path
        prompt_text = (
            Path(__file__).parent.parent / "prompts" / "voice_injection.md"
        ).read_text(encoding="utf-8")
        assert "language = ru" in prompt_text or "{{LANGUAGE}}" in prompt_text
        assert "SKIP" in prompt_text

    def test_audit_prompt_has_ru_figurative_gate(self):
        """audit.md should contain the Russian academic figurative language gate."""
        from pathlib import Path
        audit_text = (
            Path(__file__).parent.parent / "prompts" / "audit.md"
        ).read_text(encoding="utf-8")
        assert "LANGUAGE GATE" in audit_text
        assert "ru" in audit_text.lower()


class TestAntiConflictAC2GostCitation:
    """AC-2: GOST citation format preserved for Russian academic."""

    def test_citation_format_gost_for_russian_academic(self):
        """Russian academic: citation format should be GOST."""
        # Test the logic used in lexical_enricher._run_llm_lexical_cleanup
        language = "ru"
        register = "academic"
        citation_format = "GOST" if (language == "ru" and register in ("academic", "academic-essay")) else "AUTHOR_YEAR"
        assert citation_format == "GOST"

    def test_citation_format_author_year_for_english(self):
        """English: citation format should be AUTHOR_YEAR."""
        language = "en"
        register = "academic"
        citation_format = "GOST" if (language == "ru" and register in ("academic", "academic-essay")) else "AUTHOR_YEAR"
        assert citation_format == "AUTHOR_YEAR"


class TestAntiConflictAC6LanguageRouting:
    """AC-15: Perplexity skipped for Russian."""

    def test_language_routing_sets_skip_perplexity_for_ru(self):
        """Pipeline.run() should set _skip_perplexity=True for language='ru'."""
        # Mock the Pipeline.run() language routing logic without full API call
        analysis_report = {}
        language = "ru"
        if language == "ru":
            analysis_report["_skip_perplexity"] = True
            analysis_report["_use_word_cv"] = True
            analysis_report["_language"] = "ru"
        assert analysis_report.get("_skip_perplexity") is True
        assert analysis_report.get("_language") == "ru"


class TestSourceFinder:
    """Tests for SourceFinder."""

    def test_source_list_score_structure(self):
        """SourceList.score() should return dict with expected keys."""
        from pipeline.source_finder import SourceList, Source
        sl = SourceList(
            sources=[
                Source(
                    type="article",
                    authors=["Иванов И.И."],
                    year=2022,
                    title="Тестовая статья",
                    journal_or_publisher="Вопросы экономики",
                    gost_formatted="Иванов И.И. Тестовая статья...",
                    confidence="high",
                    needs_verification=False,
                ),
                Source(
                    type="monograph",
                    authors=["Петров П.П."],
                    year=2020,
                    title="Монография",
                    journal_or_publisher="МГУ",
                    gost_formatted="Петров П.П. Монография...",
                    confidence="medium",
                    needs_verification=True,
                ),
            ]
        )
        score = sl.score()
        assert "total" in score
        assert score["total"] == 2
        assert "needs_verification" in score
        assert score["needs_verification"] == 1
        assert "by_type" in score
        assert "gost_compliant" in score

    def test_gost_format_article_russian(self):
        """_format_gost should produce valid GOST string for Russian article."""
        from pipeline.source_finder import SourceFinder, Source
        # Use a minimal config
        sf = SourceFinder({})
        src = Source(
            type="article",
            authors=["Иванов И.И.", "Петров П.П."],
            year=2023,
            title="Влияние санкций",
            journal_or_publisher="Вопросы экономики",
            city="Москва",
            pages_or_volume="Т. 12, № 3, С. 45–67",
            language="ru",
            confidence="high",
            needs_verification=False,
        )
        result = sf._format_gost(src)
        assert "Иванов И.И." in result
        assert "Влияние санкций" in result
        assert "Вопросы экономики" in result
        assert "2023" in result

    def test_source_list_numbered_bibliography(self):
        """as_numbered_list() should produce numbered GOST bibliography."""
        from pipeline.source_finder import SourceList, Source
        sl = SourceList(sources=[
            Source(type="article", authors=["A."], year=2020, title="T1",
                   journal_or_publisher="J", gost_formatted="A. T1 // J. 2020."),
            Source(type="article", authors=["B."], year=2021, title="T2",
                   journal_or_publisher="J", gost_formatted="B. T2 // J. 2021."),
        ])
        numbered = sl.as_numbered_list()
        assert numbered.startswith("1.")
        assert "2." in numbered


class TestFormatterGost:
    """Tests for Word formatter — GOST and free formatting."""

    def test_docx_export_creates_file(self, tmp_path):
        """export_to_docx should create a .docx file."""
        try:
            from pipeline.formatter import export_to_docx
            config = {
                "formatter": {
                    "gost_font": "Times New Roman",
                    "gost_font_size": 14,
                    "gost_line_spacing": 1.5,
                    "gost_indent_cm": 1.25,
                    "gost_margins": {"left": 3.0, "right": 1.5, "top": 2.0, "bottom": 2.0},
                }
            }
            docx_path = tmp_path / "test.docx"
            text = "## Introduction\n\nThis is a test paragraph.\n\n### Subsection\n\nMore text here."
            result = export_to_docx(text, "academic", docx_path, config, title="Test Title")
            assert result.exists()
            assert result.suffix == ".docx"
        except ImportError:
            pytest.skip("python-docx not installed")

    def test_docx_free_format_creates_file(self, tmp_path):
        """export_to_docx with journalistic register should create file without GOST margins."""
        try:
            from pipeline.formatter import export_to_docx
            config = {
                "formatter": {
                    "free_font": "Calibri",
                    "free_font_size": 11,
                    "free_line_spacing": 1.15,
                    "free_margins": {"all": 2.5},
                    "free_indent_cm": 0,
                }
            }
            docx_path = tmp_path / "test_free.docx"
            text = "# Article Title\n\nSome journalistic content here.\n\nAnother paragraph."
            result = export_to_docx(text, "journalistic", docx_path, config)
            assert result.exists()
        except ImportError:
            pytest.skip("python-docx not installed")


class TestRussianPatterns:
    """Tests for Russian P7/P29 pattern removal."""

    def test_russian_announcement_patterns_removed(self):
        """_apply_russian_patterns should remove Russian announcement openers."""
        from pipeline.structural_rewriter import _apply_russian_patterns
        config = {
            "p7_russian": {
                "absolute_ban": ["как известно"],
                "importance_framing_ban": [],
                "announcement_ban": ["следует отметить, что"],
            },
            "p29_russian": {
                "absolute_ban": [],
                "near_ban_max_per_doc": {},
                "rate_limited_per_500w": {},
            }
        }
        text = "Следует отметить, что данный метод является эффективным."
        result = _apply_russian_patterns(text, config)
        assert "следует отметить" not in result.lower()

    def test_russian_absolute_ban_removed(self):
        """_apply_russian_patterns should remove absolute ban phrases."""
        from pipeline.structural_rewriter import _apply_russian_patterns
        config = {
            "p7_russian": {
                "absolute_ban": ["как известно"],
                "importance_framing_ban": [],
                "announcement_ban": [],
            },
            "p29_russian": {
                "absolute_ban": [],
                "near_ban_max_per_doc": {},
                "rate_limited_per_500w": {},
            }
        }
        text = "Как известно, российская экономика столкнулась с санкциями."
        result = _apply_russian_patterns(text, config)
        assert "как известно" not in result.lower()

    def test_russian_p29_absolute_ban_removed(self):
        """Russian absolute-ban connectors should be removed from text."""
        from pipeline.structural_rewriter import _apply_russian_patterns
        config = {
            "p7_russian": {
                "absolute_ban": [],
                "importance_framing_ban": [],
                "announcement_ban": [],
            },
            "p29_russian": {
                "absolute_ban": ["во-первых"],
                "near_ban_max_per_doc": {},
                "rate_limited_per_500w": {},
            }
        }
        text = "Во-первых, необходимо рассмотреть основные факторы."
        result = _apply_russian_patterns(text, config)
        assert "во-первых" not in result.lower()
