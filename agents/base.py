from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from loguru import logger

from agents.state import PipelineState


class BaseAgent(ABC):
    """
    Abstract base for all agents in the multi-agent pipeline.

    Every agent (CEO, Manager, Stage, Worker, Gate, Service) inherits this class
    and implements execute(state) → state.

    Design principles:
    - Pure state-in, state-out: no hidden side effects
    - Each agent has a name for logging and cost tracking
    - Prompt loading from agents/prompts/ directory
    - Claude API calls go through call_claude() with retry + cost tracking
    - All errors are caught and stored in state.errors (never crash pipeline)
    """

    # Subclasses set this
    agent_name: str = "base"
    agent_type: str = "base"  # "ceo" | "manager" | "stage" | "worker" | "gate" | "service"

    def __init__(self) -> None:
        self._prompts_dir = Path(__file__).parent / "prompts"

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Main entry point. Takes PipelineState, returns modified PipelineState.
        Must be implemented by every agent.
        """
        ...

    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt template from agents/prompts/<prompt_name>.md

        Args:
            prompt_name: filename without extension (e.g., "hm2_architect")

        Returns:
            Prompt text as string

        Raises:
            FileNotFoundError: if prompt file does not exist
        """
        path = self._prompts_dir / f"{prompt_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def call_claude(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> tuple[str, dict]:
        """
        Call Claude API with retry logic and cost tracking.

        Uses cache_control=ephemeral on system prompt for Prompt Caching
        (cache hit = 10% input price — critical optimization from IMPLEMENTATION_PLAN).

        Args:
            system: System prompt text
            user: User message text
            model: Override model (default: from config.yaml pipeline.rewrite_model)
            temperature: Override temperature (default: from config.yaml)
            max_tokens: Max output tokens

        Returns:
            tuple of (response_text, usage_dict)
            usage_dict: {"input_tokens": int, "output_tokens": int, "cache_hit": bool}
        """
        import anthropic
        from pipeline import load_config

        cfg = load_config()
        model = model or cfg["pipeline"]["rewrite_model"]
        temperature = temperature if temperature is not None else cfg["pipeline"]["rewrite_temperature"]
        delay = cfg["pipeline"].get("retry_delay_seconds", 2)
        max_retries = cfg["pipeline"].get("max_retries", 3)

        client = anthropic.Anthropic()

        for attempt in range(max_retries):
            try:
                t0 = time.time()
                resp = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=[{
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": user}],
                )
                elapsed = time.time() - t0

                usage = {
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                    "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0),
                    "model": model,
                    "elapsed_seconds": round(elapsed, 2),
                }

                logger.debug(
                    f"[{self.agent_name}] API call: "
                    f"in={usage['input_tokens']} out={usage['output_tokens']} "
                    f"cache_read={usage['cache_read_input_tokens']} "
                    f"time={elapsed:.1f}s"
                )

                return resp.content[0].text, usage

            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    wait = delay * (2 ** attempt)
                    logger.warning(
                        f"[{self.agent_name}] Rate limit on attempt {attempt + 1}, "
                        f"retrying in {wait}s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"[{self.agent_name}] Rate limit exceeded after {max_retries} retries")
                    raise

            except anthropic.APIError as e:
                logger.error(f"[{self.agent_name}] API error: {e}")
                raise

        return "", {}

    def safe_execute(self, state: PipelineState) -> PipelineState:
        """
        Wrapper around execute() that catches exceptions and stores them in state.errors.
        Use this in orchestration code to prevent single-agent failures from crashing the pipeline.
        Sync-only: do NOT call from inside an async context (use `await execute()` there).
        """
        import asyncio
        try:
            return asyncio.run(self.execute(state))
        except Exception as e:
            error_msg = f"[{self.agent_name}] {type(e).__name__}: {e}"
            logger.error(error_msg)
            state.errors.append(error_msg)
            return state

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.agent_name} type={self.agent_type}>"
