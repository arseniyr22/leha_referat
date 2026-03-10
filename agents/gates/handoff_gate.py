from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from agents.base import BaseAgent
from agents.state import PipelineState


@dataclass
class HandoffMetadata:
    """
    Metadata package passed from Phase 0 (generation) to humanization pipeline.

    Created by HandoffGate after Phase 0 content generation is complete.
    Contains all information needed by HumanizerManager (Phase 4) to process the text.
    """
    text: str                          # Full Phase 0 output (all sections concatenated)
    source_count: int = 0              # Number of sources from Phase 0A
    viz_count_tables: int = 0          # Table count from Phase 0B
    viz_count_figures: int = 0         # Figure count from Phase 0B
    domain: str = "general"            # Domain for HM stages
    register: str = "general"          # Register for HM stages
    language: str = "en"               # Language for AC-rules gating
    stream_id: str = ""                # Stream type for context
    level: str = ""                    # Academic level for context
    sections_generated: int = 0        # Number of sections generated
    structural_violations: list[str] = field(default_factory=list)  # Any QA violations found


class HandoffGate(BaseAgent):
    """
    Handoff Gate — validates Phase 0 output and packages for humanization.

    Sits between Phase 0 (content generation) and Phase 4 (humanization).
    Responsibilities:
    1. Validate Phase 0 structural requirements:
       - Announcement openers = 0
       - Triplet instances = 0
       - Visualization count >= stream minimum (БЛОК 16.2)
    2. Package HandoffMetadata for HumanizerManager
    3. Map domain → pipeline domain, stream_id → register
    4. Return state ready for humanization pipeline entry

    This gate REPORTS violations but does NOT block. ContentQAGate (Phase 1)
    handles blocking logic. HandoffGate is a metadata packager that also validates.
    """

    agent_name = "handoff_gate"
    agent_type = "gate"

    # Domain → pipeline code mapping (from generator.py DOMAIN_MAP)
    DOMAIN_MAP: dict[str, str] = {
        "it_cs": "cs",
        "law": "general",
        "psychology": "social-science",
        "economics": "economics",
        "humanities": "humanities",
        "media": "journalistic",
        "general": "general",
    }

    # stream_id → register mapping (from generator.py REGISTER_MAP)
    REGISTER_MAP: dict[str, str] = {
        "vkr": "academic",
        "coursework": "academic",
        "research": "academic",
        "abstract_paper": "academic",
        "text": "journalistic",
        "essay": "academic-essay",
        "composition": "general",
    }

    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Validate Phase 0 output and package metadata for humanization.

        Steps:
        1. Validate: state must have generated text
        2. Run structural validation (announcement openers, triplets)
        3. Check visualization count vs. minimum
        4. Build HandoffMetadata
        5. Set state.register and state.domain for downstream stages
        6. Return state ready for humanization
        """
        if not state.text:
            state.add_error(self.agent_name, "No text to hand off — Phase 0 produced no output")
            return state

        logger.info(
            f"[HandoffGate] Validating Phase 0 output | "
            f"words={state.word_count()} | "
            f"sections={len(state.generated_sections)} | "
            f"stream_id={state.stream_id}"
        )

        violations: list[str] = []

        # Step 2: Structural validation
        violations.extend(self._check_structural_quality(state))

        # Step 3: Visualization check
        violations.extend(self._check_visualization_count(state))

        # Log violations (non-blocking)
        if violations:
            logger.warning(f"[HandoffGate] {len(violations)} violations found:")
            for v in violations:
                logger.warning(f"  - {v}")
        else:
            logger.info("[HandoffGate] All structural checks passed")

        # Step 4-5: Set register and domain for humanization pipeline
        state.register = self.REGISTER_MAP.get(state.stream_id, "general")
        pipeline_domain = self.DOMAIN_MAP.get(state.domain, "general")

        # Build metadata (stored for Phase 4 HumanizerManager)
        source_count = 0
        if state.source_list is not None:
            source_count = len(state.source_list.sources) if hasattr(state.source_list, 'sources') else 0

        metadata = HandoffMetadata(
            text=state.text,
            source_count=source_count,
            viz_count_tables=state.visualization_count.get("tables", 0),
            viz_count_figures=state.visualization_count.get("figures", 0),
            domain=pipeline_domain,
            register=state.register,
            language=state.language,
            stream_id=state.stream_id,
            level=state.level,
            sections_generated=len(state.generated_sections),
            structural_violations=violations,
        )

        # Store metadata in state for HumanizerManager (Phase 4)
        # Using analysis_report as a temporary container until Phase 4 defines its own
        state.analysis_report["handoff_metadata"] = {
            "source_count": metadata.source_count,
            "viz_count_tables": metadata.viz_count_tables,
            "viz_count_figures": metadata.viz_count_figures,
            "domain": metadata.domain,
            "register": metadata.register,
            "language": metadata.language,
            "stream_id": metadata.stream_id,
            "level": metadata.level,
            "sections_generated": metadata.sections_generated,
            "structural_violations": metadata.structural_violations,
            "word_count": state.word_count(),
        }

        logger.info(
            f"[HandoffGate] Handoff complete | "
            f"register={state.register} | domain={pipeline_domain} | "
            f"sources={source_count} | violations={len(violations)}"
        )

        return state

    def _check_structural_quality(self, state: PipelineState) -> list[str]:
        """
        Check for announcement openers and triplets in generated text.

        Uses simple regex detection (same patterns as generator.py structural check).
        Returns list of violation strings.
        """
        import re
        violations: list[str] = []
        text = state.text

        # Announcement openers (target: 0)
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
        patterns = patterns_ru if state.language == "ru" else patterns_en
        opener_count = 0
        for p in patterns:
            opener_count += len(re.findall(p, text, re.IGNORECASE))
        if opener_count > 0:
            violations.append(f"announcement_openers={opener_count} (target: 0)")

        # Triplets: X, Y, and Z pattern (matches generator.py _count_triplets logic)
        en_triplet = r'\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+and\s+\w'
        ru_triplet = r'\b\w[\w\s]{2,30},\s+\w[\w\s]{2,30},\s+и\s+\w'
        triplet_pattern = ru_triplet if state.language == "ru" else en_triplet
        triplet_count = len(re.findall(triplet_pattern, text))
        if triplet_count > 0:
            violations.append(f"triplet_instances={triplet_count} (target: 0)")

        return violations

    def _check_visualization_count(self, state: PipelineState) -> list[str]:
        """Check visualization count against stream minimum."""
        from agents.gates.content_qa import ContentQAGate

        violations: list[str] = []
        gate = ContentQAGate()

        total_viz = state.visualization_count.get("tables", 0) + state.visualization_count.get("figures", 0)
        minimum = gate._get_viz_minimum(state.stream_id, state.level)

        if total_viz < minimum:
            violations.append(
                f"visualizations={total_viz} (minimum: {minimum} for {state.stream_id}/{state.level})"
            )

        return violations
