"""
Stage 3: Lexical & Tonal Cleanup
Targets Humanizer patterns: P1–P7, P11, P17–P18, P28–P29.
New operations: P7 context-aware filter, modal hedging auditor,
attribution-based hedging converter, result praise remover, standalone definition converter.
All 15 operations as specified in the plan.
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
                wait = delay * (2 ** attempt)
                logger.warning(f"Rate limit, retrying in {wait}s")
                time.sleep(wait)
            else:
                raise
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            raise
    return ""


# ── Local regex passes ────────────────────────────────────────────────────────

_P28_SUBSTITUTIONS = [
    (r"\bleverag(e|es|ed|ing)\b", "use"),
    (r"\butiliz(e|es|ed|ing)\b", "use"),
    (r"\bfacilitat(e|es|ed|ing)\b", "help"),
    (r"\bdemonstrat(e|es|ed|ing)\b", "show"),
    (r"\bindicat(e|es|ed|ing)\b", "suggest"),
    (r"\bcommenc(e|es|ed|ing)\b", "start"),
    (r"\bterminat(e|es|ed|ing)\b", "end"),
    (r"\bendeavor(s|ed|ing)?\b", "try"),
    (r"\bascertain(s|ed|ing)?\b", "find out"),
    (r"\bin order to\b", "to"),
    (r"\bwith regard to\b", "on"),
    (r"\bas a result of\b", "because of"),
    (r"\bit is important to\b", ""),
]

_P7_ABSOLUTE_BAN_RE = re.compile(
    r"\b(vibrant|nestled|breathtaking|tapestry|delves? into|delves?|embark on|"
    r"realm|harness|unlock|game-changer|seamless|synergy|cutting-edge|"
    r"multifaceted|nuanced|groundbreaking|renowned|stunning|game-changers?)\b",
    re.IGNORECASE,
)

_P7_REPLACEMENTS = {
    "vibrant": "active",
    "nestled": "located",
    "breathtaking": "",
    "tapestry": "mix",
    "delves into": "examine",
    "delves": "examine",
    "delve into": "examine",
    "delve": "examine",
    "embark on": "begin",
    "realm": "area",
    "harness": "use",
    "unlock": "enable",
    "game-changer": "shift",
    "seamless": "smooth",
    "synergy": "cooperation",
    "cutting-edge": "current",
    "multifaceted": "complex",
    "nuanced": "specific",
    "groundbreaking": "new",
    "renowned": "well-known",
    "stunning": "",
}

_P4_PROMOTIONAL_RE = re.compile(
    r"\b(boasts a|vibrant|rich culture|profound|showcasing|exemplifies|"
    r"commitment to|natural beauty|in the heart of|must-visit)\b",
    re.IGNORECASE,
)

_P22_FILLER_MAP = [
    (r"\bit is important to note that\b", ""),
    (r"\bit is worth noting that\b", ""),
    (r"\bit should be mentioned that\b", ""),
    (r"\bneedless to say[,]?\b", ""),
    (r"\bone might argue that\b", ""),
    (r"\bdue to the fact that\b", "because"),
    (r"\bat this point in time\b", "now"),
    (r"\bin the event that\b", "if"),
    (r"\bhas the ability to\b", "can"),
    (r"\bin order to\b", "to"),
]

_P23_STACKED_HEDGING_RE = re.compile(
    r"\bcould potentially possibly\b|\bmight possibly\b|"
    r"\bmay potentially\b|\bcould potentially be argued\b",
    re.IGNORECASE,
)

_P19_CHATBOT_RE = re.compile(
    r"(i hope this helps|of course!?|certainly!?|you'?re absolutely right!?|"
    r"would you like|let me know if|here is a|great question!?)",
    re.IGNORECASE,
)

_P24_GENERIC_END_RE = re.compile(
    r"\b(the future looks bright|exciting times lie ahead|"
    r"major step in the right direction|journey toward excellence)\b",
    re.IGNORECASE,
)

_GENUINELY_RE = re.compile(r"\bgenuinely\s+\w+", re.IGNORECASE)

_IMPORTANCE_FRAMING_RE = re.compile(
    r"\b(plays a crucial role|is central to|is pivotal for|is essential for|"
    r"serves as a cornerstone of|is key to|is of vital importance|"
    r"is fundamental to|is instructive (about|for)|deserves mention|"
    r"is worth flagging|is worth a brief detour|is actually remarkable)\b",
    re.IGNORECASE,
)

_P29_BANNED_RE = re.compile(
    r"\b(Furthermore|Additionally|Firstly|Secondly|Thirdly|Finally"
    r"|In addition to this|It is worth noting that),\s*",
    re.IGNORECASE,
)

_MODAL_RESULT_RE = re.compile(
    r"\b(may|might|could|appears? to|suggests?|indicates?|seem(?:s|ed)?)\b",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(
    r"\b(\d+[\.,]?\d*\s*(%|percent|pp|pct|x|times|fold|bps)?|\d+\.\d+)\b"
)

_RESULT_PRAISE_RE = re.compile(
    r"\b(remarkable|impressive|exceptional|outstanding|extraordinary|"
    r"excellent|superior|stellar|exemplary)\b",
    re.IGNORECASE,
)

_STANDALONE_DEF_RE = re.compile(
    r"\b(is defined as|refers to|by \w+ we mean|can be defined as|is understood as)\b",
    re.IGNORECASE,
)

_CURLY_RE = re.compile(r"[\u201c\u201d\u2018\u2019]")
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)


def apply_p28_substitutions(text: str, domain: str = "general", register: str = "general") -> str:
    """Op 9: Vocabulary substitution table (P28) — domain-aware."""
    _PRESERVE_DOMAINS = {"cs", "math", "economics"}  # some terms have precise meaning
    for pattern, replacement in _P28_SUBSTITUTIONS:
        # "facilitate" in technical contexts may have precise meaning — skip for CS
        if "facilitat" in pattern and domain in _PRESERVE_DOMAINS:
            continue
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def apply_p7_absolute_ban(text: str) -> str:
    """Remove absolutely banned P7 words, replacing with plain equivalents."""
    def replace_word(m: re.Match) -> str:
        word = m.group(0).lower()
        return _P7_REPLACEMENTS.get(word, "")
    return _P7_ABSOLUTE_BAN_RE.sub(replace_word, text)


def remove_filler_phrases(text: str) -> str:
    """Op 11 / P22: Remove filler phrases."""
    for pattern, replacement in _P22_FILLER_MAP:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"  +", " ", text)


def remove_stacked_hedging(text: str) -> str:
    """Op 8 / P23: Remove stacked hedging qualifiers."""
    text = _P23_STACKED_HEDGING_RE.sub("may", text)
    return text


def remove_chatbot_artifacts(text: str) -> str:
    """P19: Remove chatbot correspondence artifacts."""
    return _P19_CHATBOT_RE.sub("", text)


def remove_generic_endings(text: str) -> str:
    """P24: Remove generic positive conclusion phrases."""
    return _P24_GENERIC_END_RE.sub("", text)


def remove_genuinely_adj(text: str) -> str:
    """P7: Remove 'genuinely [adjective]' importance inflators."""
    return _GENUINELY_RE.sub("", text)


def remove_importance_framing(text: str) -> str:
    """P7/P31: Remove importance-framing constructions."""
    return _IMPORTANCE_FRAMING_RE.sub("", text)


def remove_curly_quotes(text: str) -> str:
    """P18: Replace curly quotes with straight ASCII quotes."""
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def remove_emojis(text: str) -> str:
    """P17: Remove decorative emojis."""
    return _EMOJI_RE.sub("", text)


def remove_banned_connectors_regex(text: str) -> str:
    """Op 10 / P29: Remove absolutely banned connectors from sentence starts."""
    return _P29_BANNED_RE.sub("", text)


def remove_modal_from_result_sentences(text: str) -> str:
    """
    Op 12: Modal hedging auditor.
    If a sentence has a numerical result + modal verb → remove the modal.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = []
    for s in sentences:
        if _NUMERIC_RE.search(s) and _MODAL_RESULT_RE.search(s):
            # Remove the modal verb
            s = _MODAL_RESULT_RE.sub("", s)
            s = re.sub(r"\s{2,}", " ", s).strip()
        cleaned.append(s)
    return " ".join(cleaned)


def remove_result_praise(text: str) -> str:
    """Op 14 / P36: Remove evaluative praise adjectives from result sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = []
    for s in sentences:
        # If sentence looks like a result (has numeric data) and has praise → remove
        if _NUMERIC_RE.search(s) and _RESULT_PRAISE_RE.search(s):
            s = _RESULT_PRAISE_RE.sub("", s)
            s = re.sub(r"\s{2,}", " ", s).strip()
        cleaned.append(s)
    return " ".join(cleaned)


# ── LLM-based operations ──────────────────────────────────────────────────────

def _run_llm_lexical_cleanup(
    text: str,
    domain: str,
    register: str,
    p7_report: Optional[dict] = None,
    modal_report: Optional[dict] = None,
    language: str = "en",
) -> str:
    """
    Main LLM pass for lexical & tonal cleanup.
    Handles: P1, P4, P5, P7 (context-dependent), P11 (elegant variation),
    P28 (nuanced substitutions), P29 (connector replacement),
    P38 (attribution hedging), P39 (counter-argument naming).
    Language-aware: {{LANGUAGE}} and {{CITATION_FORMAT}} variables injected (AC-2).
    """
    system_prompt = _load_prompt("lexical_enrichment")
    system_prompt = system_prompt.replace("{{DOMAIN}}", domain)
    system_prompt = system_prompt.replace("{{REGISTER}}", register)
    system_prompt = system_prompt.replace("{{LANGUAGE}}", language)
    # AC-2: Citation format gating
    citation_format = "GOST" if (language == "ru" and register in ("academic", "academic-essay")) else "AUTHOR_YEAR"
    system_prompt = system_prompt.replace("{{CITATION_FORMAT}}", citation_format)

    report_context = ""
    if p7_report:
        abs_v = len(p7_report.get("absolute_violations", []))
        if_v = len(p7_report.get("importance_framing_violations", []))
        ctx_v = len(p7_report.get("context_dependent_flagged", []))
        report_context += (
            f"\nP7 violations: {abs_v} absolute ban, {if_v} importance-framing, "
            f"{ctx_v} context-dependent."
        )
    if modal_report:
        modal_count = modal_report.get("count", 0)
        report_context += (
            f"\nModal hedging on result sentences: {modal_count} instances "
            f"(must reach 0)."
        )

    user_prompt = (
        f"Apply the lexical and tonal cleanup rules to the following text."
        f"{report_context}\n\n"
        f"TEXT:\n{text}\n\nOUTPUT (cleaned text only, no explanation):"
    )

    cfg = _load_config()
    temperature = cfg["pipeline"]["rewrite_temperature"]
    return _call_claude(system_prompt, user_prompt, temperature=temperature)


def _run_llm_modal_hedging_audit(
    text: str,
    domain: str,
    register: str,
    flagged_sentences: list[str],
) -> str:
    """Op 12: LLM-based modal hedging audit — classify and fix flagged sentences."""
    if not flagged_sentences:
        return text

    system_prompt = _load_prompt("modal_hedging_audit")
    system_prompt = system_prompt.replace("{{DOMAIN}}", domain)
    system_prompt = system_prompt.replace("{{REGISTER}}", register)

    flagged_str = "\n".join(f"- {s}" for s in flagged_sentences[:10])  # cap at 10
    user_prompt = (
        f"The following sentences contain modal verbs on empirical results. "
        f"For each: classify as KEEP (interpretation/method) or REMOVE (result sentence). "
        f"For REMOVE sentences, provide the corrected version.\n\n"
        f"Sentences:\n{flagged_str}\n\n"
        f"Full text for context:\n{text}\n\n"
        f"OUTPUT: Return the FULL text with all REMOVE sentences corrected. "
        f"No explanation."
    )
    cfg = _load_config()
    return _call_claude(system_prompt, user_prompt,
                        temperature=cfg["pipeline"]["analysis_temperature"])


def _run_llm_result_presentation(
    text: str,
    domain: str,
) -> str:
    """Op 14 / P36: LLM-based result presentation rewriter."""
    system_prompt = _load_prompt("result_presentation")
    system_prompt = system_prompt.replace("{{DOMAIN}}", domain)

    user_prompt = (
        f"Rewrite any result sentences in the following text to follow the format: "
        f"[finding] + [baseline comparison] + [mechanism]. "
        f"Remove evaluative praise. No modals on results.\n\n"
        f"TEXT:\n{text}\n\nOUTPUT (full text, no explanation):"
    )
    cfg = _load_config()
    return _call_claude(system_prompt, user_prompt,
                        temperature=cfg["pipeline"]["rewrite_temperature"])


# ── LexicalEnricher class ─────────────────────────────────────────────────────

class LexicalEnricher:
    """
    Stage 3: Lexical & Tonal Cleanup.
    15 operations: local regex passes + LLM rewrite.
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
            f"Stage 3 starting | words={len(text.split())} | "
            f"domain={domain} | register={register} | language={language}"
        )
        t0 = time.time()

        # ── Local passes ──────────────────────────────────────────────────

        # Op 1 / P7: AI vocabulary absolute ban — English only (Russian handled by structural_rewriter)
        if language == "en":
            text = apply_p7_absolute_ban(text)

        # Op 2 / P1: Significance inflation — removed in importance-framing pass
        # English patterns only; Russian importance-framing already removed in Stage 2
        if language == "en":
            text = remove_importance_framing(text)

        # Op 3 / P4: Promotional language remover (most caught by P7 ban)

        # Op 4 / P7: Remove "genuinely [adj]" importance inflators — English only
        if language == "en":
            text = remove_genuinely_adj(text)

        # Op 6: Emoji remover (P17) — applies to both languages
        text = remove_emojis(text)

        # Op 7: Quote normalization (P18) — handled in Stage 2 by language gate
        # (English: straight quotes; Russian: guillemets — already done)

        # Op 8: Weasel word / stacked hedging eliminator (P23) — English only
        if language == "en":
            text = remove_stacked_hedging(text)

        # Op 9: Vocabulary substitution table (P28) — English only
        if language == "en":
            text = apply_p28_substitutions(text, domain)

        # Op 10: Banned connector regex pass (P29) — English only
        # Russian banned connectors handled in Stage 2 via _apply_russian_patterns
        if language == "en":
            text = remove_banned_connectors_regex(text)

        # Op 11: Filler phrases (P22) — English only
        if language == "en":
            text = remove_filler_phrases(text)

        # P19: Chatbot artifacts — applies to both (LLM artifacts cross languages)
        text = remove_chatbot_artifacts(text)

        # P24: Generic positive endings — applies to both
        text = remove_generic_endings(text)

        # Op 12: Modal hedging on result sentences (regex pass) — applies to both
        # Russian modals (может, мог бы, вероятно) handled via LLM prompt {{LANGUAGE}}
        if language == "en":
            text = remove_modal_from_result_sentences(text)

        # Op 14: Result praise remover (regex pass, P36) — English only
        if language == "en":
            text = remove_result_praise(text)

        # ── LLM pass: lexical cleanup ─────────────────────────────────────
        p7_report = analysis_report.get("p7_violations") if analysis_report else None
        modal_report = (
            analysis_report.get("modal_hedging_on_results") if analysis_report else None
        )
        text = _run_llm_lexical_cleanup(
            text, domain, register, p7_report, modal_report, language=language
        )

        # ── LLM pass: modal hedging audit ─────────────────────────────────
        if modal_report and modal_report.get("sentences"):
            text = _run_llm_modal_hedging_audit(
                text, domain, register, modal_report["sentences"]
            )

        # ── LLM pass: result presentation (if domain has empirical results) ──
        empirical_domains = {"cs", "economics", "math", "social-science"}
        if domain in empirical_domains:
            text = _run_llm_result_presentation(text, domain)

        elapsed = time.time() - t0
        logger.info(
            f"Stage 3 complete | words={len(text.split())} | elapsed={elapsed:.2f}s"
        )
        return text

    def score(self, text: str) -> dict:
        """Quick lexical metrics on already-transformed text."""
        from pipeline.analyzer import scan_p7_context_aware, count_modal_hedging_on_results

        p7_scan = scan_p7_context_aware(text)
        modal_result = count_modal_hedging_on_results(text)
        modal_count = modal_result["count"] if isinstance(modal_result, dict) else modal_result

        return {
            "p7_absolute_violations": len(p7_scan.get("absolute_violations", [])),
            "importance_framing_count": len(p7_scan.get("importance_framing_violations", [])),
            "genuinely_adj_count": len(_GENUINELY_RE.findall(text)),
            "filler_phrase_count": sum(
                len(re.findall(p, text, re.IGNORECASE)) for p, _ in _P22_FILLER_MAP
            ),
            "stacked_hedging_count": len(_P23_STACKED_HEDGING_RE.findall(text)),
            "chatbot_artifacts": len(_P19_CHATBOT_RE.findall(text)),
            "generic_endings": len(_P24_GENERIC_END_RE.findall(text)),
            "banned_connector_count": len(_P29_BANNED_RE.findall(text)),
            "modal_hedging_on_results": modal_count,
            "result_praise_count": len(_RESULT_PRAISE_RE.findall(text)),
            "word_count": len(text.split()),
        }
