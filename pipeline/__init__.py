"""
AI Anti-anti Plag — Pipeline Package
Exposes the Pipeline orchestrator, shared utilities, and data models.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_config: dict = {}


def load_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def load_prompt(name: str) -> str:
    """Load a prompt template from /prompts/<name>.md"""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def chunk_text(
    text: str,
    chunk_size_words: int = 300,
    overlap_sentences: int = 1,
) -> list[str]:
    """
    Split text into overlapping chunks for LLM processing.
    Uses sentence boundaries to avoid mid-sentence cuts.
    """
    import re

    # Split into sentences (simple heuristic)
    sentence_endings = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_endings.split(text.strip())
    if not sentences:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for i, sent in enumerate(sentences):
        word_count = len(sent.split())
        current.append(sent)
        current_words += word_count

        if current_words >= chunk_size_words:
            chunks.append(" ".join(current))
            # Overlap: keep last `overlap_sentences` sentences
            overlap = current[-overlap_sentences:] if overlap_sentences > 0 else []
            current = overlap
            current_words = sum(len(s.split()) for s in current)

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [text]


def call_claude(
    system: str,
    user: str,
    model: str = "claude-sonnet-4-6",
    temperature: float = 0.9,
    max_tokens: int = 4096,
    max_retries: int = 3,
) -> str:
    """
    Call the Claude API with exponential-backoff retry logic.
    Respects config.yaml retry_delay_seconds.
    """
    import anthropic

    cfg = load_config()
    delay = cfg["pipeline"].get("retry_delay_seconds", 2)
    client = anthropic.Anthropic()

    for attempt in range(max_retries):
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
            if attempt < max_retries - 1:
                wait = delay * (2 ** attempt)
                logger.warning(f"Rate limit on attempt {attempt + 1}, retrying in {wait}s")
                time.sleep(wait)
            else:
                logger.error("Rate limit exceeded after all retries")
                raise
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            raise

    return ""


# ── Pipeline orchestrator ─────────────────────────────────────────────────────


class Pipeline:
    """
    Full 5-stage humanization pipeline.

    Usage:
        pipe = Pipeline()
        output_text, score_report = pipe.run(input_text, verbose=True)
    """

    def __init__(self) -> None:
        from pipeline.analyzer import Analyzer
        from pipeline.structural_rewriter import StructuralRewriter
        from pipeline.lexical_enricher import LexicalEnricher
        from pipeline.discourse_shaper import DiscourseShaper
        from pipeline.scorer import Scorer

        self.analyzer = Analyzer()
        self.structural_rewriter = StructuralRewriter()
        self.lexical_enricher = LexicalEnricher()
        self.discourse_shaper = DiscourseShaper()
        self.scorer = Scorer()

    def run(
        self,
        text: str,
        verbose: bool = False,
        domain_override: Optional[str] = None,
        register_override: Optional[str] = None,
        run_detector_probes: bool = False,
    ) -> tuple[str, dict]:
        """
        Run all 5 stages sequentially.

        Returns:
            (output_text, score_report)
        """
        t0 = time.time()

        # Detect language from instance attribute (set by run_from_params)
        language = getattr(self, "_current_language", "en")

        # ── Stage 1: Analysis ─────────────────────────────────────────────
        logger.info("Pipeline Stage 1: Analysis")
        analysis_report = self.analyzer.score(text)

        domain = domain_override or analysis_report.get("domain", "general")
        register = register_override or analysis_report.get("register", "general")

        # Language routing: configure analysis_report flags for downstream stages
        analysis_report["_language"] = language
        if language == "ru":
            analysis_report["_skip_perplexity"] = True   # GPT-2 English-only
            analysis_report["_use_word_cv"] = True       # Word-level CV for Russian

        if verbose:
            logger.info(
                f"  domain={domain} | register={register} | language={language} | "
                f"words={analysis_report.get('word_count', '?')} | "
                f"perplexity={analysis_report.get('perplexity', 0):.1f}"
            )

        # ── Stage 2: Structural Rewrite ───────────────────────────────────
        logger.info("Pipeline Stage 2: Structural Rewrite")
        structural_score = self.structural_rewriter.score(text)
        text_s2 = self.structural_rewriter.transform(
            text,
            domain=domain,
            register=register,
            analysis_report=analysis_report,
            language=language,
        )
        if verbose:
            logger.info(f"  Stage 2 output: {len(text_s2.split())} words")

        # ── Stage 3: Lexical Enrichment ────────────────────────────────────
        logger.info("Pipeline Stage 3: Lexical Enrichment")
        text_s3 = self.lexical_enricher.transform(
            text_s2,
            domain=domain,
            register=register,
            analysis_report=analysis_report,
            language=language,
        )
        if verbose:
            logger.info(f"  Stage 3 output: {len(text_s3.split())} words")

        # ── Stage 4: Discourse Shaping ────────────────────────────────────
        logger.info("Pipeline Stage 4: Discourse Shaping")
        text_s4 = self.discourse_shaper.transform(
            text_s3,
            domain=domain,
            register=register,
            analysis_report=analysis_report,
            structural_score=structural_score,
            language=language,
        )
        if verbose:
            logger.info(f"  Stage 4 output: {len(text_s4.split())} words")

        # ── Stage 5: Scoring ───────────────────────────────────────────────
        logger.info("Pipeline Stage 5: Scoring")
        score_report = self.scorer.score(
            input_text=text,
            output_text=text_s4,
            domain=domain,
            register=register,
            run_detector_probes=run_detector_probes,
        )

        # Attach language to score report; skip perplexity display for Russian
        score_report["_language"] = language
        if language == "ru":
            score_report["perplexity_lift"] = None
            score_report["perplexity_note"] = "N/A (Russian text — GPT-2 English only)"

        elapsed = time.time() - t0
        score_report["_elapsed_seconds"] = elapsed
        score_report["_word_count_in"] = len(text.split())
        score_report["_word_count_out"] = len(text_s4.split())

        logger.info(f"Pipeline complete | elapsed={elapsed:.1f}s")
        return text_s4, score_report

    def run_from_params(
        self,
        params,  # GenerationParams
        verbose: bool = False,
        run_detector_probes: bool = False,
    ) -> tuple[str, dict]:
        """
        Generation mode: Phase 0 (SourceFinder + AcademicGenerator) → Stages 1–5.

        Args:
            params: GenerationParams instance
            verbose: Enable verbose logging
            run_detector_probes: Call detector APIs (GPTZero etc.) if True

        Returns:
            (output_text, score_report)
        """
        from pipeline.generator import AcademicGenerator

        # Set language for this run (read by run())
        self._current_language = params.language

        logger.info(
            f"Pipeline.run_from_params: stream={params.stream_id}, "
            f"domain={params.domain}, language={params.language}"
        )

        config = load_config()
        generator = AcademicGenerator(config)
        result = generator.generate(params)

        logger.info(
            f"Phase 0 complete: {len(result.text.split())} words generated, "
            f"structural_check_passed={result.structural_check_passed}"
        )

        output_text, score_report = self.run(
            text=result.text,
            verbose=verbose,
            domain_override=result.pipeline_domain,
            register_override=result.pipeline_register,
            run_detector_probes=run_detector_probes,
        )

        # Attach generation metadata to score report
        score_report["generation"] = {
            "stream_id": params.stream_id,
            "topic": params.topic,
            "domain": params.domain,
            "language": params.language,
            "level": params.level,
            "research_type": params.research_type,
            "pipeline_domain": result.pipeline_domain,
            "pipeline_register": result.pipeline_register,
            "section_count": result.section_count,
            "structural_check_passed": result.structural_check_passed,
            "structural_warnings": result.structural_warnings,
            "word_count_generated": len(result.text.split()),
        }

        # Attach source scoring
        if result.source_list:
            score_report["sources"] = result.source_list.score()
        else:
            score_report["sources"] = {}

        return output_text, score_report
