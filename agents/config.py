from __future__ import annotations

from dataclasses import dataclass

from pipeline import load_config


@dataclass
class AgentConfig:
    """
    Agent-specific configuration loaded from config.yaml `agents:` section.

    Falls back to pipeline-level defaults if agents section is missing.
    This allows gradual migration: agents work with existing config.yaml
    and use agent-specific overrides when they exist.
    """
    # Model selection (can differ from pipeline defaults)
    rewrite_model: str = "claude-sonnet-4-6"
    analysis_model: str = "claude-haiku-4-5-20251001"

    # Temperature
    rewrite_temperature: float = 0.9
    analysis_temperature: float = 0.3

    # Retry
    max_retries: int = 3
    retry_delay_seconds: int = 2

    # Feedback loop
    max_feedback_iterations: int = 2

    # Cost guardrails
    max_cost_per_request_usd: float = 15.0    # Hard stop if exceeded
    warn_cost_threshold_usd: float = 10.0     # Warning log if exceeded

    # Smart Worker Skip
    enable_smart_skip: bool = True


def load_agent_config() -> AgentConfig:
    """
    Load agent configuration from config.yaml.

    Reads from `agents:` section if it exists.
    Falls back to `pipeline:` section defaults for model/temperature/retry.
    Returns AgentConfig with all fields populated.
    """
    cfg = load_config()

    # Start with pipeline defaults
    pipeline_cfg = cfg.get("pipeline", {})
    defaults = {
        "rewrite_model": pipeline_cfg.get("rewrite_model", "claude-sonnet-4-6"),
        "analysis_model": pipeline_cfg.get("analysis_model", "claude-haiku-4-5-20251001"),
        "rewrite_temperature": pipeline_cfg.get("rewrite_temperature", 0.9),
        "analysis_temperature": pipeline_cfg.get("analysis_temperature", 0.3),
        "max_retries": pipeline_cfg.get("max_retries", 3),
        "retry_delay_seconds": pipeline_cfg.get("retry_delay_seconds", 2),
    }

    # Override with agents section if present
    agents_cfg = cfg.get("agents", {})
    defaults.update({k: v for k, v in agents_cfg.items() if v is not None})

    return AgentConfig(**{
        k: defaults.get(k, getattr(AgentConfig, k, None))
        for k in AgentConfig.__dataclass_fields__
        if k in defaults
    })
