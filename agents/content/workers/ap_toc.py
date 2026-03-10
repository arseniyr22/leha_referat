from __future__ import annotations

from loguru import logger

from agents.content.workers.base_section_worker import BaseSectionWorker
from agents.state import PipelineState


class APTOCWorker(BaseSectionWorker):
    """
    Abstract Paper Table of Contents worker (2-pass).

    Same pattern as VKRTOCWorker but with abstract_paper-specific TOC_SECTIONS.
    """

    section_id = "toc"
    agent_name = "ap_toc"

    # Abstract Paper TOC: intro, chapter_1, conclusion
    TOC_SECTIONS = [
        "introduction",
        "chapter_1",
        "conclusion",
    ]

    async def execute_pass_2(self, state: PipelineState) -> PipelineState:
        """Build TOC from generated section headings."""
        from pipeline.generator import SECTION_NAMES_RU, SECTION_NAMES_EN

        section_names = SECTION_NAMES_RU if state.language == "ru" else SECTION_NAMES_EN
        toc_title = "Оглавление" if state.language == "ru" else "Table of Contents"

        toc_lines: list[str] = [f"## {toc_title}", ""]

        for section_id in self.TOC_SECTIONS:
            section_text = state.generated_sections.get(section_id, "")
            heading = self._extract_heading(section_text)
            if not heading:
                heading = section_names.get(section_id, section_id.replace("_", " ").title())
            toc_lines.append(f"- {heading}")

        ref_name = section_names.get("references", "References")
        toc_lines.append(f"- {ref_name}")

        toc_text = "\n".join(toc_lines)
        state.generated_sections["toc"] = toc_text

        if toc_text:
            state.text = toc_text + "\n\n" + state.text

        logger.info(
            f"[{self.agent_name}] TOC Pass 2 complete | "
            f"{len(self.TOC_SECTIONS) + 1} entries"
        )
        return state

    @staticmethod
    def _extract_heading(section_text: str) -> str:
        """Extract the first markdown heading from section text."""
        if not section_text:
            return ""
        for line in section_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
            if stripped.startswith("### "):
                return stripped[4:].strip()
        return ""
