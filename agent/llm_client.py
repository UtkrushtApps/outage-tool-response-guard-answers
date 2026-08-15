"""Real OpenAI-compatible model client for the outage assistant."""

from typing import Any

from openai import OpenAI

from agent.config import AgentConfig


class ModelClient:
    """Call the configured provider without an offline replacement."""

    def __init__(self, config: AgentConfig) -> None:
        if not config.api_key:
            raise RuntimeError("A provider key is required to create ModelClient")

        options: dict[str, Any] = {
            "api_key": config.api_key,
            "timeout": config.model_timeout_seconds,
        }
        if config.base_url:
            options["base_url"] = config.base_url

        self._client = OpenAI(**options)
        self._model = config.model

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Return one message from the configured real chat model."""
        request: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**request)
        return response.choices[0].message
