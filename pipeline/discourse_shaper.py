"""
Stage 4: Voice & Discourse Injection
Two-pass approach: Pass A (14 operations) + Pass B (14-point audit checklist).
Targets: soul requirement, P1–P6, P19–P24, P30 (register-appropriate),
plus new corpus-validated operations from P31–P43.
"""
from __future__ import annotations

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


# ── Pass A: 14 operations ─────────────────────────────────────────────────────

def _build_pass_a_system(
    domain: str,
    register: str,
    human_example: str = "",
    language: str = "en",
) -> str:
    """Build the Pass A system prompt from template, injecting domain/register/example/language."""
    system = _load_prompt("voice_injection")
    system = system.replace("{{DOMAIN}}", domain)
    system = system.replace("{{REGISTER}}", register)
    system = system.replace("{{LANGUAGE}}", language)

    # Inject P30 mode based on register
    cfg = _load_config()
    p30_modes = cfg.get("p30_mode", {})
    p30_mode = p30_modes.get(register, p30_modes.get("academic", "limited"))
    system = system.replace("{{P30_MODE}}", p30_mode)

    # First-person target by domain
    fp_targets = cfg.get("first_person_targets", {})
    fp_target = fp_targets.get(domain, fp_targets.get("general", "moderate"))
    system = system.replace("{{FIRST_PERSON_TARGET}}", fp_target)

    # Inject human example (few-shot reference)
    if human_example:
        header = f"[{domain} — human reference, {len(human_example.split())} words]"
        system = system.replace("{{HUMAN_EXAMPLE_HEADER}}", header)
        system = system.replace("{{HUMAN_EXAMPLE}}", human_example)
    else:
        # Collapse the entire example block cleanly when no example is available
        import re as _re
        system = _re.sub(
            r"\*\*Human writing reference\*\*:.*?Your transformation must produce text.*?\n\n",
            "",
            system,
            flags=_re.DOTALL,
        )
        # Fallback replacements in case regex didn't match
        system = system.replace("{{HUMAN_EXAMPLE_HEADER}}", "")
        system = system.replace("{{HUMAN_EXAMPLE}}", "")

    return system


def _build_pass_a_user(
    text: str,
    analysis_report: Optional[dict] = None,
    structural_score: Optional[dict] = None,
) -> str:
    """Build the Pass A user prompt with analysis context."""
    context_parts = []

    if analysis_report:
        domain = analysis_report.get("domain", "general")
        register = analysis_report.get("register", "general")
        perplexity = analysis_report.get("perplexity", 0)
        sentence_cv = analysis_report.get("sentence_cv", 0)
        para_cv = analysis_report.get("para_cv", 0)
        section_cv = analysis_report.get("section_cv", 0)
        but_however = analysis_report.get("but_however", {}).get("ratio", 0)
        also_freq = analysis_report.get("also_frequency", {}).get("per_page", 0)
        modal_count = analysis_report.get("modal_hedging_on_results", {}).get(
            "count", 0
        )
        standalone_defs = analysis_report.get("standalone_definitions", 0)
        citation_pct = analysis_report.get("citations", {}).get("pct_evaluated", 0)

        context_parts.append(
            f"Analysis metrics:\n"
            f"- Domain: {domain}, Register: {register}\n"
            f"- Perplexity: {perplexity:.1f}\n"
            f"- Sentence CV: {sentence_cv:.3f} (target ≥ 0.45)\n"
            f"- Paragraph CV: {para_cv:.3f} (target ≥ 0.50)\n"
            f"- Section CV: {section_cv:.3f} (target ≥ 0.30)\n"
            f"- But:However ratio: {but_however:.2f} (target ≥ 2:1)\n"
            f"- Also per page: {also_freq:.2f} (target ≥ 0.08)\n"
            f"- Modal hedging on results: {modal_count} (target: 0)\n"
            f"- Standalone definitions: {standalone_defs} (target: 0)\n"
            f"- Citations evaluated: {citation_pct:.1%} (target ≥ 30%)"
        )

    if structural_score:
        triplets = structural_score.get("triplets", {}).get("total", 0)
        context_parts.append(f"\nRemaining triplets after Stage 2: {triplets} (must be 0)")

    context = "\n\n".join(context_parts)

    return (
        f"Apply Pass A voice and discourse injection to the following text.\n\n"
        f"{context}\n\n"
        f"TEXT TO TRANSFORM:\n{text}\n\n"
        f"OUTPUT (transformed text only, no explanation):"
    )


def _build_pass_b_system(domain: str, register: str, language: str = "en") -> str:
    """Build the Pass B audit system prompt."""
    system = _load_prompt("audit")
    system = system.replace("{{DOMAIN}}", domain)
    system = system.replace("{{REGISTER}}", register)
    system = system.replace("{{LANGUAGE}}", language)
    return system


def _build_pass_b_user(text: str, domain: str, register: str, language: str = "en") -> str:
    """Build the Pass B audit user prompt with the 14-point checklist."""
    is_academic = register == "academic"
    is_russian = language == "ru"

    structural_note = (
        "For academic text: check within-section micro-structure only (P26 register restriction). "
        "Do NOT reorder major sections (Введение/Introduction → Literature → Methods → Results → Заключение/Conclusion)."
        if is_academic else
        "For non-academic text: reorder sections if the structure is predictably linear."
    )

    p30_note = (
        "For academic register: apply only epistemic hedging, methodological asides, "
        "and mild evaluative language. Do NOT inject colloquial markers, fragments, "
        "or register drops."
        if is_academic else
        "For journalistic/general register: apply full P30 toolkit — parenthetical asides, "
        "fragments for emphasis, register drops, discourse markers."
    )

    # AC-5: Figurative language gate (Russian academic)
    figurative_note = (
        "SKIP item 4 — figurative language injection. Russian academic text convention: "
        "no metaphors or analogies in VKR/coursework/research."
        if (is_russian and is_academic) else
        "Does each section have at least one concrete analogy or metaphor? "
        "If not, add one. (Skip for math domain — metaphors are not appropriate.)"
    )

    # AC-7: F5/F6 gating
    if is_academic:
        f5_f6_note = "F5/F6: SKIP entirely — academic register, controlled errors not applied."
    elif is_russian:
        f5_f6_note = (
            "F5/F6: Russian text — F5 inapplicable (no apostrophes in Russian). "
            "F6: comma placement variation only (1-2 instances max)."
        )
    else:
        f5_f6_note = (
            "F5: Add 3–5 controlled missing apostrophes on proper noun possessives "
            "(e.g., Tehrans instead of Tehran's). "
            "F6: Add 2–3 minor grammar errors: subject-verb agreement on compound phrases, "
            "comma splices between closely related clauses, or missing article."
        )

    # AC-12: But:However note is language-specific
    connector_ratio_note = (
        "14. Is the Но:Однако ratio at least 2:1? If not, convert 2–3 'Однако' sentences to 'Но'."
        if is_russian else
        "14. Is the But:However ratio at least 2:1? If not, convert 2–3 'However' sentences to 'But'."
    )

    return (
        f"Domain: {domain}. Register: {register}. Language: {language}.\n\n"
        f"PASS B — 14-POINT AUDIT CHECKLIST:\n"
        f"For each item below, check if the issue exists and, if so, fix it.\n\n"
        f"1. Does every paragraph start with a topic sentence and end with a wrap-up? "
        f"Break the pattern in at least one paragraph.\n"
        f"2. Does the same connector appear more than twice per page? Replace excess instances.\n"
        f"3. {structural_note}\n"
        f"4. {figurative_note}\n"
        f"5. Is the output shorter than typical AI output on this topic? "
        f"Cut padding if word count > 90% of input.\n"
        f"6. Are there ANY triplets (X, Y, and Z series), including verb tricolons and "
        f"adverbial tricolons? Zero tolerance. Break every triplet found.\n"
        f"7. Does any passage stay at one abstraction level for 3+ sentences? "
        f"Inject a concrete example or pull back to a general claim.\n"
        f"8. Does the text write with false certainty on estimated or contested claims? "
        f"Add hedging: 'probably'/'вероятно', 'roughly'/'примерно', 'it seems'/'по всей видимости'. "
        f"BUT do NOT add hedging to result sentences with numerical evidence (P32).\n"
        f"9. Is >80% of the text in the same verb tense? Vary 2–3 sentences.\n"
        f"10. Does any sentence announce what is about to be said, flag importance before "
        f"stating content, or describe content as 'worth mentioning'/'следует отметить'? "
        f"Delete and start with content.\n"
        f"11. Does any paragraph end with an abstract generalization from the preceding facts? "
        f"Delete and end on the most specific data point instead.\n"
        f"12. Is importance framed before content, or does content demonstrate its own importance? "
        f"Delete any importance-announcing sentence.\n"
        f"13. Are any empirical results hedged with modal verbs? "
        f"Remove modals from result sentences. Numbers speak; 'may achieve' is redundant when RMSE = 0.096.\n"
        f"{connector_ratio_note}\n\n"
        f"P30 mode: {p30_note}\n\n"
        f"Formatting (F5/F6): {f5_f6_note}\n\n"
        f"TEXT TO AUDIT:\n{text}\n\n"
        f"OUTPUT (audited and corrected text only, no explanation or audit notes):"
    )


# ── DiscourseShaper class ─────────────────────────────────────────────────────

class DiscourseShaper:
    """
    Stage 4: Voice & Discourse Injection.
    Pass A: 14 operations (voice, specificity, rhythm, soul injection).
    Pass B: 14-point audit checklist.
    """

    def transform(
        self,
        text: str,
        domain: str = "general",
        register: str = "general",
        analysis_report: Optional[dict] = None,
        structural_score: Optional[dict] = None,
        language: str = "en",
    ) -> str:
        logger.info(
            f"Stage 4 starting | words={len(text.split())} | "
            f"domain={domain} | register={register} | language={language}"
        )
        t0 = time.time()

        cfg = _load_config()
        temperature = cfg["pipeline"]["rewrite_temperature"]

        # ── Load human example for few-shot reference ─────────────────────
        human_example = ""
        if cfg.get("examples", {}).get("enabled", False):
            try:
                from pipeline.example_loader import ExampleLoader
                loader = ExampleLoader()
                human_example = loader.get_example(domain) or ""
                if human_example:
                    logger.info(
                        f"Stage 4: injected {len(human_example.split())}-word "
                        f"human example for domain={domain}"
                    )
            except Exception as exc:
                logger.warning(
                    f"Stage 4: example loading failed ({exc}); continuing without example"
                )

        # ── Pass A: Voice & Discourse Injection ───────────────────────────
        logger.info("Stage 4 Pass A starting")
        t_a = time.time()
        system_a = _build_pass_a_system(
            domain, register, human_example=human_example, language=language
        )
        user_a = _build_pass_a_user(text, analysis_report, structural_score)
        text_a = _call_claude(system_a, user_a, temperature=temperature)
        logger.info(
            f"Stage 4 Pass A complete | words={len(text_a.split())} | "
            f"elapsed={time.time() - t_a:.2f}s"
        )

        # ── Pass B: Audit ─────────────────────────────────────────────────
        logger.info("Stage 4 Pass B starting")
        t_b = time.time()
        system_b = _build_pass_b_system(domain, register, language=language)
        user_b = _build_pass_b_user(text_a, domain, register, language=language)
        text_b = _call_claude(system_b, user_b, temperature=temperature)
        logger.info(
            f"Stage 4 Pass B complete | words={len(text_b.split())} | "
            f"elapsed={time.time() - t_b:.2f}s"
        )

        elapsed = time.time() - t0
        logger.info(
            f"Stage 4 complete | words={len(text_b.split())} | elapsed={elapsed:.2f}s"
        )
        return text_b

    def score(self, text: str) -> dict:
        """Quick voice/discourse metrics on already-transformed text."""
        from pipeline.analyzer import (
            compute_sentence_cv,
            compute_para_cv,
            compute_but_however_ratio,
            count_triplets,
            count_announcement_openers,
            count_para_ending_generalizations,
            compute_also_frequency,
        )
        return {
            "sentence_cv": compute_sentence_cv(text),
            "para_cv": compute_para_cv(text),
            "but_however": compute_but_however_ratio(text),
            "triplets": count_triplets(text),
            "announcement_openers": count_announcement_openers(text),
            "para_ending_generalizations": count_para_ending_generalizations(text),
            "also_frequency": compute_also_frequency(text),
            "word_count": len(text.split()),
        }
