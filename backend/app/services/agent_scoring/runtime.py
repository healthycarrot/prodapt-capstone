from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

try:
    from agents import Agent, Runner, set_default_openai_key
    from agents.model_settings import ModelSettings
except Exception:  # pragma: no cover
    Agent = None
    Runner = None
    set_default_openai_key = None
    ModelSettings = None


OutputT = TypeVar("OutputT", bound=BaseModel)
logger = logging.getLogger(__name__)


def is_agent_sdk_available() -> bool:
    return Agent is not None and Runner is not None


@dataclass(slots=True)
class AgentRuntime:
    model: str
    timeout_sec: float
    api_key: str = ""
    max_turns: int = 1
    temperature: float = 0.0

    async def run_structured(
        self,
        *,
        name: str,
        instructions: str,
        input_text: str,
        output_type: type[OutputT],
    ) -> OutputT:
        if Agent is None or Runner is None:
            raise RuntimeError("openai-agents is not installed.")

        self._configure_openai_credentials()
        input_chars = len(input_text or "")
        if input_chars > 50000:
            logger.warning(
                "Large agent input detected (agent=%s, input_chars=%s).",
                name,
                input_chars,
            )
        started_at = time.perf_counter()

        kwargs: dict[str, Any] = {
            "name": name,
            "instructions": instructions,
            "model": self.model,
            "output_type": output_type,
        }
        if ModelSettings is not None:
            kwargs["model_settings"] = ModelSettings(temperature=self.temperature)

        agent = Agent(**kwargs)
        try:
            result = await asyncio.wait_for(
                Runner.run(agent, input_text, max_turns=self.max_turns),
                timeout=self.timeout_sec,
            )
        except Exception:
            logger.exception(
                "Agent runtime failed (agent=%s, model=%s, timeout_sec=%s, input_chars=%s).",
                name,
                self.model,
                self.timeout_sec,
                input_chars,
            )
            raise
        final_output = getattr(result, "final_output", None)
        elapsed_sec = round(time.perf_counter() - started_at, 3)
        logger.info(
            "Agent runtime succeeded (agent=%s, model=%s, elapsed_sec=%s, input_chars=%s).",
            name,
            self.model,
            elapsed_sec,
            input_chars,
        )
        if isinstance(final_output, output_type):
            return final_output
        return output_type.model_validate(final_output)

    def _configure_openai_credentials(self) -> None:
        key = (self.api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured for agent scoring.")

        # Ensure both SDK-global default key and env var are available.
        os.environ["OPENAI_API_KEY"] = key
        if set_default_openai_key is None:
            return
        try:
            set_default_openai_key(key, use_for_tracing=False)
        except TypeError:
            set_default_openai_key(key)
