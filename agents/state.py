from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CostReport:
    """Tracks API usage and costs for a single pipeline run."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_api_calls: int = 0
    total_cost_usd: float = 0.0
    cache_savings_usd: float = 0.0
    cost_by_stage: dict[str, float] = field(default_factory=dict)
    calls_by_agent: dict[str, int] = field(default_factory=dict)

    def add_usage(self, agent_name: str, usage: dict) -> None:
        """
        Add a single API call's usage to the running totals.

        Args:
            agent_name: Name of the agent that made the call
            usage: Dict from BaseAgent.call_claude() with token counts
        """
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)
        self.total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)
        self.total_cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
        self.total_api_calls += 1
        self.calls_by_agent[agent_name] = self.calls_by_agent.get(agent_name, 0) + 1


@dataclass
class PipelineState:
    """
    Central state object passed between all agents.

    Every agent receives this, may modify fields relevant to its job,
    and returns it. Fields are additive — agents add data, never delete it.

    Lifecycle:
    1. Created by CEO with initial parameters (mode, stream_id, topic, etc.)
    2. Phase 0: source_list, generated_text populated
    3. Stage 1 (HM-1): analysis_report populated
    4. Stages 2-4 (HM-2/3/4): text progressively transformed
    5. Stage 5 (HM-5): final_score_report populated
    6. Export: .txt + .docx + score_report.json generated
    """

    # ── Required fields (set at creation) ──────────────────────────
    mode: str                        # "generation" | "humanization"
    text: str = ""                   # Current text (mutated by each stage)

    # ── Identity fields (set by CEO or user input) ─────────────────
    stream_id: str = ""              # vkr | coursework | research | abstract_paper | text | essay | composition
    topic: str = ""                  # Full topic string
    language: str = "en"             # "en" | "ru"
    domain: str = "general"          # it_cs | law | psychology | economics | humanities | media | general
    register: str = "general"        # academic | academic-essay | journalistic | general
    level: str = ""                  # bachelor | master | specialist | postgraduate
    research_type: str = ""          # theoretical | empirical | applied
    university: str = ""             # Optional institution name

    # ── Phase 0 output ─────────────────────────────────────────────
    source_list: Any = None          # SourceList from source_finder (Phase 0A)
    generated_sections: dict = field(default_factory=dict)  # section_id → text (Phase 0B)
    visualization_count: dict = field(default_factory=lambda: {"tables": 0, "figures": 0})
    last_section_text: str = ""              # Last generated section text (for logical bridge between sections)

    # ── Stage 1 (HM-1) output ─────────────────────────────────────
    analysis_report: dict = field(default_factory=dict)

    # ── Stage 5 (HM-5) output ─────────────────────────────────────
    final_score_report: dict = field(default_factory=dict)

    # ── Feedback loop ──────────────────────────────────────────────
    feedback_from_qa: Optional[dict] = None     # QA gate feedback → routed to specific HM stage
    feedback_iterations: int = 0                # Count of HM-5 → HM-2/3/4 loops (max 2)
    feedback_target: str = ""                   # "hm2" | "hm3" | "hm4" — where to route feedback

    # ── Error tracking ─────────────────────────────────────────────
    errors: list[str] = field(default_factory=list)

    # ── Cost tracking ──────────────────────────────────────────────
    cost_report: CostReport = field(default_factory=CostReport)

    # ── Worker skip tracking (Smart Worker Skip from Phase 6) ──────
    skipped_workers: list[str] = field(default_factory=list)

    # ── Output paths (set by ExportManager) ────────────────────────
    output_dir: str = ""             # Path to output directory
    output_txt_path: str = ""        # Path to .txt output
    output_docx_path: str = ""       # Path to .docx output
    output_score_path: str = ""      # Path to score_report.json

    # ── Metadata ───────────────────────────────────────────────────
    pipeline_version: str = "0.1.0"

    def add_error(self, agent_name: str, error: str) -> None:
        """Add a formatted error entry."""
        self.errors.append(f"[{agent_name}] {error}")

    def has_errors(self) -> bool:
        """Check if any errors occurred during pipeline execution."""
        return len(self.errors) > 0

    def word_count(self) -> int:
        """Current text word count."""
        return len(self.text.split()) if self.text else 0
