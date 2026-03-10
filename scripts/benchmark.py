#!/usr/bin/env python3
"""
Benchmark script: runs the full pipeline on all fixture texts and prints a score table.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --verbose
    python scripts/benchmark.py --fixture fixture_01_economics_academic.txt
    python scripts/benchmark.py --detector-probes   # calls GPTZero/Copyleaks if configured
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import box

# ── Pipeline imports ───────────────────────────────────────────────────────────
from pipeline.analyzer import Analyzer
from pipeline.structural_rewriter import StructuralRewriter
from pipeline.lexical_enricher import LexicalEnricher
from pipeline.discourse_shaper import DiscourseShaper
from pipeline.scorer import Scorer

FIXTURES_DIR = ROOT / "tests" / "fixtures"
CONSOLE = Console()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _pass_indicator(passed: bool) -> str:
    return "[green]✓[/green]" if passed else "[red]✗[/red]"


def _fmt(value: object, decimals: int = 2) -> str:
    if isinstance(value, float):
        return f"{value:.{decimals}f}"
    return str(value)


def run_pipeline(
    text: str,
    domain: str,
    register: str,
    verbose: bool = False,
    run_detector_probes: bool = False,
) -> tuple[str, dict]:
    """Run all 5 stages and return (output_text, score_dict)."""

    analyzer = Analyzer()
    structural_rewriter = StructuralRewriter()
    lexical_enricher = LexicalEnricher()
    discourse_shaper = DiscourseShaper()
    scorer = Scorer()

    t0 = time.time()

    # Stage 1: Analysis
    logger.info("Stage 1: Analysis")
    analysis_report = analyzer.score(text)
    if verbose:
        CONSOLE.print("\n[bold]Stage 1 — Analysis Report[/bold]")
        for k, v in analysis_report.items():
            CONSOLE.print(f"  {k}: {v}")

    # Use classifier output if available
    detected_domain = analysis_report.get("domain", domain)
    detected_register = analysis_report.get("register", register)
    if detected_domain != "general":
        domain = detected_domain
    if detected_register != "general":
        register = detected_register
    logger.info(f"Domain: {domain} | Register: {register}")

    # Stage 2: Structural Rewrite
    logger.info("Stage 2: Structural Rewrite")
    structural_score_before = structural_rewriter.score(text)
    text_s2 = structural_rewriter.transform(
        text, domain=domain, register=register, analysis_report=analysis_report
    )
    if verbose:
        CONSOLE.print(f"\n[bold]Stage 2 complete[/bold] — words: {len(text_s2.split())}")

    # Stage 3: Lexical Enrichment
    logger.info("Stage 3: Lexical Enrichment")
    text_s3 = lexical_enricher.transform(
        text_s2, domain=domain, register=register, analysis_report=analysis_report
    )
    if verbose:
        CONSOLE.print(f"\n[bold]Stage 3 complete[/bold] — words: {len(text_s3.split())}")

    # Stage 4: Discourse Shaping
    logger.info("Stage 4: Discourse Shaping")
    text_s4 = discourse_shaper.transform(
        text_s3,
        domain=domain,
        register=register,
        analysis_report=analysis_report,
        structural_score=structural_score_before,
    )
    if verbose:
        CONSOLE.print(f"\n[bold]Stage 4 complete[/bold] — words: {len(text_s4.split())}")

    # Stage 5: Scoring
    logger.info("Stage 5: Scoring")
    final_score = scorer.score(
        input_text=text,
        output_text=text_s4,
        domain=domain,
        register=register,
        run_detector_probes=run_detector_probes,
    )

    elapsed = time.time() - t0
    final_score["_elapsed_seconds"] = elapsed
    final_score["_word_count_in"] = len(text.split())
    final_score["_word_count_out"] = len(text_s4.split())

    return text_s4, final_score


def print_score_table(fixture_name: str, score: dict) -> None:
    """Render a Rich score table for a single fixture run."""

    table = Table(
        title=f"Score Report — {fixture_name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Pass", justify="center")

    # Define metric display rows
    rows = [
        # (display_name, score_key, value_key, target_str)
        ("Sentence CV", "sentence_cv", "cv", "≥ 0.45"),
        ("Paragraph CV", "para_cv", "cv", "≥ 0.50"),
        ("Section CV", "section_cv", "cv", "≥ 0.30"),
        ("Length reduction ratio", "length_reduction", "ratio", "≤ 0.90"),
        ("Perplexity lift", "perplexity_lift", "ratio", "≥ 1.5×"),
        ("Announcement openers", "announcement_openers", "count", "= 0"),
        ("Triplets", "triplets", "total", "= 0"),
        ("Para-ending generalizations", "para_ending_generalizations", "count", "= 0"),
        ("Attributive passives", "attributive_passives", "count", "= 0"),
        ("But:However ratio", "but_however", "ratio", "≥ 2.0"),
        ("Modal hedging on results", "modal_hedging_on_results", "count", "= 0"),
        ("Standalone definitions", "standalone_definitions", "count", "= 0"),
        ("Also frequency (per page)", "also_frequency", "per_page", "≥ 0.08"),
        ("P7 absolute violations", "p7_violations", "absolute_violations", "= 0"),
        ("Pattern elimination rate", "pattern_elimination", "rate", "≥ 0.85"),
        ("Coherence score", "coherence", "score", "≥ 0.80"),
    ]

    passes = 0
    fails = 0

    for display_name, score_key, value_key, target_str in rows:
        metric = score.get(score_key, {})
        if not isinstance(metric, dict):
            continue
        value = metric.get(value_key)
        passed = metric.get("pass")
        if value is None:
            continue

        value_str = _fmt(value)
        pass_str = _pass_indicator(passed) if passed is not None else "—"

        table.add_row(display_name, value_str, target_str, pass_str)

        if passed is True:
            passes += 1
        elif passed is False:
            fails += 1

    # Optional: detector probes
    if "detector_probes" in score:
        probes = score["detector_probes"]
        for detector_name, probe_data in probes.items():
            if isinstance(probe_data, dict):
                ai_prob = probe_data.get("ai_probability")
                passed = probe_data.get("pass")
                if ai_prob is not None:
                    table.add_row(
                        f"  {detector_name} AI prob",
                        f"{ai_prob:.1%}",
                        "< 20%",
                        _pass_indicator(passed) if passed is not None else "—",
                    )
                    if passed is True:
                        passes += 1
                    elif passed is False:
                        fails += 1

    CONSOLE.print(table)

    # Summary line
    total = passes + fails
    color = "green" if fails == 0 else ("yellow" if fails <= 2 else "red")
    CONSOLE.print(
        f"  [{color}]{passes}/{total} metrics passing[/{color}] | "
        f"input {score.get('_word_count_in', '?')}w → "
        f"output {score.get('_word_count_out', '?')}w | "
        f"elapsed {score.get('_elapsed_seconds', 0):.1f}s\n"
    )


def print_summary_table(results: list[tuple[str, dict]]) -> None:
    """Print a one-row-per-fixture summary across all runs."""
    if len(results) <= 1:
        return

    table = Table(
        title="Benchmark Summary",
        box=box.SIMPLE_HEAVY,
        header_style="bold white",
    )
    table.add_column("Fixture", style="cyan")
    table.add_column("Sent CV", justify="right")
    table.add_column("Para CV", justify="right")
    table.add_column("Len ratio", justify="right")
    table.add_column("Triplets", justify="right")
    table.add_column("But:Hvr", justify="right")
    table.add_column("Modal R", justify="right")
    table.add_column("Announce", justify="right")
    table.add_column("Elapsed", justify="right")

    for fixture_name, score in results:
        row = [
            fixture_name,
            _fmt(score.get("sentence_cv", {}).get("cv", "—")),
            _fmt(score.get("para_cv", {}).get("cv", "—")),
            _fmt(score.get("length_reduction", {}).get("ratio", "—")),
            str(score.get("triplets", {}).get("total", "—")),
            _fmt(score.get("but_however", {}).get("ratio", "—")),
            str(score.get("modal_hedging_on_results", {}).get("count", "—")),
            str(score.get("announcement_openers", {}).get("count", "—")),
            f"{score.get('_elapsed_seconds', 0):.1f}s",
        ]
        table.add_row(*row)

    CONSOLE.print(table)


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full humanization pipeline on fixture texts and print score tables."
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Run only this fixture filename (e.g. fixture_01_economics_academic.txt). "
             "Default: run all fixtures.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print per-stage word counts and analysis reports.",
    )
    parser.add_argument(
        "--detector-probes",
        action="store_true",
        default=False,
        help="Call detector APIs (GPTZero, Copyleaks) if configured in .env.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="If provided, write humanized text files to this directory.",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Override domain detection (economics|cs|management|social-science|math|general).",
    )
    parser.add_argument(
        "--register",
        type=str,
        default=None,
        help="Override register detection (academic|journalistic|general).",
    )
    args = parser.parse_args()

    # Collect fixture files
    if args.fixture:
        fixture_files = [FIXTURES_DIR / args.fixture]
        if not fixture_files[0].exists():
            CONSOLE.print(f"[red]Fixture not found: {fixture_files[0]}[/red]")
            sys.exit(1)
    else:
        fixture_files = sorted(FIXTURES_DIR.glob("*.txt"))
        if not fixture_files:
            CONSOLE.print(f"[red]No fixture files found in {FIXTURES_DIR}[/red]")
            sys.exit(1)

    output_dir: Optional[Path] = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    CONSOLE.print(f"\n[bold white]AI Anti-anti Plag — Benchmark[/bold white]")
    CONSOLE.print(f"Running {len(fixture_files)} fixture(s)\n")

    results: list[tuple[str, dict]] = []

    for fixture_path in fixture_files:
        text = fixture_path.read_text(encoding="utf-8").strip()
        fixture_name = fixture_path.name
        CONSOLE.print(f"[bold yellow]▶ {fixture_name}[/bold yellow] ({len(text.split())} words)")

        domain = args.domain or "general"
        register = args.register or "general"

        try:
            output_text, score = run_pipeline(
                text=text,
                domain=domain,
                register=register,
                verbose=args.verbose,
                run_detector_probes=args.detector_probes,
            )
        except Exception as exc:
            CONSOLE.print(f"[red]Pipeline error on {fixture_name}: {exc}[/red]")
            logger.exception(f"Pipeline error on {fixture_name}")
            continue

        print_score_table(fixture_name, score)
        results.append((fixture_name, score))

        if output_dir:
            out_path = output_dir / f"humanized_{fixture_name}"
            out_path.write_text(output_text, encoding="utf-8")
            CONSOLE.print(f"  → Written to {out_path}\n")

        if args.verbose:
            CONSOLE.rule()
            CONSOLE.print("[dim]HUMANIZED OUTPUT PREVIEW (first 500 chars)[/dim]")
            CONSOLE.print(output_text[:500] + "…")
            CONSOLE.rule()

    if len(results) > 1:
        print_summary_table(results)

    # Exit code: 0 if all metrics pass on all fixtures, 1 otherwise
    all_passed = all(
        all(
            v.get("pass", True)
            for v in score.values()
            if isinstance(v, dict) and "pass" in v
        )
        for _, score in results
    )
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    # Suppress loguru debug output unless --verbose
    import sys as _sys
    logger.remove()
    if "--verbose" in _sys.argv:
        logger.add(_sys.stderr, level="DEBUG")
    else:
        logger.add(_sys.stderr, level="INFO")
    main()
