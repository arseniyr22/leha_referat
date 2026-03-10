"""
Stage 2: Structural & Format Rewrite
Targets Humanizer patterns: P8–P10, P12–P16, P25–P27, and new operations 13–16.
Calls Claude API. One transformation per prompt call.
All 16 operations as specified in the plan.
"""
from __future__ import annotations

import re
import time
import yaml
from pathlib import Path
from typing import Optional

import anthropic
from loguru import logger

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_config: dict = {}


def _load_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _call_claude(
    system: str,
    user: str,
    temperature: float = 0.9,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    cfg = _load_config()
    model = cfg["pipeline"]["rewrite_model"]
    delay = cfg["pipeline"]["retry_delay_seconds"]
    client = _get_client()

    for attempt in range(retries):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        except anthropic.RateLimitError:
            if attempt < retries - 1:
                logger.warning(f"Rate limit hit, retrying in {delay * (2 ** attempt)}s")
                time.sleep(delay * (2 ** attempt))
            else:
                raise
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            raise
    return ""


# ── Local (regex-based) operations ───────────────────────────────────────────

def remove_announcement_openers(text: str) -> str:
    """Op 1: Remove sentences that announce topic before stating it (P9)."""
    _PATTERNS = [
        r"[^.!?]*\bhere'?s the (problem|issue|thing) with[^.!?]*[.!?]",
        r"[^.!?]*\bis worth a brief detour[^.!?]*[.!?]",
        r"[^.!?]*\bthere'?s also a \w+ worth flagging[^.!?]*[.!?]",
        r"[^.!?]*\bone thing you rarely see[^.!?]*[.!?]",
        r"[^.!?]*\balso deserves mention[^.!?]*[.!?]",
        r"[^.!?]*\bi mention this mostly because[^.!?]*[.!?]",
        r"[^.!?]*\bis instructive (about|for)[^.!?]*[.!?]",
        r"[^.!?]*\brepeats the same (story|pattern) across[^.!?]*[.!?]",
        r"[^.!?]*\bthis (section|chapter|part) will (explore|examine|discuss|cover)[^.!?]*[.!?]",
        r"[^.!?]*\bin what follows[^.!?]*[.!?]",
        r"[^.!?]*\bwe will now examine[^.!?]*[.!?]",
        r"[^.!?]*\bdeserves mention[^.!?]*[.!?]",
        r"[^.!?]*\bit is worth noting that[^.!?]*[.!?]",
    ]
    for pattern in _PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return re.sub(r"  +", " ", text).strip()


def restore_copulas(text: str) -> str:
    """Op 2: Replace copula avoidance constructs with is/are/has (P8)."""
    replacements = [
        (r"\bserves as (the|a|an) ", r"is the "),
        (r"\bstands as (the|a|an) ", r"is the "),
        (r"\bmarks (the|a|an) ", r"is the "),
        (r"\brepresents (the|a|an) ", r"is the "),
        (r"\bboasts (the|a|an) ", r"has the "),
        (r"\bfeatures (the|a|an) ", r"has a "),
        (r"\boffers (the|a|an) ", r"has a "),
        (r"\bboasts\b", r"has"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def remove_false_ranges(text: str) -> str:
    """Op 5: Remove 'from X to Y' where X and Y are not actually on a scalar spectrum (P12)."""
    # Heuristic: keep numeric ranges, flag abstract ones.
    # This is an approximation; LLM in prompt handles nuanced cases.
    # Remove obvious non-scalar "from X to Y" where both X and Y are abstract nouns.
    return text  # primary handling delegated to LLM prompt


def reduce_em_dashes(text: str) -> str:
    """Op 6 (English): Replace ALL em dashes with commas or periods (P13).
    ONLY call for language='en'. Target: 0 em dashes.
    """
    text = re.sub(r"\s*—\s*", ", ", text)
    return text


def reduce_em_dashes_ru(text: str) -> str:
    """Op 6 (Russian): Conservative em dash reduction.
    Russian grammar requires em dashes in copular sentences, definitions, appositives.
    Only removes AI-overuse: > 3 em dashes per paragraph on non-grammatical positions.
    Preserves: 'X — Y' where X is a noun and Y is a predicate (copular sentence).
    """
    paragraphs = text.split("\n\n")
    result = []
    for para in paragraphs:
        em_count = para.count("—")
        if em_count > 3:
            # Remove only non-initial em dashes that appear within parenthetical contexts
            # (i.e., NOT at the start of a clause defining or equating two terms)
            # Conservative heuristic: replace em dashes that immediately follow a comma
            para = re.sub(r",\s*—\s*", ", ", para)
        result.append(para)
    return "\n\n".join(result)


def normalize_quotes_ru(text: str) -> str:
    """Op (Russian): Normalize quotation marks to Russian guillemets «»."""
    # Replace ASCII and curly quotes with guillemets
    # "word" → «word»
    text = re.sub(r'"([^"]+)"', r'«\1»', text)
    text = re.sub(r'\u201c([^\u201d]+)\u201d', r'«\1»', text)
    text = re.sub(r'\u2018([^\u2019]+)\u2019', r'«\1»', text)
    return text


def _apply_russian_patterns(text: str, config: dict) -> str:
    """Apply Russian-specific P7 and P29 pattern removal from config.
    Analogous to apply_p7_absolute_ban for English.
    """
    p7_ru = config.get("p7_russian", {})
    p29_ru = config.get("p29_russian", {})

    # P7 Russian: absolute ban
    for phrase in p7_ru.get("absolute_ban", []):
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)

    # P7 Russian: importance-framing ban
    for phrase in p7_ru.get("importance_framing_ban", []):
        # Remove the whole clause containing this phrase (up to comma or period)
        text = re.sub(
            re.escape(phrase) + r"[^,.!?;]*",
            "",
            text,
            flags=re.IGNORECASE,
        )

    # P7 Russian: announcement ban (remove whole sentence)
    for phrase in p7_ru.get("announcement_ban", []):
        text = re.sub(
            r"[^.!?]*" + re.escape(phrase) + r"[^.!?]*[.!?]",
            "",
            text,
            flags=re.IGNORECASE,
        )

    # P29 Russian: absolute ban connectors
    for connector in p29_ru.get("absolute_ban", []):
        text = re.sub(
            r"(?m)^" + re.escape(connector) + r",?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\.\s+" + re.escape(connector) + r",?\s*",
            ". ",
            text,
            flags=re.IGNORECASE,
        )

    # P29 Russian: near-ban (кроме того — keep max 1 per document)
    for connector, max_count in p29_ru.get("near_ban_max_per_doc", {}).items():
        occurrences = list(re.finditer(re.escape(connector), text, re.IGNORECASE))
        if len(occurrences) > max_count:
            excess_starts = [m.start() for m in occurrences[max_count:]]
            # Remove excess occurrences (iterate in reverse to keep indices valid)
            for start in reversed(excess_starts):
                text = text[:start] + text[start + len(connector):]

    # Clean up double spaces left by removals
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_headings(text: str) -> str:
    """Op 8: Convert Title Case headings to Sentence case (P16)."""
    def to_sentence_case(match: re.Match) -> str:
        prefix = match.group(1)  # the ## part
        heading = match.group(2)
        words = heading.split()
        if not words:
            return match.group(0)
        result = [words[0]]  # keep first word capitalized
        for w in words[1:]:
            # keep proper nouns only if ALL-CAPS (acronyms like AI, GDP, etc.)
            if w.isupper() and len(w) > 1:
                result.append(w)
            else:
                result.append(w.lower())
        return prefix + " ".join(result)

    return re.sub(r"(#{1,3}\s+)(.+)$", to_sentence_case, text, flags=re.MULTILINE)


def remove_curly_quotes(text: str) -> str:
    """Op for P18: Replace curly quotes with straight ASCII quotes."""
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def remove_emojis(text: str) -> str:
    """Remove decorative emojis (P17)."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def rebalance_connectors(text: str, but_however_ratio: float = 1.0) -> str:
    """
    Op 13: Connector rebalancer.
    - Remove 'Furthermore', 'Additionally' → replace with direct continuation or 'But'
    - Convert excess 'Moreover' → 'Also' or direct continuation
    - If But:However < 2:1, convert 30% of 'However' starts to 'But'
    """
    # Replace Additionally / Furthermore at sentence start
    text = re.sub(r"(?m)^Additionally,?\s*", "", text)
    text = re.sub(r"(?m)^Furthermore,?\s*", "", text)
    text = re.sub(r"\. Additionally,?\s*", ". ", text)
    text = re.sub(r"\. Furthermore,?\s*", ". ", text)

    # Rate-limit Moreover (leave ≤ 1 per 500 words; convert rest to 'Also')
    moreover_count = len(re.findall(r"\bMoreover\b", text, re.IGNORECASE))
    words = len(text.split())
    max_moreover = max(1, words // 500)
    if moreover_count > max_moreover:
        excess = moreover_count - max_moreover
        replaced = 0

        def replace_moreover(m: re.Match) -> str:
            nonlocal replaced
            if replaced < excess:
                replaced += 1
                return "Also"
            return m.group(0)

        text = re.sub(r"\bMoreover\b", replace_moreover, text)

    # Inject 'Also' if count is 0 (handle in LLM prompt; here just remove banned)

    # Rebalance However → But if ratio < 2:1
    if but_however_ratio < 2.0:
        however_count = len(re.findall(r"(?m)^However,?\b", text))
        convert_count = max(0, int(however_count * 0.30))
        converted = 0

        def maybe_convert_however(m: re.Match) -> str:
            nonlocal converted
            if converted < convert_count:
                converted += 1
                return m.group(0).replace("However", "But").replace("however", "but")
            return m.group(0)

        text = re.sub(r"(?m)^However,?\s", maybe_convert_however, text)

    return text


def convert_standalone_definitions(text: str) -> str:
    """Op 15: Convert standalone definition sentences to parenthetical embedding."""
    pattern = re.compile(
        r"([A-Z][^.!?]*(?:is defined as|refers to|can be defined as|is understood as)"
        r"\s+([^.!?]+)\.)",
        re.IGNORECASE,
    )

    def replace_def(m: re.Match) -> str:
        # Just remove the standalone definition; LLM prompt handles parenthetical insertion
        return ""

    return pattern.sub(replace_def, text)


# ── Op 14: Section asymmetry enforcer ────────────────────────────────────────

def _check_section_asymmetry(text: str) -> dict:
    """
    Op 14: Analyse section word-count CV and flag imbalances for LLM guidance.
    Only meaningful when ≥ 3 sections are present (headed by #/##/###).
    """
    import numpy as np
    section_bodies = re.split(r"(?m)^#{1,3}\s+.+$", text)
    sections = [s.strip() for s in section_bodies if s.strip()]
    if len(sections) < 3:
        return {"cv": 0.0, "flagged_low_cv": False, "section_count": len(sections)}

    counts = [len(s.split()) for s in sections]
    arr = np.array(counts, dtype=float)
    cv = float(arr.std() / arr.mean()) if arr.mean() > 0 else 0.0

    body_total = sum(counts[:-1]) if len(counts) > 1 else sum(counts)
    conclusion_pct = counts[-1] / body_total if body_total > 0 else 0.0

    return {
        "cv": cv,
        "section_word_counts": counts,
        "flagged_low_cv": cv < 0.20,
        "conclusion_pct_of_body": conclusion_pct,
        "conclusion_oversized": conclusion_pct > 0.20,
        "section_count": len(sections),
    }


# ── Op 16: Domain-specific passive voice handler ──────────────────────────────

_PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|has been|have been|had been|will be|being)\s+"
    r"(?:\w+ed|built|done|made|shown|found|given|known|seen|told|taught|"
    r"drawn|gone|taken|broken|chosen|written|spoken|driven)\b",
    re.IGNORECASE,
)


def _get_passive_voice_guidance(text: str, domain: str) -> dict:
    """
    Op 16: Count passive constructions and return domain-appropriate threshold + guidance.
    CS/math: preserve passive (convention). Journalistic/general: flag > 20%.
    Management/humanities: flag > 35%.
    """
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sents:
        return {"passive_pct": 0.0, "flagged": False, "guidance": ""}

    passive_sents = sum(1 for s in sents if _PASSIVE_RE.search(s))
    passive_pct = passive_sents / len(sents)

    cs_math_domains = {"academic-cs", "academic-math", "cs", "math"}
    journalistic_domains = {"journalistic", "general"}

    if domain in cs_math_domains:
        threshold = 1.0
        guidance = "Preserve passive voice — standard convention in CS/math domain."
    elif domain in journalistic_domains:
        threshold = 0.20
        guidance = (
            f"Passive voice at {passive_pct:.0%} — target < 20%."
            " Convert with named agents where the rewrite reads naturally."
        )
    else:
        threshold = 0.35
        guidance = (
            f"Passive voice at {passive_pct:.0%} — flag if > 35%."
            " Convert key passive constructions to active where clearly better."
        )

    flagged = passive_pct > threshold
    return {
        "passive_pct": passive_pct,
        "passive_sents": passive_sents,
        "total_sents": len(sents),
        "domain_threshold": threshold,
        "flagged": flagged,
        "guidance": guidance,
    }


# ── LLM-based operations ──────────────────────────────────────────────────────

def _run_llm_structural_rewrite(
    text: str,
    domain: str,
    register: str,
    analysis_report: Optional[dict] = None,
    language: str = "en",
) -> str:
    """
    Calls Claude with the structural_rewrite prompt.
    Handles: parallelism breaking (P9), triad busting (P10), list-to-prose (P15),
    sentence/paragraph length variation (P25), idea-order disruption (P26),
    sentence-starter diversification (P27), section asymmetry (P37).
    Language-aware via {{LANGUAGE}} template variable (AC-3, AC-9).
    """
    system_prompt = _load_prompt("structural_rewrite")
    system_prompt = system_prompt.replace("{{DOMAIN}}", domain)
    system_prompt = system_prompt.replace("{{REGISTER}}", register)
    system_prompt = system_prompt.replace("{{LANGUAGE}}", language)

    # Op 14: Section asymmetry check
    section_asym = _check_section_asymmetry(text)
    # Op 16: Domain passive voice guidance
    passive_guidance = _get_passive_voice_guidance(text, domain)

    report_context = ""
    if analysis_report:
        triplets = analysis_report.get("triplets", {}).get("total", 0)
        para_cv = analysis_report.get("para_cv", 0)
        section_cv = analysis_report.get("section_cv", 0)
        but_however = analysis_report.get("but_however", {}).get("ratio", 0)
        report_context = (
            f"\n\nAnalysis context:\n"
            f"- Triplet count (must reach 0): {triplets}\n"
            f"- Paragraph CV (target ≥ 0.50, current: {para_cv:.3f})\n"
            f"- Section CV (target ≥ 0.30, current: {section_cv:.3f})\n"
            f"- But:However ratio (target ≥ 2:1, current: {but_however:.2f})\n"
        )

    # Append Op 14 + Op 16 context regardless of analysis_report presence
    asym_note = ""
    if section_asym["section_count"] >= 3:
        asym_note = (
            f"- Section asymmetry CV: {section_asym['cv']:.3f}"
            f" (target ≥ 0.30; {'LOW — sections too uniform' if section_asym['flagged_low_cv'] else 'OK'})\n"
        )
        if section_asym.get("conclusion_oversized"):
            asym_note += (
                f"  Conclusion is {section_asym['conclusion_pct_of_body']:.0%} of body"
                " — compress conclusion to < 20% of body length.\n"
            )
    passive_note = f"- Passive voice: {passive_guidance['guidance']}\n"
    if asym_note or passive_note:
        report_context += (
            f"\n\nOp 14/16 guidance:\n{asym_note}{passive_note}"
        )

    user_prompt = (
        f"Rewrite the following text according to your structural transformation rules."
        f"{report_context}\n\n"
        f"TEXT TO REWRITE:\n{text}\n\nOUTPUT (rewritten text only, no explanation):"
    )

    cfg = _load_config()
    temperature = cfg["pipeline"]["rewrite_temperature"]
    return _call_claude(system_prompt, user_prompt, temperature=temperature)


def _run_llm_connector_rebalancer(
    text: str,
    domain: str,
    register: str,
    connector_report: Optional[dict] = None,
    language: str = "en",
) -> str:
    """Op 13: LLM-based connector rebalancing pass."""
    system_prompt = _load_prompt("connector_rebalancer")
    system_prompt = system_prompt.replace("{{DOMAIN}}", domain)
    system_prompt = system_prompt.replace("{{REGISTER}}", register)
    system_prompt = system_prompt.replace("{{LANGUAGE}}", language)

    report_context = ""
    if connector_report:
        by_type = connector_report.get("by_type", {})
        ratio = connector_report.get("but_however", {}).get("ratio", 0)
        also = connector_report.get("also_frequency", {}).get("per_page", 0)
        report_context = (
            f"\n\nConnector analysis:\n"
            f"- Connector frequencies: {by_type}\n"
            f"- But:However ratio: {ratio:.2f} (target ≥ 2:1)\n"
            f"- Also per page: {also:.2f} (target ≥ 0.08)\n"
        )

    user_prompt = (
        f"Rebalance connectors in the following text according to your rules."
        f"{report_context}\n\n"
        f"TEXT:\n{text}\n\nOUTPUT (rewritten text only):"
    )

    cfg = _load_config()
    return _call_claude(system_prompt, user_prompt,
                        temperature=cfg["pipeline"]["rewrite_temperature"])


# ── StructuralRewriter class ──────────────────────────────────────────────────

class StructuralRewriter:
    """
    Stage 2: Structural & Format Rewrite.
    16 operations: local regex passes + LLM rewrite.
    """

    def transform(
        self,
        text: str,
        domain: str = "general",
        register: str = "general",
        analysis_report: Optional[dict] = None,
        language: str = "en",
    ) -> str:
        logger.info(
            f"Stage 2 starting | words={len(text.split())} | "
            f"domain={domain} | register={register} | language={language}"
        )
        t0 = time.time()

        # ── Local passes (order matters) ──────────────────────────────────
        # Op 1: Announcement opener remover (P9) — language-aware
        if language == "en":
            text = remove_announcement_openers(text)
        else:
            # Russian announcement patterns handled by _apply_russian_patterns below
            pass

        # Op 2: Copula restoration (P8) — English only (Russian has different copula norms)
        if language == "en":
            text = restore_copulas(text)

        # Op 5: False range eliminator (P12) — English heuristic only
        if language == "en":
            text = remove_false_ranges(text)

        # Op 6: Em dash reducer — LANGUAGE GATE (AC-1)
        if language == "en":
            text = reduce_em_dashes(text)          # English: target 0 em dashes
        else:
            text = reduce_em_dashes_ru(text)        # Russian: conservative reduction

        # Op 8: Heading normalizer (P16) — applies to both languages
        text = normalize_headings(text)

        # P17: Emoji remover — applies to both languages
        text = remove_emojis(text)

        # P18: Quote normalization — LANGUAGE GATE (AC-8)
        if language == "en":
            text = remove_curly_quotes(text)       # English: ASCII straight quotes
        else:
            text = normalize_quotes_ru(text)        # Russian: guillemets «»

        # Op 15: Standalone definition converter (P35) — language-aware
        if language == "en":
            text = convert_standalone_definitions(text)
        # Russian "Под X понимается Y" form handled in LLM prompt via {{LANGUAGE}}

        # Op 13: Regex-based connector rebalancing — English only
        # Russian connectors handled by _apply_russian_patterns
        if language == "en":
            but_however_ratio = 1.0
            if analysis_report:
                but_however_ratio = analysis_report.get(
                    "but_however", {}
                ).get("ratio", 1.0)
            text = rebalance_connectors(text, but_however_ratio)

        # Russian-specific pattern removal (P7_ru + P29_ru)
        if language == "ru":
            cfg = _load_config()
            text = _apply_russian_patterns(text, cfg)

        # ── LLM pass: structural rewrite (P9, P10, P15, P25, P26, P27, P37) ──
        # Pass {{LANGUAGE}} to prompt for language-aware rewriting (AC-3, AC-9)
        text = _run_llm_structural_rewrite(
            text, domain, register, analysis_report, language=language
        )

        # ── LLM pass: connector rebalancer ───────────────────────────────────
        connector_report = None
        if analysis_report:
            connector_report = {
                "by_type": analysis_report.get("connector_density", {}).get(
                    "by_type", {}
                ),
                "but_however": analysis_report.get("but_however", {}),
                "also_frequency": analysis_report.get("also_frequency", {}),
            }
        text = _run_llm_connector_rebalancer(
            text, domain, register, connector_report, language=language
        )

        elapsed = time.time() - t0
        logger.info(
            f"Stage 2 complete | words={len(text.split())} | elapsed={elapsed:.2f}s"
        )
        return text

    def score(self, text: str) -> dict:
        """Quick structural metrics on already-transformed text."""
        from pipeline.analyzer import (
            compute_para_cv,
            compute_section_cv,
            count_triplets,
            compute_but_however_ratio,
            count_announcement_openers,
        )
        return {
            "para_cv": compute_para_cv(text),
            "section_cv": compute_section_cv(text),
            "triplets": count_triplets(text),
            "but_however": compute_but_however_ratio(text),
            "announcement_openers": count_announcement_openers(text),
            "word_count": len(text.split()),
        }
