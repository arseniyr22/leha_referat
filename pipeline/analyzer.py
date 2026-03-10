"""
Stage 1: Analysis
Runs entirely locally — no API cost.
Produces a pattern report + baseline metrics that feed into Stage 2 prompt construction.
All 20 operations as specified in the plan.
"""
from __future__ import annotations

import re
import math
import yaml
from pathlib import Path
from typing import Optional
from collections import Counter

import numpy as np
import spacy
from loguru import logger
from transformers import GPT2LMHeadModel, GPT2TokenizerFast
import torch

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_config: dict = {}


def _load_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


# ── lazy model loaders ──────────────────────────────────────────────────────

_nlp: Optional[spacy.Language] = None
_gpt2_model: Optional[GPT2LMHeadModel] = None
_gpt2_tok: Optional[GPT2TokenizerFast] = None


def _get_nlp() -> spacy.Language:
    global _nlp
    if _nlp is None:
        cfg = _load_config()
        model_name = cfg.get("local_models", {}).get("spacy_model", "en_core_web_sm")
        _nlp = spacy.load(model_name)
    return _nlp


def _get_gpt2():
    global _gpt2_model, _gpt2_tok
    if _gpt2_model is None:
        cfg = _load_config()
        model_name = cfg.get("local_models", {}).get("perplexity_model", "gpt2")
        _gpt2_tok = GPT2TokenizerFast.from_pretrained(model_name)
        _gpt2_model = GPT2LMHeadModel.from_pretrained(model_name)
        _gpt2_model.eval()
    return _gpt2_model, _gpt2_tok


# ── helpers ─────────────────────────────────────────────────────────────────

def _sentences(text: str) -> list[str]:
    nlp = _get_nlp()
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def _sections(text: str) -> list[str]:
    """Split on markdown headings (# / ## / ###)."""
    parts = re.split(r"(?m)^#{1,3}\s+.+$", text)
    return [p.strip() for p in parts if p.strip()]


def _token_count(text: str) -> int:
    _, tok = _get_gpt2()
    return len(tok.encode(text))


def _word_count(text: str) -> int:
    return len(text.split())


def _coeff_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    arr = np.array(values, dtype=float)
    mean = arr.mean()
    if mean == 0:
        return 0.0
    return float(arr.std() / mean)


# ── Operation 2: Baseline perplexity ────────────────────────────────────────

def compute_perplexity(text: str) -> float:
    """GPT-2 perplexity on raw input text."""
    model, tok = _get_gpt2()
    encodings = tok(text, return_tensors="pt", truncation=True, max_length=1024)
    input_ids = encodings.input_ids
    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
        loss = outputs.loss
    return float(torch.exp(loss).item())


# ── Operation 3: Sentence burstiness ────────────────────────────────────────

def compute_sentence_cv(text: str) -> float:
    """Coefficient of variation of sentence token lengths."""
    sents = _sentences(text)
    if len(sents) < 2:
        return 0.0
    _, tok = _get_gpt2()
    lengths = [len(tok.encode(s)) for s in sents]
    return _coeff_of_variation([float(l) for l in lengths])


# ── Operation 5: Paragraph burstiness ───────────────────────────────────────

def compute_para_cv(text: str) -> float:
    """Coefficient of variation of paragraph token counts."""
    paras = _paragraphs(text)
    if len(paras) < 2:
        return 0.0
    _, tok = _get_gpt2()
    lengths = [len(tok.encode(p)) for p in paras]
    return _coeff_of_variation([float(l) for l in lengths])


# ── Operation 16: Section CV ─────────────────────────────────────────────────

def compute_section_cv(text: str) -> float:
    """CV of section word counts; only meaningful with ≥ 3 sections."""
    sections = _sections(text)
    if len(sections) < 3:
        return 0.0
    counts = [_word_count(s) for s in sections]
    return _coeff_of_variation([float(c) for c in counts])


# ── Operation 6: Transition monotony ────────────────────────────────────────

_BANNED_CONNECTORS = {
    "furthermore", "additionally", "moreover", "in addition",
    "firstly", "secondly", "thirdly", "finally", "it is worth noting that",
    "in addition to this",
}

_ALL_CONNECTORS_RE = re.compile(
    r"\b(furthermore|additionally|moreover|in addition|firstly|secondly|thirdly|"
    r"finally|however|thus|therefore|but|yet|also|that said|granted|to be fair|"
    r"meanwhile|then|next|although|though|while)\b",
    re.IGNORECASE,
)


def compute_transition_monotony(text: str) -> dict:
    """
    Returns connector_freq dict and pct_sentences_starting_with_banned.
    """
    sents = _sentences(text)
    banned_starts = 0
    connector_freq: Counter = Counter()

    for s in sents:
        first_word = s.split()[0].lower().rstrip(",") if s.split() else ""
        if first_word in _BANNED_CONNECTORS:
            banned_starts += 1

    for m in _ALL_CONNECTORS_RE.finditer(text):
        connector_freq[m.group(0).lower()] += 1

    pct_banned = banned_starts / max(len(sents), 1)
    return {"connector_freq": dict(connector_freq), "pct_sentences_banned_start": pct_banned}


# ── Operation 7: Announcement opener count ───────────────────────────────────

_ANNOUNCEMENT_PATTERNS = [
    r"here'?s the (problem|issue|thing) with",
    r"\bis worth a brief detour\b",
    r"\bthere'?s also a \w+ worth flagging\b",
    r"\bone thing you rarely see\b",
    r"\b\w+ also deserves mention\b",
    r"\bi mention this mostly because\b",
    r"\bis actually (remarkable|significant|notable|important)\b",
    r"\bis instructive (about|for)\b",
    r"\brepeats the same (story|pattern) across\b",
    r"\bthis section will (explore|examine|discuss|cover)\b",
    r"\bin what follows",
    r"\bwe will now examine\b",
    r"\bdeserves mention\b",
    r"\bworth flagging\b",
    r"\bis worth a detour\b",
    r"\bit is worth noting that\b",
    r"\bit is important to note that\b",
]

_ANNOUNCEMENT_RE = re.compile("|".join(_ANNOUNCEMENT_PATTERNS), re.IGNORECASE)


def count_announcement_openers(text: str) -> int:
    return len(_ANNOUNCEMENT_RE.findall(text))


# ── Operation 8: Triplet instance count ──────────────────────────────────────

_TRIPLET_NOUN_RE = re.compile(
    r"\b[\w\s\-]+,\s+[\w\s\-]+,?\s+and\s+[\w\s\-]+\b", re.IGNORECASE
)
_TRIPLET_PARTLY_RE = re.compile(
    r"\bpartly to \S+,\s*partly to \S+,?\s*and partly to\b", re.IGNORECASE
)
_TRIPLET_NO_RE = re.compile(
    r"\bno \w[\w\s]*,\s+no \w[\w\s]*,\s+no \w[\w\s]*\b", re.IGNORECASE
)


def count_triplets(text: str) -> dict:
    noun_tricolons = len(_TRIPLET_NOUN_RE.findall(text))
    adverbial_tricolons = len(_TRIPLET_PARTLY_RE.findall(text))
    negation_series = len(_TRIPLET_NO_RE.findall(text))
    return {
        "noun_tricolons": noun_tricolons,
        "adverbial_tricolons": adverbial_tricolons,
        "parallel_negation_series": negation_series,
        "total": noun_tricolons + adverbial_tricolons + negation_series,
    }


# ── Operation 9: Para-ending generalization count ────────────────────────────

_PARA_END_GENERALIZATION_PATTERNS = [
    r"complicates any (simple|straightforward|neat)\b",
    r"repeats the same \w+ across\b",
    r"\bregardless of how\b",
    r"\bany simple \w+ about\b",
    r"\bno matter (how|what|which)\b",
]

_PARA_END_GEN_RE = re.compile(
    "|".join(_PARA_END_GENERALIZATION_PATTERNS), re.IGNORECASE
)


def count_para_ending_generalizations(text: str) -> int:
    paras = _paragraphs(text)
    count = 0
    for para in paras:
        sents = _sentences(para)
        if not sents:
            continue
        last = sents[-1]
        if _PARA_END_GEN_RE.search(last):
            count += 1
    return count


# ── Operation 10: Attributive passive count ───────────────────────────────────

_ATTRIBUTIVE_PASSIVE_RE = re.compile(
    r"\bhas been (accused|noted|reported|claimed|said|alleged|criticized|described)\b",
    re.IGNORECASE,
)


def count_attributive_passives(text: str) -> int:
    return len(_ATTRIBUTIVE_PASSIVE_RE.findall(text))


# ── Operation 11: "genuinely [adj]" count ────────────────────────────────────

_GENUINELY_RE = re.compile(r"\bgenuinely\s+\w+", re.IGNORECASE)


def count_genuinely_adj(text: str) -> int:
    return len(_GENUINELY_RE.findall(text))


# ── Operation 12: But:However ratio ──────────────────────────────────────────

_BUT_SENT_START_RE = re.compile(r"(?m)^But\b", re.IGNORECASE)
_HOWEVER_RE = re.compile(r"\bHowever\b", re.IGNORECASE)


def compute_but_however_ratio(text: str) -> dict:
    but_count = len(_BUT_SENT_START_RE.findall(text))
    # also count mid-sentence "but"
    but_count += len(re.findall(r"[.!?]\s+[Bb]ut\b", text))
    however_count = len(_HOWEVER_RE.findall(text))
    ratio = but_count / max(however_count, 1)
    return {"but": but_count, "however": however_count, "ratio": ratio}


# ── Operation 13: Connector density per page ─────────────────────────────────

def compute_connector_density(text: str) -> dict:
    words = _word_count(text)
    pages = max(words / 300, 1)
    matches = _ALL_CONNECTORS_RE.findall(text)
    freq: Counter = Counter(m.lower() for m in matches)
    total = len(matches)
    density_per_page = total / pages
    return {
        "total_connectors": total,
        "density_per_page": density_per_page,
        "by_type": dict(freq),
        "also_per_page": freq.get("also", 0) / pages,
    }


# ── Operation 14: Modal hedging on result sentences ──────────────────────────

_MODAL_RE = re.compile(
    r"\b(may|might|could|appears? to|suggests?|indicates?|seem(?:s|ed)?)\b",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(
    r"\b(\d+[\.,]?\d*\s*(%|percent|pp|pct|x|times|fold|bps)?|\d+\.\d+)\b"
)


def count_modal_hedging_on_results(text: str) -> dict:
    sents = _sentences(text)
    flagged = []
    for s in sents:
        if _NUMERIC_RE.search(s) and _MODAL_RE.search(s):
            flagged.append(s)
    return {"count": len(flagged), "sentences": flagged}


# ── Operation 15: Standalone definition count ────────────────────────────────

_STANDALONE_DEF_RE = re.compile(
    r"\b(is defined as|refers to|by \w+ we mean|can be defined as|is understood as)\b",
    re.IGNORECASE,
)


def count_standalone_definitions(text: str) -> int:
    return len(_STANDALONE_DEF_RE.findall(text))


# ── Operation 17: Key term repetition audit ──────────────────────────────────

def audit_key_term_repetition(text: str, top_n: int = 5) -> dict:
    """
    Identify top N nouns by frequency. For each term:
    - Count total occurrences
    - Check paragraph distribution (should appear in ≥ half the paragraphs it can)
    - Flag if term appears in < 50% of paragraphs that mention similar content
      (proxy for synonym cycling: key term disappears mid-text, replaced by variant)
    Returns top terms with distribution metrics and a cycling_risk flag.
    """
    nlp = _get_nlp()
    paras = _paragraphs(text)
    doc = nlp(text)

    nouns = [
        token.lemma_.lower()
        for token in doc
        if token.pos_ in {"NOUN", "PROPN"} and len(token.text) > 3
    ]
    top_terms = Counter(nouns).most_common(top_n)

    results = []
    for term, count in top_terms:
        # Count in which paragraphs the term appears
        para_hits = [
            i for i, p in enumerate(paras)
            if re.search(r"\b" + re.escape(term) + r"\b", p, re.IGNORECASE)
        ]
        # Heuristic: if term appears in < 40% of paragraphs (but overall count is high),
        # it may be concentrated in bursts — potential synonym cycling elsewhere.
        para_coverage = len(para_hits) / len(paras) if paras else 1.0
        cycling_risk = count >= 5 and para_coverage < 0.40
        results.append({
            "term": term,
            "count": count,
            "para_coverage": round(para_coverage, 2),
            "cycling_risk": cycling_risk,
        })

    cycling_risk_count = sum(1 for r in results if r["cycling_risk"])
    return {
        "top_key_terms": results,
        "cycling_risk_count": cycling_risk_count,
    }


# ── Operation 18: Also frequency ─────────────────────────────────────────────

def compute_also_frequency(text: str) -> dict:
    also_count = len(re.findall(r"\balso\b", text, re.IGNORECASE))
    words = _word_count(text)
    pages = max(words / 300, 1)
    return {"count": also_count, "per_page": also_count / pages}


# ── Operation 19: P7 context-aware scan ──────────────────────────────────────

_P7_ABSOLUTE_BAN = {
    "vibrant", "nestled", "breathtaking", "tapestry", "delve", "embark",
    "realm", "harness", "unlock", "game-changer", "seamless", "synergy",
    "cutting-edge", "multifaceted", "nuanced",
}

_P7_CONTEXT_DEPENDENT = {
    "crucial", "key", "important", "significant", "highlight", "enhance",
    "valuable", "leverage",
}

_P7_IMPORTANCE_FRAMING = [
    "plays a crucial role", "is central to", "is pivotal for", "is essential for",
    "serves as a cornerstone of", "is key to", "is of vital importance",
    "is fundamental to", "is instructive about", "deserves mention",
    "is worth flagging", "is worth a brief detour", "is actually remarkable",
]

_P7_IF_RE = re.compile(
    "|".join(re.escape(p) for p in _P7_IMPORTANCE_FRAMING), re.IGNORECASE
)


def scan_p7_context_aware(text: str, domain: str = "general", register: str = None) -> dict:
    """
    Returns:
        absolute_violations: list of (word, snippet) for words in absolute ban
        importance_framing_violations: list of matched importance-framing phrases
        context_dependent_flagged: list of (word, snippet) that exceed density threshold
          or appear in importance-framing position in non-matching domain
    """
    cfg = _load_config()
    academic_domains = {"management", "economics", "politics", "cs", "math",
                        "linguistics", "social-science", "humanities"}
    is_academic = domain in academic_domains

    words_500 = _word_count(text) / max(_word_count(text) / 500, 1)

    absolute_violations = []
    for word in _P7_ABSOLUTE_BAN:
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
            snippet = text[max(0, m.start() - 40):m.end() + 40]
            absolute_violations.append({"word": word, "snippet": snippet.strip()})

    importance_framing = []
    for m in _P7_IF_RE.finditer(text):
        importance_framing.append({"phrase": m.group(0), "pos": m.start()})

    context_dependent_flagged = []
    for word in _P7_CONTEXT_DEPENDENT:
        count = len(re.findall(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE))
        density = count / max(words_500, 1) * 500
        if density >= 3:
            for m in re.finditer(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
                snippet = text[max(0, m.start() - 40):m.end() + 40]
                context_dependent_flagged.append({"word": word, "count": count,
                                                   "snippet": snippet.strip()})
            break  # flag once per word, not per occurrence

    return {
        "absolute_violations": absolute_violations,
        "importance_framing_violations": importance_framing,
        "context_dependent_flagged": context_dependent_flagged,
        "total_violations": (
            len(absolute_violations) + len(importance_framing)
            + len(context_dependent_flagged)
        ),
    }


# ── Operation 20: Citation integration quality ───────────────────────────────

_CITATION_RE = re.compile(
    r"\((?:[A-Z][a-z]+(?:\s+et\s+al\.?)?(?:,?\s*\d{4})?|"
    r"\d{4})\)|"
    r"\[[A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\]",
    re.IGNORECASE,
)
_EVAL_WORDS_RE = re.compile(
    r"\b(because|relevant|applicable|since this|matters here|"
    r"which is relevant|directly|supports|contradicts)\b",
    re.IGNORECASE,
)


def audit_citation_integration(text: str) -> dict:
    citations = list(_CITATION_RE.finditer(text))
    total = len(citations)
    evaluated = 0
    for m in citations:
        # check within 50 chars after citation for evaluation language
        snippet = text[m.end():m.end() + 150]
        if _EVAL_WORDS_RE.search(snippet):
            evaluated += 1
    pct_evaluated = evaluated / max(total, 1)
    return {
        "total_citations": total,
        "evaluated_citations": evaluated,
        "pct_evaluated": pct_evaluated,
    }


# ── Operation 1: Domain classifier (via local heuristics; Stage 1 fast pass) ─

_DOMAIN_SIGNALS: dict[str, list[str]] = {
    "math": ["theorem", "proof", "lemma", "corollary", "proposition", "conjecture",
             "algebra", "topology", "manifold", "eigenvalue", "polynomial"],
    "cs": ["algorithm", "dataset", "neural network", "machine learning", "lstm",
           "catboost", "model accuracy", "training", "inference", "github",
           "hyperparameter", "benchmark", "rmse", "f1 score", "precision",
           "recall", "epoch", "batch size"],
    "economics": ["gdp", "regression", "instrumental variable", "did", "gravity model",
                  "panel data", "ols", "fixed effects", "elasticity", "inflation",
                  "monetary policy", "fiscal"],
    "management": ["strategy", "competitive advantage", "market entry", "fdi",
                   "greenfield", "joint venture", "merger", "acquisition", "stakeholder",
                   "supply chain", "value chain"],
    "social-science": ["survey", "respondents", "qualitative", "ethnography",
                       "sociological", "norms", "institutions", "social capital",
                       "discourse", "ideology"],
    "humanities": ["rhetoric", "narrative", "discourse analysis", "hermeneutics",
                   "philology", "semiotics", "phenomenology", "epistemology",
                   "postcolonial", "literary"],
    "journalistic": ["reporting", "journalist", "editor", "publication", "byline",
                     "breaking news", "sources said", "according to officials"],
}


def classify_domain(text: str) -> str:
    """Simple frequency-based domain classifier for Stage 1 fast pass."""
    text_lower = text.lower()
    scores: dict[str, int] = Counter()
    for domain, signals in _DOMAIN_SIGNALS.items():
        for signal in signals:
            if signal in text_lower:
                scores[domain] += 1
    if not scores:
        return "general"
    top = scores.most_common(1)[0]
    return top[0] if top[1] >= 2 else "general"


def classify_register(text_or_domain: str) -> str:
    """
    Accepts either a domain name string or raw text.
    If the input matches a known domain, maps it to register.
    Otherwise, classifies domain from text first, then maps to register.
    """
    academic = {"math", "cs", "economics", "management", "social-science",
                "humanities", "linguistics"}
    if text_or_domain in academic:
        return "academic"
    if text_or_domain == "journalistic":
        return "journalistic"
    if text_or_domain == "general":
        return "general"
    # Input is raw text — auto-detect domain first
    domain = classify_domain(text_or_domain)
    if domain in academic:
        return "academic"
    if domain == "journalistic":
        return "journalistic"
    return "general"


# ── Humanizer pattern scanner (P1–P30 + P31–P43) ─────────────────────────────

_P1_INFLATION_RE = re.compile(
    r"\b(stands as|serves as|testament to|vital|pivotal|key role|underscores|"
    r"highlights|reflects broader|setting the stage for|marks? a shift|"
    r"evolving landscape|indelible mark|key turning point)\b",
    re.IGNORECASE,
)

_P3_ING_ENDINGS_RE = re.compile(
    r"\b(highlighting|underscoring|emphasizing|ensuring|reflecting|symbolizing|"
    r"contributing to|cultivating|fostering|encompassing|showcasing)\b",
    re.IGNORECASE,
)

_P4_PROMO_RE = re.compile(
    r"\b(vibrant|nestled|breathtaking|groundbreaking|renowned|stunning|must-visit|"
    r"boasts a|in the heart of|natural beauty)\b",
    re.IGNORECASE,
)

_P5_VAGUE_RE = re.compile(
    r"\b(industry reports|observers have (cited|noted)|experts argue|"
    r"some critics argue|several sources|researchers say|studies suggest)\b",
    re.IGNORECASE,
)

_P6_FORMULAIC_RE = re.compile(
    r"\b(despite (its|these|the)|challenges and legacy|future outlook|"
    r"continues to (thrive|face challenges))\b",
    re.IGNORECASE,
)

_P8_COPULA_RE = re.compile(
    r"\b(serves as|stands as|marks a|represents a|boasts|features|offers a)\b",
    re.IGNORECASE,
)

_P9_NEG_PARALLEL_RE = re.compile(
    r"\b(not only .{1,60} but also|it'?s not just .{1,60} it'?s|"
    r"not merely .{1,60} but)\b",
    re.IGNORECASE,
)

_P13_EMDASH_RE = re.compile(r"—")
_P14_BOLDFACE_RE = re.compile(r"\*\*[^*]+\*\*")
_P16_TITLECASE_RE = re.compile(r"^#{1,3}\s+([A-Z][a-z]+ ){2,}", re.MULTILINE)
_P17_EMOJI_RE = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]"
)
_P18_CURLY_RE = re.compile(r"[\u201c\u201d\u2018\u2019]")
_P19_CHATBOT_RE = re.compile(
    r"\b(i hope this helps|of course!|certainly!|you'?re absolutely right|"
    r"great question!|here is a|let me know if)\b",
    re.IGNORECASE,
)
_P20_CUTOFF_RE = re.compile(
    r"\b(as of (my|the) (latest|last|current)|up to my (last|latest) training|"
    r"while specific details are (limited|scarce)|in recent years|recently|"
    r"in the modern era|contemporary)\b",
    re.IGNORECASE,
)
_P22_FILLER_RE = re.compile(
    r"\b(in order to|due to the fact that|at this point in time|in the event that|"
    r"has the ability to|it is important to note that|it is worth noting that|"
    r"it should be mentioned that|one might argue that|needless to say)\b",
    re.IGNORECASE,
)
_P23_HEDGING_RE = re.compile(
    r"\b(could potentially possibly|might possibly|may potentially|"
    r"could potentially be argued)\b",
    re.IGNORECASE,
)
_P24_GENERIC_END_RE = re.compile(
    r"\b(the future looks bright|exciting times lie ahead|"
    r"major step in the right direction|journey toward excellence)\b",
    re.IGNORECASE,
)
_P27_SENT_START_RE = re.compile(r"(?m)^(The |This |These |That |Those )", re.IGNORECASE)
_P28_INFLATE_RE = re.compile(
    r"\b(leverage|utilize|facilitate|implement|demonstrate|indicate|"
    r"commence|terminate|endeavor|ascertain)\b",
    re.IGNORECASE,
)


def scan_humanizer_patterns(text: str) -> dict:
    """Count occurrences of all P1–P30 patterns."""
    return {
        "P1_significance_inflation": len(_P1_INFLATION_RE.findall(text)),
        "P3_ing_endings": len(_P3_ING_ENDINGS_RE.findall(text)),
        "P4_promotional": len(_P4_PROMO_RE.findall(text)),
        "P5_vague_attribution": len(_P5_VAGUE_RE.findall(text)),
        "P6_formulaic": len(_P6_FORMULAIC_RE.findall(text)),
        "P8_copula_avoidance": len(_P8_COPULA_RE.findall(text)),
        "P9_negative_parallelism": len(_P9_NEG_PARALLEL_RE.findall(text)),
        "P10_triplets": count_triplets(text)["total"],
        "P13_em_dashes": len(_P13_EMDASH_RE.findall(text)),
        "P14_boldface": len(_P14_BOLDFACE_RE.findall(text)),
        "P16_title_case_headings": len(_P16_TITLECASE_RE.findall(text)),
        "P17_emojis": len(_P17_EMOJI_RE.findall(text)),
        "P18_curly_quotes": len(_P18_CURLY_RE.findall(text)),
        "P19_chatbot_artifacts": len(_P19_CHATBOT_RE.findall(text)),
        "P20_cutoff_disclaimers": len(_P20_CUTOFF_RE.findall(text)),
        "P22_filler_phrases": len(_P22_FILLER_RE.findall(text)),
        "P23_excessive_hedging": len(_P23_HEDGING_RE.findall(text)),
        "P24_generic_endings": len(_P24_GENERIC_END_RE.findall(text)),
        "P27_sentence_starter_monotony": len(_P27_SENT_START_RE.findall(text)),
        "P28_register_inflation": len(_P28_INFLATE_RE.findall(text)),
        "P9_announcement_openers": count_announcement_openers(text),
        "P9_announcement_openers_hard": count_announcement_openers(text),
        "P24_para_ending_generalizations": count_para_ending_generalizations(text),
        "P5_attributive_passives": count_attributive_passives(text),
        "P7_genuinely_adj": count_genuinely_adj(text),
    }


# ── Main Analyzer class ──────────────────────────────────────────────────────

class Analyzer:
    """
    Stage 1: Analysis.
    Runs all 20 operations and returns a comprehensive report dict.
    """

    def transform(self, text: str) -> str:
        """Analyzer is read-only; returns text unchanged."""
        return text

    def score(self, text: str) -> dict:
        """Run all 20 Stage 1 operations and return full analysis report."""
        logger.info(f"Stage 1 analysis starting | input_words={_word_count(text)}")
        import time
        t0 = time.time()

        # Op 1: Domain + register
        domain = classify_domain(text)
        register = classify_register(domain)

        # Op 2: Baseline perplexity
        perplexity = compute_perplexity(text)

        # Op 3: Sentence burstiness
        sentence_cv = compute_sentence_cv(text)

        # Op 4: Pattern scan P1–P30
        patterns = scan_humanizer_patterns(text)

        # Op 5: Paragraph burstiness
        para_cv = compute_para_cv(text)

        # Op 6: Transition monotony
        transitions = compute_transition_monotony(text)

        # Op 7: Announcement opener count
        announcement_count = count_announcement_openers(text)

        # Op 8: Triplet count
        triplets = count_triplets(text)

        # Op 9: Para-ending generalization count
        para_ending_gen = count_para_ending_generalizations(text)

        # Op 10: Attributive passive count
        attributive_passives = count_attributive_passives(text)

        # Op 11: "genuinely [adj]" count
        genuinely_adj = count_genuinely_adj(text)

        # Op 12: But:However ratio
        but_however = compute_but_however_ratio(text)

        # Op 13: Connector density
        connector_density = compute_connector_density(text)

        # Op 14: Modal hedging on results
        modal_hedging = count_modal_hedging_on_results(text)

        # Op 15: Standalone definition count
        standalone_defs = count_standalone_definitions(text)

        # Op 16: Section CV
        section_cv = compute_section_cv(text)

        # Op 17: Key term repetition audit
        key_terms = audit_key_term_repetition(text)

        # Op 18: Also frequency
        also_freq = compute_also_frequency(text)

        # Op 19: P7 context-aware scan
        p7_scan = scan_p7_context_aware(text, domain)

        # Op 20: Citation integration quality
        citations = audit_citation_integration(text)

        elapsed = time.time() - t0
        report = {
            "domain": domain,
            "register": register,
            "word_count": _word_count(text),
            "perplexity": perplexity,
            "sentence_cv": sentence_cv,
            "para_cv": para_cv,
            "section_cv": section_cv,
            "patterns": patterns,
            "transition_monotony": transitions,
            "announcement_openers": announcement_count,
            "triplets": triplets,
            "para_ending_generalizations": para_ending_gen,
            "attributive_passives": attributive_passives,
            "genuinely_adj": genuinely_adj,
            "but_however": but_however,
            "connector_density": connector_density,
            "modal_hedging_on_results": modal_hedging,
            "standalone_definitions": standalone_defs,
            "key_terms": key_terms,
            "also_frequency": also_freq,
            "p7_violations": p7_scan,
            "citations": citations,
            "elapsed_seconds": elapsed,
        }

        logger.info(
            f"Stage 1 complete | domain={domain} | perplexity={perplexity:.1f} | "
            f"sentence_cv={sentence_cv:.3f} | para_cv={para_cv:.3f} | "
            f"elapsed={elapsed:.2f}s"
        )
        return report
