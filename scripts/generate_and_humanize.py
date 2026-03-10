#!/usr/bin/env python3
"""
scripts/generate_and_humanize.py — CLI Entry Point

Supports two operating modes:
  1. Generation mode: topic → Phase 0 (sources + text) → Stages 1–5 → .txt + .docx + score report
  2. Humanization mode: existing text → Stages 1–5 → .txt + .docx + score report

Usage examples:
  # Generation mode (Russian coursework on economics):
  python scripts/generate_and_humanize.py \\
      --stream coursework \\
      --topic "Влияние санкций на российские предприятия малого бизнеса" \\
      --domain economics \\
      --language ru \\
      --level bachelor \\
      --verbose

  # Humanization mode (existing text):
  python scripts/generate_and_humanize.py \\
      --input my_ai_text.txt \\
      --domain cs \\
      --language en \\
      --verbose

  # With additional sources:
  python scripts/generate_and_humanize.py \\
      --stream vkr \\
      --topic "Machine learning in healthcare" \\
      --domain it_cs \\
      --language en \\
      --sources "Topol E.J. High-performance medicine. 2019." "LeCun Y. Deep learning. 2015."
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime


# Make sure the repo root is on the path
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def slugify(text: str, max_len: int = 40) -> str:
    """Create a filesystem-safe slug from a topic string."""
    import re
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:max_len].strip("_")


def create_output_dir(topic: str) -> Path:
    """Create a timestamped output directory for this run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(topic)
    dir_name = f"{timestamp}_{slug}"
    output_dir = _REPO_ROOT / "outputs" / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def print_generation_table(params, result) -> None:
    """Print a Rich generation parameters table."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Phase 0 — Generation Parameters", show_header=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Stream", params.stream_id)
        table.add_row("Topic", params.topic[:60] + ("..." if len(params.topic) > 60 else ""))
        table.add_row("Domain", params.domain)
        table.add_row("Language", params.language)
        table.add_row("Level", params.level)
        table.add_row("Research type", params.research_type)
        if params.university:
            table.add_row("University", params.university)
        table.add_row("Pipeline domain", result.pipeline_domain)
        table.add_row("Pipeline register", result.pipeline_register)
        table.add_row("Sections generated", str(result.section_count))
        table.add_row(
            "Structural check",
            "[green]PASSED[/green]" if result.structural_check_passed else "[red]FAILED[/red]"
        )
        table.add_row("Words generated", str(len(result.text.split())))

        if result.source_list:
            src_score = result.source_list.score()
            table.add_row("Sources total", str(src_score["total"]))
            table.add_row(
                "Sources verified",
                f"{src_score['verified_by_api']}/{src_score['total']}"
            )
            if src_score["needs_verification"] > 0:
                table.add_row(
                    "Needs verification",
                    f"[yellow]{src_score['needs_verification']} sources[/yellow]"
                )

        console.print(table)

    except ImportError:
        # Fallback plain text
        print("\n=== Phase 0: Generation Parameters ===")
        print(f"  Stream:    {params.stream_id}")
        print(f"  Topic:     {params.topic[:60]}")
        print(f"  Domain:    {params.domain}")
        print(f"  Language:  {params.language}")
        print(f"  Register:  {result.pipeline_register}")
        print(f"  Words:     {len(result.text.split())}")
        print(f"  Struct. check: {'PASSED' if result.structural_check_passed else 'FAILED'}")


def save_outputs(
    output_dir: Path,
    source_list,
    generated_text: str | None,
    output_text: str,
    score_report: dict,
    register: str,
    topic: str,
    skip_docx: bool,
    config: dict,
) -> dict:
    """Save all output files and return a dict of file paths."""
    paths = {}

    # 01: Sources
    if source_list:
        sources_path = output_dir / "01_sources.json"
        sources_path.write_text(source_list.as_json(), encoding="utf-8")
        paths["sources_json"] = str(sources_path)

    # 02: Generated text (Phase 0 output)
    if generated_text:
        gen_path = output_dir / "02_generated.txt"
        gen_path.write_text(generated_text, encoding="utf-8")
        paths["generated_txt"] = str(gen_path)

    # 06: Final humanized text
    final_path = output_dir / "06_humanized.txt"
    final_path.write_text(output_text, encoding="utf-8")
    paths["humanized_txt"] = str(final_path)

    # Score report JSON
    score_json_path = output_dir / "score_report.json"
    score_json_path.write_text(
        json.dumps(score_report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    paths["score_json"] = str(score_json_path)

    # Score report TXT (plain text summary)
    score_txt_path = output_dir / "score_report.txt"
    _write_score_txt(score_txt_path, score_report)
    paths["score_txt"] = str(score_txt_path)

    # Word document
    if not skip_docx:
        try:
            from pipeline.formatter import export_to_docx

            docx_path = output_dir / "result.docx"
            export_to_docx(
                text=output_text,
                register=register,
                output_path=docx_path,
                config=config,
                title=topic if topic else None,
            )
            paths["docx"] = str(docx_path)
        except ImportError as e:
            print(f"Warning: Word export skipped — {e}")
        except Exception as e:
            print(f"Warning: Word export failed — {e}")

    return paths


def _write_score_txt(path: Path, score_report: dict) -> None:
    """Write a human-readable score report to a text file."""
    lines = ["=== AI Anti-anti Plag — Score Report ===\n"]

    # Generation section
    if "generation" in score_report:
        gen = score_report["generation"]
        lines.append("[ Phase 0: Generation ]")
        lines.append(f"  Stream:           {gen.get('stream_id')}")
        lines.append(f"  Domain:           {gen.get('domain')}")
        lines.append(f"  Language:         {gen.get('language')}")
        lines.append(f"  Register:         {gen.get('pipeline_register')}")
        lines.append(f"  Words generated:  {gen.get('word_count_generated')}")
        lines.append(f"  Struct. check:    {'PASSED' if gen.get('structural_check_passed') else 'FAILED'}")
        if gen.get("structural_warnings"):
            for w in gen["structural_warnings"]:
                lines.append(f"    WARNING: {w}")
        lines.append("")

    # Sources section
    if "sources" in score_report and score_report["sources"]:
        src = score_report["sources"]
        lines.append("[ Sources ]")
        lines.append(f"  Total:            {src.get('total')}")
        lines.append(f"  Verified by API:  {src.get('verified_by_api')}")
        lines.append(f"  Needs verify:     {src.get('needs_verification')}")
        lines.append(f"  GOST compliant:   {src.get('gost_compliant')}")
        lines.append(f"  Min sources met:  {src.get('min_sources_met')}")
        lines.append("")

    # Pipeline metrics
    lines.append("[ Pipeline Metrics ]")
    metrics = [
        ("sentence_cv", 0.45, "≥ 0.45"),
        ("para_cv", 0.50, "≥ 0.50"),
        ("section_cv", 0.30, "≥ 0.30"),
        ("pattern_elimination_rate", 0.85, "≥ 0.85"),
        ("length_reduction_ratio", None, "≤ 0.90"),
        ("but_however_ratio", 2.0, "≥ 2:1"),
        ("announcement_openers", None, "= 0"),
        ("triplets", None, "= 0"),
    ]
    for key, threshold, target in metrics:
        val = score_report.get(key)
        if val is None:
            val = "N/A"
        if isinstance(val, float):
            lines.append(f"  {key:<30} {val:.3f}  (target {target})")
        else:
            lines.append(f"  {key:<30} {val}  (target {target})")

    if score_report.get("perplexity_note"):
        lines.append(f"  perplexity:  {score_report['perplexity_note']}")

    lines.append(f"\n  Words in:  {score_report.get('_word_count_in')}")
    lines.append(f"  Words out: {score_report.get('_word_count_out')}")
    lines.append(f"  Elapsed:   {score_report.get('_elapsed_seconds', 0):.1f}s")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI Anti-anti Plag — Generate and Humanize Academic Text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stream", choices=[
        "vkr", "coursework", "research", "abstract_paper",
        "text", "essay", "composition"
    ], help="Stream type for Generation mode")
    mode.add_argument("--input", "-i", type=str, help="Path to input text file (Humanization mode)")

    # Generation params
    parser.add_argument("--topic", type=str, help="Topic for Generation mode")
    parser.add_argument("--domain", type=str, default="general", choices=[
        "it_cs", "law", "psychology", "economics", "humanities", "media", "general"
    ])
    parser.add_argument("--language", type=str, default="ru", choices=["ru", "en"])
    parser.add_argument("--level", type=str, default="bachelor",
                        choices=["bachelor", "master", "specialist", "postgraduate"])
    parser.add_argument("--research-type", type=str, default="theoretical",
                        dest="research_type",
                        choices=["theoretical", "empirical", "applied"])
    parser.add_argument("--university", type=str, default=None,
                        help="University name (for title page)")
    parser.add_argument("--word-count", type=int, default=None, dest="word_count",
                        help="Target word count (overrides stream default)")
    parser.add_argument("--sources", type=str, nargs="*", default=[],
                        help="Additional sources to include (formatted strings)")

    # Humanization / output params
    parser.add_argument("--output-dir", type=str, default=None, dest="output_dir",
                        help="Output directory (default: outputs/[timestamp]_[slug]/)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--detector-probes", action="store_true", dest="detector_probes",
                        help="Call GPTZero/Copyleaks APIs (optional, requires API keys)")
    parser.add_argument("--generate-only", action="store_true", dest="generate_only",
                        help="Run only Phase 0 (no humanization Stages 1–5)")
    parser.add_argument("--skip-docx", action="store_true", dest="skip_docx",
                        help="Skip Word (.docx) output")
    parser.add_argument("--validate-sources", action="store_true", dest="validate_sources",
                        help="Enable Semantic Scholar API validation for sources")

    args = parser.parse_args()

    # Validate arguments
    if args.stream and not args.topic:
        print("Error: --topic is required when using --stream (Generation mode)")
        return 1

    if not args.stream and not args.input:
        print("Error: specify either --stream (Generation mode) or --input (Humanization mode)")
        return 1

    # Load config
    from pipeline import load_config
    config = load_config()

    # Override Semantic Scholar validation flag if requested
    if args.validate_sources:
        config.setdefault("source_finder", {})["validate_via_semantic_scholar"] = True

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        topic = args.topic or (Path(args.input).stem if args.input else "text")
        output_dir = create_output_dir(topic)

    print(f"\nOutput directory: {output_dir}")

    # ── Humanization mode ──────────────────────────────────────────────────
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: input file not found: {input_path}")
            return 1

        input_text = input_path.read_text(encoding="utf-8")
        print(f"Input: {input_path} ({len(input_text.split())} words)")

        from pipeline import Pipeline

        pipe = Pipeline()
        pipe._current_language = args.language

        print("Running Stages 1–5...")
        t0 = time.time()
        output_text, score_report = pipe.run(
            text=input_text,
            verbose=args.verbose,
            run_detector_probes=args.detector_probes,
        )

        register = score_report.get("register", "general")
        paths = save_outputs(
            output_dir=output_dir,
            source_list=None,
            generated_text=None,
            output_text=output_text,
            score_report=score_report,
            register=register,
            topic=input_path.stem,
            skip_docx=args.skip_docx,
            config=config,
        )

        elapsed = time.time() - t0
        print(f"\nComplete in {elapsed:.1f}s")
        print(f"Output text: {paths.get('humanized_txt')}")
        if "docx" in paths:
            print(f"Word file:   {paths['docx']}")
        print(f"Score report: {paths.get('score_txt')}")
        return 0

    # ── Generation mode ────────────────────────────────────────────────────
    from pipeline.generator import AcademicGenerator, GenerationParams
    from pipeline import Pipeline

    params = GenerationParams(
        stream_id=args.stream,
        topic=args.topic,
        language=args.language,
        domain=args.domain,
        level=args.level,
        research_type=args.research_type,
        university=args.university,
        word_count=args.word_count,
        additional_sources=args.sources or [],
    )

    print(f"\n[Phase 0] Generating {args.stream} on: {args.topic[:60]}")
    print(f"  Domain: {args.domain} | Language: {args.language} | Level: {args.level}")

    generator = AcademicGenerator(config)
    t0 = time.time()
    result = generator.generate(params)

    print_generation_table(params, result)

    # Save generated text
    gen_path = output_dir / "02_generated.txt"
    gen_path.write_text(result.text, encoding="utf-8")

    # Save sources JSON
    if result.source_list:
        src_path = output_dir / "01_sources.json"
        src_path.write_text(result.source_list.as_json(), encoding="utf-8")
        print(f"Sources: {src_path} ({len(result.source_list.sources)} sources)")

    if args.generate_only:
        elapsed = time.time() - t0
        print(f"\nGeneration complete in {elapsed:.1f}s. Output: {gen_path}")
        return 0

    # ── Stages 1–5 ────────────────────────────────────────────────────────
    print("\n[Stages 1–5] Humanizing...")
    pipe = Pipeline()
    output_text, score_report = pipe.run_from_params(
        params=params,
        verbose=args.verbose,
        run_detector_probes=args.detector_probes,
    )

    # Merge generation metadata (already added by run_from_params)
    paths = save_outputs(
        output_dir=output_dir,
        source_list=result.source_list,
        generated_text=result.text,
        output_text=output_text,
        score_report=score_report,
        register=result.pipeline_register,
        topic=args.topic,
        skip_docx=args.skip_docx,
        config=config,
    )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")
    print(f"Humanized text: {paths.get('humanized_txt')}")
    if "docx" in paths:
        print(f"Word file:      {paths['docx']}")
    print(f"Score report:   {paths.get('score_txt')}")
    print(f"All outputs:    {output_dir}/")

    # Print warnings if sources need verification
    if result.source_list:
        src_score = result.source_list.score()
        if src_score.get("needs_verification"):
            print(
                f"\nNOTE: {src_score['needs_verification']} sources need verification "
                f"(see 01_sources.json for details)"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
