"""
pipeline/generator.py — Phase 0B: Academic Text Generation

Generates initial academic text using the academic_megaprompt.md system.
Works section-by-section for long-form works (VKR, coursework, research).
Integrates with SourceFinder for bibliography generation.

Flow:
  1. SourceFinder discovers and formats bibliography (Phase 0A)
  2. AcademicGenerator builds section-by-section (Phase 0B)
  3. Structural check validates output before passing to Stage 1
  4. Result fed into Pipeline.run_from_params() for humanization
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger

from pipeline.source_finder import SourceFinder, SourceList


@dataclass
class GenerationParams:
    """Parameters for text generation."""

    stream_id: str  # vkr | coursework | research | abstract_paper | text | essay | composition
    topic: str
    language: str = "ru"
    domain: str = "general"
    level: str = "bachelor"  # bachelor | master | specialist | postgraduate
    research_type: str = "theoretical"  # theoretical | empirical | applied
    university: Optional[str] = None
    word_count: Optional[int] = None
    additional_sources: list[str] = field(default_factory=list)

    def validate(self) -> None:
        valid_streams = {"vkr", "coursework", "research", "abstract_paper", "text", "essay", "composition"}
        if self.stream_id not in valid_streams:
            raise ValueError(f"Invalid stream_id '{self.stream_id}'. Must be one of: {valid_streams}")
        valid_languages = {"ru", "en"}
        if self.language not in valid_languages:
            raise ValueError(f"Invalid language '{self.language}'. Must be 'ru' or 'en'.")


@dataclass
class GenerationResult:
    """Result of Phase 0 generation."""

    text: str
    params: GenerationParams
    source_list: Optional[SourceList]
    pipeline_domain: str
    pipeline_register: str
    section_count: int
    structural_check_passed: bool
    structural_warnings: list[str] = field(default_factory=list)


# Section order per stream type
SECTION_ORDER = {
    "vkr": [
        "title_page",
        "annotation",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "chapter_3",
        "conclusion",
        "references",
    ],
    "coursework": [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "chapter_2",
        "conclusion",
        "references",
    ],
    "research": [
        "annotation",
        "introduction",
        "literature_review",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "references",
    ],
    "abstract_paper": [
        "title_page",
        "toc",
        "introduction",
        "chapter_1",
        "conclusion",
        "references",
    ],
    "text": ["full"],
    "essay": ["full"],
    "composition": ["full"],
}

# Domain → pipeline code mapping
DOMAIN_MAP = {
    "it_cs": "cs",
    "law": "general",
    "psychology": "social-science",
    "economics": "economics",
    "humanities": "humanities",
    "media": "journalistic",
    "general": "general",
}

# Register → pipeline register mapping
REGISTER_MAP = {
    "vkr": "academic",
    "coursework": "academic",
    "research": "academic",
    "abstract_paper": "academic",
    "text": "journalistic",
    "essay": "academic-essay",
    "composition": "general",
}

# Human-readable section names in Russian
SECTION_NAMES_RU = {
    "title_page": "Титульный лист",
    "annotation": "Аннотация",
    "toc": "Оглавление",
    "introduction": "Введение",
    "chapter_1": "Глава 1",
    "chapter_2": "Глава 2",
    "chapter_3": "Глава 3",
    "literature_review": "Обзор литературы",
    "methodology": "Методология",
    "results": "Результаты",
    "discussion": "Обсуждение",
    "conclusion": "Заключение",
    "references": "Список литературы",
    "full": "Текст",
}

SECTION_NAMES_EN = {
    "title_page": "Title Page",
    "annotation": "Abstract",
    "toc": "Table of Contents",
    "introduction": "Introduction",
    "chapter_1": "Chapter 1",
    "chapter_2": "Chapter 2",
    "chapter_3": "Chapter 3",
    "literature_review": "Literature Review",
    "methodology": "Methodology",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "references": "References",
    "full": "Text",
}


class AcademicGenerator:
    """
    Phase 0B: Generates academic text using academic_megaprompt.md.

    Usage:
        gen = AcademicGenerator(config)
        result = gen.generate(params)
        # result.text is the raw generated text
        # result.source_list is the GOST bibliography
    """

    def __init__(self, config: dict):
        self.config = config
        gen_cfg = config.get("generator", {})
        self.model = gen_cfg.get("generation_model", "claude-sonnet-4-6")
        self.temperature = gen_cfg.get("generation_temperature", 0.90)
        self.max_tokens = gen_cfg.get("max_tokens_per_section", 4096)
        self.section_word_targets = gen_cfg.get("section_word_targets", {})
        self.structural_check_cfg = gen_cfg.get("structural_check", {})
        self.source_minimums = gen_cfg.get("source_minimums", {})

        self._megaprompt: Optional[str] = None
        self._source_finder: Optional[SourceFinder] = None

    def _get_source_finder(self) -> SourceFinder:
        if self._source_finder is None:
            self._source_finder = SourceFinder(self.config)
        return self._source_finder

    def _load_megaprompt(self) -> str:
        if self._megaprompt is not None:
            return self._megaprompt
        path = Path(__file__).parent.parent / "prompts" / "academic_megaprompt.md"
        if path.exists():
            self._megaprompt = path.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"academic_megaprompt.md not found at {path}")
        return self._megaprompt

    def generate(self, params: GenerationParams) -> GenerationResult:
        """Main entry point: generate text for given params."""
        params.validate()

        pipeline_domain = DOMAIN_MAP.get(params.domain, "general")
        pipeline_register = REGISTER_MAP.get(params.stream_id, "academic")

        logger.info(
            f"AcademicGenerator: stream={params.stream_id}, domain={params.domain}, "
            f"language={params.language}, topic='{params.topic[:60]}...'"
        )

        # Phase 0A: Discover sources
        source_list = None
        if self.config.get("source_finder", {}).get("enabled", True):
            min_sources = self._get_min_sources(params)
            if min_sources > 0:
                sf = self._get_source_finder()
                source_list = sf.find(
                    topic=params.topic,
                    domain=params.domain,
                    language=params.language,
                    stream_id=params.stream_id,
                    min_sources=min_sources,
                    additional_sources=params.additional_sources,
                )
                logger.info(
                    f"AcademicGenerator: SourceFinder returned {len(source_list.sources)} sources"
                )

        # Phase 0B: Generate text
        sections_order = SECTION_ORDER.get(params.stream_id, ["full"])
        if len(sections_order) == 1 and sections_order[0] == "full":
            text = self._generate_full(params, source_list)
            section_count = 1
        else:
            text = self._generate_sectional(params, source_list, sections_order)
            section_count = len(sections_order)

        # Structural check
        check_passed, warnings = self._run_structural_check(text, params)
        if not check_passed and self.structural_check_cfg.get("regen_on_hard_failure", True):
            max_attempts = self.structural_check_cfg.get("max_regen_attempts", 2)
            for attempt in range(max_attempts):
                logger.warning(
                    f"AcademicGenerator: structural check failed (attempt {attempt + 1}/{max_attempts}), regenerating..."
                )
                if len(sections_order) == 1 and sections_order[0] == "full":
                    text = self._generate_full(params, source_list)
                else:
                    text = self._generate_sectional(params, source_list, sections_order)
                check_passed, warnings = self._run_structural_check(text, params)
                if check_passed:
                    break

        return GenerationResult(
            text=text,
            params=params,
            source_list=source_list,
            pipeline_domain=pipeline_domain,
            pipeline_register=pipeline_register,
            section_count=section_count,
            structural_check_passed=check_passed,
            structural_warnings=warnings,
        )

    def generate_section(
        self,
        section_id: str,
        params: GenerationParams,
        source_list: Optional[SourceList] = None,
        previously_generated: str = "",
    ) -> str:
        """
        Generate a single section of academic text.

        Public API for Phase 3 workers. Wraps the internal section generation
        logic that was previously only called from _generate_sectional().

        Args:
            section_id: Section to generate (e.g., "introduction", "chapter_1")
            params: Generation parameters (topic, domain, language, etc.)
            source_list: GOST bibliography from Phase 0A (injected into megaprompt)
            previously_generated: Last ~500 chars of previous section (for logical bridge)

        Returns:
            Generated section text as string.

        Special cases:
            - "title_page", "toc": Returns empty string (format-only, handled by formatter)
            - "references": Returns formatted source list if source_list provided,
              otherwise generates via LLM
            - "full": Calls _generate_full() for single-generation streams
        """
        import anthropic

        # Format-only sections: return empty (handled by formatter.py / TOC worker)
        if section_id in ("title_page", "toc"):
            logger.debug(f"AcademicGenerator.generate_section: '{section_id}' is format-only, returning empty")
            return ""

        # Full generation (text/essay/composition)
        if section_id == "full":
            return self._generate_full(params, source_list)

        # References section: format source list directly
        if section_id == "references":
            if source_list and source_list.sources:
                section_names = SECTION_NAMES_RU if params.language == "ru" else SECTION_NAMES_EN
                section_header = section_names.get("references", "References")
                return f"## {section_header}\n\n{source_list.as_numbered_list()}"
            # Fall through to LLM generation if no source list

        # Standard section generation via LLM
        system_prompt = self._build_system_prompt(params, source_list)
        target_words = params.word_count or self._get_target_words(section_id, params)
        user_prompt = self._build_section_prompt(
            section_id, params, previously_generated, target_words
        )

        logger.info(
            f"AcademicGenerator.generate_section: '{section_id}' (~{target_words} words)"
        )

        client = anthropic.Anthropic()
        temperature = 0.1 if section_id == "references" else self.temperature

        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text.strip()

    def _get_min_sources(self, params: GenerationParams) -> int:
        """Get minimum source count for the given stream and level."""
        stream = params.stream_id
        level = params.level

        if stream == "vkr":
            key = f"vkr_{level}"
            return self.source_minimums.get(key, self.source_minimums.get("vkr_bachelor", 50))
        return self.source_minimums.get(stream, 0)

    def _build_system_prompt(self, params: GenerationParams, source_list: Optional[SourceList]) -> str:
        """Build the system prompt from megaprompt + source list."""
        megaprompt = self._load_megaprompt()

        # Append source list to prompt if available
        if source_list and source_list.sources:
            bibliography = source_list.as_numbered_list()
            if params.language == "ru":
                source_section = (
                    f"\n\n---\n\n## СПИСОК ИСТОЧНИКОВ ДЛЯ ЦИТИРОВАНИЯ\n\n"
                    f"Используй следующие источники для цитирования в тексте. "
                    f"Ссылайся на них по номеру [N] согласно ГОСТ. "
                    f"Не придумывай другие источники.\n\n"
                    f"{bibliography}\n\n---\n"
                )
            else:
                source_section = (
                    f"\n\n---\n\n## SOURCES FOR CITATION\n\n"
                    f"Use the following sources for in-text citations. "
                    f"Reference them by number [N] per GOST standard. "
                    f"Do not invent other sources.\n\n"
                    f"{bibliography}\n\n---\n"
                )
            return megaprompt + source_section

        return megaprompt

    def _build_section_prompt(
        self,
        section_id: str,
        params: GenerationParams,
        previously_generated: str,
        target_words: int,
    ) -> str:
        """Build a user-turn prompt for generating a specific section."""
        section_names = SECTION_NAMES_RU if params.language == "ru" else SECTION_NAMES_EN
        section_name = section_names.get(section_id, section_id)

        # Get last paragraph of previous section for bridge (AC-2)
        last_para = ""
        if previously_generated:
            paras = [p.strip() for p in previously_generated.split("\n\n") if p.strip()]
            if paras:
                last_para = paras[-1][:500]  # Truncate to avoid context overflow

        if params.language == "ru":
            prompt = (
                f"Тема работы: «{params.topic}»\n"
                f"Стрим: {params.stream_id}\n"
                f"Дисциплина: {params.domain}\n"
                f"Тип исследования: {params.research_type}\n"
                f"Уровень: {params.level}\n"
            )
            if params.university:
                prompt += f"Учебное заведение: {params.university}\n"
            prompt += f"\nНапиши раздел: **{section_name}**\n"
            prompt += f"Целевой объём: примерно {target_words} слов.\n"

            if last_para:
                prompt += (
                    f"\nПоследний абзац предыдущего раздела (для логической связи):\n"
                    f"«{last_para}»\n"
                    f"\nВАЖНО: Начни с содержательной ссылки на предыдущий раздел, "
                    f"а не с вводного коннектора типа «Кроме того,» или «Следует отметить,».\n"
                )
        else:
            prompt = (
                f"Topic: «{params.topic}»\n"
                f"Stream: {params.stream_id}\n"
                f"Domain: {params.domain}\n"
                f"Research type: {params.research_type}\n"
                f"Level: {params.level}\n"
            )
            if params.university:
                prompt += f"University: {params.university}\n"
            prompt += f"\nWrite section: **{section_name}**\n"
            prompt += f"Target length: approximately {target_words} words.\n"

            if last_para:
                prompt += (
                    f"\nLast paragraph of the previous section (for logical bridge):\n"
                    f"«{last_para}»\n"
                    f"\nIMPORTANT: Open with a content reference to the previous section, "
                    f"not with a connector like 'Moreover,' or 'Additionally,'.\n"
                )

        return prompt

    def _get_target_words(self, section_id: str, params: GenerationParams) -> int:
        """Get word count target for a section."""
        stream_targets = self.section_word_targets.get(params.stream_id, {})

        # Direct lookup
        if section_id in stream_targets:
            return stream_targets[section_id]

        # Chapter fallback (chapter_1, chapter_2, chapter_3 → "chapter")
        if section_id.startswith("chapter_"):
            return stream_targets.get("chapter", 2500)

        # Fallback for unknown section
        return 800

    def _generate_full(self, params: GenerationParams, source_list: Optional[SourceList]) -> str:
        """Generate text as a single call (for essay, text, composition)."""
        import anthropic

        system_prompt = self._build_system_prompt(params, source_list)
        target_words = params.word_count or self._get_target_words("full", params)

        if params.language == "ru":
            user_prompt = (
                f"Напиши полный текст в стриме «{params.stream_id}» на тему: «{params.topic}».\n"
                f"Дисциплина: {params.domain}. Тип: {params.research_type}.\n"
                f"Целевой объём: ~{target_words} слов."
            )
        else:
            user_prompt = (
                f"Write a complete text in stream «{params.stream_id}» on topic: «{params.topic}».\n"
                f"Domain: {params.domain}. Type: {params.research_type}.\n"
                f"Target length: ~{target_words} words."
            )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens * 2,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text.strip()

    def _generate_sectional(
        self,
        params: GenerationParams,
        source_list: Optional[SourceList],
        sections: list[str],
    ) -> str:
        """Generate text section by section, passing previous content as context."""
        import anthropic

        system_prompt = self._build_system_prompt(params, source_list)
        client = anthropic.Anthropic()

        all_sections: list[str] = []
        previously_generated = ""
        section_names = SECTION_NAMES_RU if params.language == "ru" else SECTION_NAMES_EN

        # Sections we skip for actual generation (format-only content)
        skip_sections = {"title_page", "toc"}

        for section_id in sections:
            if section_id in skip_sections:
                logger.debug(f"AcademicGenerator: skipping format-only section '{section_id}'")
                continue

            # References section: inject source list directly
            if section_id == "references":
                if source_list and source_list.sources:
                    section_header = section_names.get("references", "Список литературы")
                    refs_text = f"## {section_header}\n\n{source_list.as_numbered_list()}"
                    all_sections.append(refs_text)
                else:
                    # Generate references via LLM if no source list
                    target_words = 200
                    user_prompt = self._build_section_prompt(
                        section_id, params, previously_generated, target_words
                    )
                    response = client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=0.1,  # Low temp for references
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    section_text = response.content[0].text.strip()
                    all_sections.append(section_text)
                continue

            target_words = params.word_count or self._get_target_words(section_id, params)
            user_prompt = self._build_section_prompt(
                section_id, params, previously_generated, target_words
            )

            logger.info(
                f"AcademicGenerator: generating section '{section_id}' (~{target_words} words)"
            )

            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            section_text = response.content[0].text.strip()
            all_sections.append(section_text)

            # Update context for next section (last 2 paragraphs)
            paras = [p.strip() for p in section_text.split("\n\n") if p.strip()]
            previously_generated = "\n\n".join(paras[-2:]) if paras else section_text

        return "\n\n".join(all_sections)

    def _run_structural_check(self, text: str, params: GenerationParams) -> tuple[bool, list[str]]:
        """
        Run structural checks on the generated text.
        Reuses structural_rewriter detection where possible.
        Returns (passed, list_of_warnings).
        """
        warnings = []
        cfg = self.structural_check_cfg

        # Check announcement openers
        max_openers = cfg.get("max_announcement_openers", 0)
        opener_count = self._count_announcement_openers(text, params.language)
        if opener_count > max_openers:
            warnings.append(
                f"HARD FAIL: {opener_count} announcement openers found (max: {max_openers})"
            )

        # Check triplets
        max_triplets = cfg.get("max_triplets", 0)
        triplet_count = self._count_triplets(text)
        if triplet_count > max_triplets:
            warnings.append(
                f"HARD FAIL: {triplet_count} triplet series found (max: {max_triplets})"
            )

        # Check Block 7 red flags (simplified: count P7 words)
        max_red_flags = cfg.get("max_block7_red_flags", 2)
        red_flag_count = self._count_red_flags(text, params.language)
        if red_flag_count > max_red_flags:
            warnings.append(
                f"WARNING: {red_flag_count} Block 7 red flag patterns found (max: {max_red_flags})"
            )

        # Hard failure = any HARD FAIL in warnings
        hard_failed = any("HARD FAIL" in w for w in warnings)

        if not warnings:
            logger.info("AcademicGenerator: structural check passed")
        else:
            for w in warnings:
                logger.warning(f"AcademicGenerator: {w}")

        return not hard_failed, warnings

    def _count_announcement_openers(self, text: str, language: str) -> int:
        """Count announcement opener patterns in text."""
        patterns_en = [
            r"Here's the problem with",
            r"is worth a brief detour",
            r"There's also a .{1,30} worth flagging",
            r"also deserves mention",
            r"I mention this mostly because",
            r"is instructive about",
            r"is actually remarkable",
        ]
        patterns_ru = [
            r"следует отметить, что",
            r"необходимо отметить, что",
            r"важно подчеркнуть, что",
            r"стоит отметить, что",
            r"обратим внимание на то",
            r"отметим, что",
        ]
        patterns = patterns_ru if language == "ru" else patterns_en
        count = 0
        for p in patterns:
            count += len(re.findall(p, text, re.IGNORECASE))
        return count

    def _count_triplets(self, text: str) -> int:
        """Count noun/verb tricolon patterns (X, Y, and Z)."""
        # Match patterns like "X, Y, and Z" or "X, Y, и Z"
        en_pattern = r"\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+and\s+\w"
        ru_pattern = r"\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+и\s+\w"
        count = len(re.findall(en_pattern, text))
        count += len(re.findall(ru_pattern, text))
        return count

    def _count_red_flags(self, text: str, language: str) -> int:
        """Count P7 absolute ban words in text (simplified check)."""
        if language == "ru":
            ban_words = [
                "следует отметить",
                "является ключевым",
                "играет важную роль",
                "необходимо подчеркнуть",
                "представляется актуальным",
                "как известно",
            ]
        else:
            ban_words = [
                "delve into",
                "embark on",
                "tapestry",
                "vibrant",
                "nestled",
                "synergy",
                "cutting-edge",
                "game-changer",
            ]
        count = 0
        for w in ban_words:
            count += len(re.findall(re.escape(w), text, re.IGNORECASE))
        return count

    def score(self, text: str) -> dict:
        """Return basic generation metrics."""
        word_count = len(text.split())
        para_count = len([p for p in text.split("\n\n") if p.strip()])
        return {
            "word_count": word_count,
            "paragraph_count": para_count,
        }
