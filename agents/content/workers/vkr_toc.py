from __future__ import annotations

from loguru import logger

from agents.content.workers.base_section_worker import BaseSectionWorker
from agents.state import PipelineState


class VKRTOCWorker(BaseSectionWorker):
    """
    VKR Table of Contents worker (2-pass).

    Pass 1 (execute): BaseSectionWorker stores empty string for "toc" (format-only).
    Pass 2 (execute_pass_2): Builds TOC from state.generated_sections headings.

    The TOC is a text representation for the generated document.
    The actual formatted TOC in .docx is handled by formatter.py.
    This text TOC serves as:
    - A structural reference for the humanization pipeline
    - Content for state.text so the full document is readable as plain text
    """

    section_id = "toc"
    agent_name = "vkr_toc"

    # Section IDs that appear in TOC (exclude title_page, toc itself, references)
    # Must match the VKR SECTION_ORDER minus non-TOC items
    TOC_SECTIONS = [
        "annotation",
        "introduction",
        "chapter_1",
        "chapter_2",
        "chapter_3",
        "conclusion",
    ]

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        """
        Build TOC from generated section headings (called after all sections generated).

        Extracts the first ## heading from each generated section to build a
        plain-text table of contents. Stores result in state.generated_sections["toc"]
        and prepends to state.text at the correct position.

        Uses SECTION_NAMES from pipeline/generator.py for fallback names.
        """
        from pipeline.generator import SECTION_NAMES_RU, SECTION_NAMES_EN

        section_names = SECTION_NAMES_RU if state.language == "ru" else SECTION_NAMES_EN
        toc_title = "Оглавление" if state.language == "ru" else "Table of Contents"

        toc_lines: list[str] = [f"## {toc_title}", ""]

        for section_id in self.TOC_SECTIONS:
            section_text = state.generated_sections.get(section_id, "")
            heading = self._extract_heading(section_text)

            if not heading:
                # Fallback to standard section name
                heading = section_names.get(section_id, section_id.replace("_", " ").title())

            toc_lines.append(f"- {heading}")

        # Always add references at the end
        ref_name = section_names.get("references", "References")
        toc_lines.append(f"- {ref_name}")

        toc_text = "\n".join(toc_lines)

        # Update state
        state.generated_sections["toc"] = toc_text

        # Prepend TOC text to state.text
        # (formatter.py will handle actual document ordering based on generated_sections)
        if toc_text:
            state.text = toc_text + "\n\n" + state.text

        logger.info(
            f"[{self.agent_name}] TOC Pass 2 complete | "
            f"{len(self.TOC_SECTIONS) + 1} entries"
        )

        return state

    @staticmethod
    def _extract_heading(section_text: str) -> str:
        """
        Extract the first markdown heading from section text.

        Looks for ## or ### at the start of a line.
        Returns the heading text without the ## prefix, or empty string if not found.
        """
        if not section_text:
            return ""

        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()

        return ""
