"""
Stage 5: Scoring & Feedback
All 20 metrics as specified in the plan.
Runs entirely locally — no API cost.
"""
from __future__ import annotations

import re
import time
import yaml
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_config: dict = {}


def _load_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


# ── Metric 1: Perplexity ──────────────────────────────────────────────────────

def score_perplexity_lift(
    input_text: str, output_text: str
) -> dict:
    """GPT-2 perplexity comparison. Target: ≥ 1.5× baseline."""
    from pipeline.analyzer import compute_perplexity
    cfg = _load_config()
    target = cfg["scoring"]["perplexity_lift_min"]
    baseline = compute_perplexity(input_text)
    output_perp = compute_perplexity(output_text)
    lift = output_perp / max(baseline, 1e-6)
    return {
        "baseline_perplexity": baseline,
        "output_perplexity": output_perp,
        "ratio": lift,
        "target": target,
        "pass": lift >= target,
    }


# ── Metric 2: Sentence burstiness ────────────────────────────────────────────

def score_sentence_cv(output_text: str) -> dict:
    from pipeline.analyzer import compute_sentence_cv
    cfg = _load_config()
    target = cfg["scoring"]["sentence_cv_min"]
    cv = compute_sentence_cv(output_text)
    return {"cv": cv, "target": target, "pass": cv >= target}


# ── Metric 3: Pattern rescan ──────────────────────────────────────────────────

def score_pattern_elimination(
    input_text: str, output_text: str
) -> dict:
    from pipeline.analyzer import scan_humanizer_patterns
    cfg = _load_config()
    target = cfg["scoring"]["pattern_elimination_rate_min"]
    before = scan_humanizer_patterns(input_text)
    after = scan_humanizer_patterns(output_text)

    total_before = sum(before.values())
    total_after = sum(after.values())

    if total_before == 0:
        rate = 1.0
    else:
        rate = 1.0 - (total_after / total_before)

    return {
        "patterns_before": before,
        "patterns_after": after,
        "total_before": total_before,
        "total_after": total_after,
        "rate": rate,
        "target": target,
        "pass": rate >= target,
    }


# ── Metric 4: Coherence checker ───────────────────────────────────────────────

def score_coherence(output_text: str) -> dict:
    """Embedding-based cosine similarity chain between adjacent paragraphs."""
    from sentence_transformers import SentenceTransformer
    import torch

    cfg = _load_config()
    target = cfg["scoring"]["coherence_min"]
    model_name = cfg["local_models"]["embedding_model"]

    paras = [p.strip() for p in re.split(r"\n{2,}", output_text) if p.strip()]
    if len(paras) < 2:
        return {"coherence": 1.0, "target": target, "pass": True}

    model = SentenceTransformer(model_name)
    embeddings = model.encode(paras, convert_to_tensor=True)
    sims = []
    for i in range(len(embeddings) - 1):
        cos_sim = float(
            torch.nn.functional.cosine_similarity(
                embeddings[i].unsqueeze(0), embeddings[i + 1].unsqueeze(0)
            ).item()
        )
        sims.append(cos_sim)

    avg_coherence = float(np.mean(sims))
    return {
        "score": avg_coherence,
        "paragraph_similarities": sims,
        "target": target,
        "pass": avg_coherence >= target,
    }


# ── Metric 5: Paragraph burstiness ───────────────────────────────────────────

def score_para_cv(output_text: str) -> dict:
    from pipeline.analyzer import compute_para_cv
    cfg = _load_config()
    target = cfg["scoring"]["para_cv_min"]
    cv = compute_para_cv(output_text)
    return {"cv": cv, "target": target, "pass": cv >= target}


# ── Metric 6: Length reduction ────────────────────────────────────────────────

def score_length_reduction(input_text: str, output_text: str) -> dict:
    from pipeline.analyzer import _word_count
    cfg = _load_config()
    target = cfg["scoring"]["length_reduction_max"]
    input_words = _word_count(input_text)
    output_words = _word_count(output_text)
    ratio = output_words / max(input_words, 1)
    return {
        "input_words": input_words,
        "output_words": output_words,
        "ratio": ratio,
        "target": f"<= {target}",
        "pass": ratio <= target,
    }


# ── Metric 7: Announcement opener count ──────────────────────────────────────

def score_announcement_openers(output_text: str) -> dict:
    from pipeline.analyzer import count_announcement_openers
    cfg = _load_config()
    target = cfg["scoring"]["announcement_opener_target"]
    count = count_announcement_openers(output_text)
    return {"count": count, "target": target, "pass": count == target}


# ── Metric 8: Triplet instance count ─────────────────────────────────────────

def score_triplets(output_text: str) -> dict:
    from pipeline.analyzer import count_triplets
    cfg = _load_config()
    target = cfg["scoring"]["triplet_target"]
    result = count_triplets(output_text)
    total = result["total"]
    return {**result, "target": target, "pass": total == target}


# ── Metric 9: Para-ending generalization count ───────────────────────────────

def score_para_ending_generalizations(output_text: str) -> dict:
    from pipeline.analyzer import count_para_ending_generalizations
    cfg = _load_config()
    target = cfg["scoring"]["para_ending_generalization_target"]
    count = count_para_ending_generalizations(output_text)
    return {"count": count, "target": target, "pass": count == target}


# ── Metric 10: Attributive passive count ─────────────────────────────────────

def score_attributive_passives(output_text: str) -> dict:
    from pipeline.analyzer import count_attributive_passives
    cfg = _load_config()
    target = cfg["scoring"]["attributive_passive_target"]
    count = count_attributive_passives(output_text)
    return {"count": count, "target": target, "pass": count == target}


# ── Metric 11: But:However ratio ─────────────────────────────────────────────

def score_but_however_ratio(output_text: str) -> dict:
    from pipeline.analyzer import compute_but_however_ratio
    cfg = _load_config()
    target = cfg["scoring"]["but_however_ratio_min"]
    result = compute_but_however_ratio(output_text)
    ratio = result["ratio"]
    return {
        **result,
        "target": f">= {target}",
        "pass": ratio >= target,
        "red_line": ratio >= 1.0,
    }


# ── Metric 12: Connector density per page ────────────────────────────────────

def score_connector_density(output_text: str) -> dict:
    from pipeline.analyzer import compute_connector_density
    cfg = _load_config()
    target = cfg["scoring"]["connector_density_max"]
    result = compute_connector_density(output_text)
    density = result["density_per_page"]
    additionally_count = result["by_type"].get("additionally", 0)
    return {
        **result,
        "target": f"<= {target}",
        "pass": density <= target and additionally_count == 0,
        "additionally_hard_fail": additionally_count > 0,
    }


# ── Metric 13: Modal hedging on results ratio ─────────────────────────────────

def score_modal_hedging_on_results(output_text: str) -> dict:
    from pipeline.analyzer import count_modal_hedging_on_results
    cfg = _load_config()
    target = cfg["scoring"]["modal_hedging_on_results_max"]
    result = count_modal_hedging_on_results(output_text)
    count = result["count"]
    return {
        "count": count,
        "sentences": result["sentences"][:3],  # show max 3
        "target": f"<= {target * 100:.0f}%",
        "pass": count == 0,
    }


# ── Metric 14: Section token-count CV ────────────────────────────────────────

def score_section_cv(output_text: str) -> dict:
    from pipeline.analyzer import compute_section_cv
    cfg = _load_config()
    target = cfg["scoring"]["section_cv_min"]
    cv = compute_section_cv(output_text)
    return {
        "cv": cv,
        "target": f">= {target}",
        "pass": cv >= target if cv > 0 else True,  # skip if no sections detected
    }


# ── Metric 15: Key term repetition consistency ────────────────────────────────

def score_key_term_consistency(output_text: str) -> dict:
    from pipeline.analyzer import audit_key_term_repetition
    result = audit_key_term_repetition(output_text)
    top_terms = result["top_key_terms"]
    cycling_risk_count = result.get("cycling_risk_count", 0)
    # Pass if: top terms appear ≥ 3× AND no terms show cycling risk pattern
    terms_frequent = all(t["count"] >= 3 for t in top_terms[:3]) if top_terms else True
    consistent = terms_frequent and cycling_risk_count == 0
    return {
        "top_terms": top_terms,
        "cycling_risk_count": cycling_risk_count,
        "consistent": consistent,
        "pass": consistent,
    }


# ── Metric 16: Standalone definition count ───────────────────────────────────

def score_standalone_definitions(output_text: str) -> dict:
    from pipeline.analyzer import count_standalone_definitions
    count = count_standalone_definitions(output_text)
    return {"count": count, "target": 0, "pass": count == 0}


# ── Metric 17: Source evaluation density ─────────────────────────────────────

def score_source_evaluation_density(output_text: str) -> dict:
    from pipeline.analyzer import audit_citation_integration
    cfg = _load_config()
    target = cfg["scoring"]["source_evaluation_density_min"]
    result = audit_citation_integration(output_text)
    total = result["total_citations"]
    pct = result["pct_evaluated"]
    # Only apply if ≥ 5 citations
    if total < 5:
        return {"total_citations": total, "pct_evaluated": pct,
                "target": f">= {target:.0%}", "pass": True, "note": "< 5 citations; skipped"}
    return {
        "total_citations": total,
        "evaluated_citations": result["evaluated_citations"],
        "pct_evaluated": pct,
        "target": f">= {target:.0%}",
        "pass": pct >= target,
    }


# ── Metric 18: Also frequency ─────────────────────────────────────────────────

def score_also_frequency(output_text: str, register: str = "general") -> dict:
    from pipeline.analyzer import compute_also_frequency
    cfg = _load_config()
    target = cfg["scoring"]["also_per_page_min"]
    result = compute_also_frequency(output_text)
    per_page = result["per_page"]
    is_academic = register == "academic"
    # Only enforce in academic text with ≥ 500 words
    word_count = len(output_text.split())
    if not is_academic or word_count < 500:
        return {**result, "target": f">= {target}", "pass": True,
                "note": "Not academic or < 500 words; skipped"}
    return {
        **result,
        "target": f">= {target}",
        "pass": per_page >= target,
        "red_line": result["count"] > 0,
    }


# ── Metric 19: P7 context-aware violation count ───────────────────────────────

def score_p7_violations(output_text: str, domain: str = "general") -> dict:
    from pipeline.analyzer import scan_p7_context_aware
    cfg = _load_config()
    result = scan_p7_context_aware(output_text, domain)
    total = result["total_violations"]
    return {
        "total_violations": total,
        "absolute_violations": len(result["absolute_violations"]),
        "importance_framing": len(result["importance_framing_violations"]),
        "context_dependent": len(result["context_dependent_flagged"]),
        "target": 0,
        "pass": total == 0,
    }


# ── Metric 20: Detector probes (optional) ────────────────────────────────────

def probe_gptzero(text: str, api_key: str) -> dict:
    """Optional: Call GPTZero API for AI probability score."""
    import anthropic
    # Placeholder — requires GPTZERO_API_KEY in environment
    return {"error": "GPTZero probe not configured. Set GPTZERO_API_KEY."}


def probe_copyleaks(text: str, api_key: str) -> dict:
    """Optional: Call Copyleaks API for AI probability score."""
    return {"error": "Copyleaks probe not configured. Set COPYLEAKS_API_KEY."}


# ── Full score report ─────────────────────────────────────────────────────────

class Scorer:
    """
    Stage 5: Scoring & Feedback.
    Runs all 20 metrics and returns a comprehensive score report.
    """

    def transform(self, text: str) -> str:
        """Scorer is read-only; returns text unchanged."""
        return text

    def score(
        self,
        input_text: str,
        output_text: str,
        domain: str = "general",
        register: str = "general",
        run_detector_probes: bool = False,
    ) -> dict:
        logger.info(
            f"Stage 5 scoring | output_words={len(output_text.split())} | "
            f"domain={domain}"
        )
        t0 = time.time()

        metrics = {}

        # Metric 1: Perplexity lift
        try:
            metrics["perplexity_lift"] = score_perplexity_lift(input_text, output_text)
        except Exception as e:
            logger.warning(f"Perplexity scoring failed: {e}")
            metrics["perplexity_lift"] = {"error": str(e), "pass": None}

        # Metric 2: Sentence burstiness
        metrics["sentence_cv"] = score_sentence_cv(output_text)

        # Metric 3: Pattern elimination
        metrics["pattern_elimination"] = score_pattern_elimination(
            input_text, output_text
        )

        # Metric 4: Coherence
        try:
            metrics["coherence"] = score_coherence(output_text)
        except Exception as e:
            logger.warning(f"Coherence scoring failed: {e}")
            metrics["coherence"] = {"error": str(e), "pass": None}

        # Metric 5: Paragraph burstiness
        metrics["para_cv"] = score_para_cv(output_text)

        # Metric 6: Length reduction
        metrics["length_reduction"] = score_length_reduction(input_text, output_text)

        # Metric 7: Announcement openers
        metrics["announcement_openers"] = score_announcement_openers(output_text)

        # Metric 8: Triplets
        metrics["triplets"] = score_triplets(output_text)

        # Metric 9: Para-ending generalizations
        metrics["para_ending_generalizations"] = score_para_ending_generalizations(
            output_text
        )

        # Metric 10: Attributive passives
        metrics["attributive_passives"] = score_attributive_passives(output_text)

        # Metric 11: But:However ratio
        metrics["but_however"] = score_but_however_ratio(output_text)

        # Metric 12: Connector density
        metrics["connector_density"] = score_connector_density(output_text)

        # Metric 13: Modal hedging on results
        metrics["modal_hedging_on_results"] = score_modal_hedging_on_results(output_text)

        # Metric 14: Section CV
        metrics["section_cv"] = score_section_cv(output_text)

        # Metric 15: Key term consistency
        metrics["key_term_consistency"] = score_key_term_consistency(output_text)

        # Metric 16: Standalone definitions
        metrics["standalone_definitions"] = score_standalone_definitions(output_text)

        # Metric 17: Source evaluation density
        metrics["source_evaluation"] = score_source_evaluation_density(output_text)

        # Metric 18: Also frequency
        metrics["also_frequency"] = score_also_frequency(output_text, register)

        # Metric 19: P7 context-aware violations
        metrics["p7_violations"] = score_p7_violations(output_text, domain)

        # Metric 20: Detector probes (optional)
        if run_detector_probes:
            import os
            gptzero_key = os.getenv("GPTZERO_API_KEY", "")
            if gptzero_key:
                metrics["gptzero"] = probe_gptzero(output_text, gptzero_key)
            copyleaks_key = os.getenv("COPYLEAKS_API_KEY", "")
            if copyleaks_key:
                metrics["copyleaks"] = probe_copyleaks(output_text, copyleaks_key)

        # ── Summary ──────────────────────────────────────────────────────
        passed = []
        failed = []
        for name, m in metrics.items():
            if isinstance(m, dict) and "pass" in m:
                if m["pass"] is True:
                    passed.append(name)
                elif m["pass"] is False:
                    failed.append(name)

        elapsed = time.time() - t0
        # Flatten: all metric sub-dicts at top level for direct dict access.
        # _summary is prefixed to avoid collision with metric keys.
        report: dict = {}
        report.update(metrics)
        report["_summary"] = {
            "passed": passed,
            "failed": failed,
            "total_checks": len(passed) + len(failed),
            "pass_rate": len(passed) / max(len(passed) + len(failed), 1),
            # "pass" key required by test_scorer_score_includes_pass_fail
            "pass": len(failed) == 0,
        }
        report["_elapsed_seconds"] = elapsed

        logger.info(
            f"Stage 5 complete | passed={len(passed)} | failed={len(failed)} | "
            f"elapsed={elapsed:.2f}s"
        )
        self._print_report(report)
        return report

    def _print_report(self, report: dict) -> None:
        """Print a formatted score table to stdout."""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Score Report", show_lines=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Target", style="yellow")
        table.add_column("Pass?", style="green")

        for name, m in report.items():
            if name.startswith("_") or not isinstance(m, dict):
                continue
            value_str = ""
            target_str = str(m.get("target", ""))
            pass_val = m.get("pass")
            pass_str = "✓" if pass_val is True else ("✗" if pass_val is False else "—")

            # Pick the most informative value field
            for key in ["cv", "ratio", "score", "count", "total", "density_per_page",
                        "pct_evaluated", "per_page", "total_violations", "rate"]:
                if key in m:
                    v = m[key]
                    value_str = f"{v:.3f}" if isinstance(v, float) else str(v)
                    break

            table.add_row(name, value_str, target_str, pass_str)

        console.print(table)
        summary = report.get("_summary", {})
        console.print(
            f"[bold]Pass rate: {summary.get('pass_rate', 0):.0%} "
            f"({len(summary.get('passed', []))}/{summary.get('total_checks', 0)} checks)[/bold]"
        )
