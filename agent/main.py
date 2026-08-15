"""Command-line agent loop for customer outage questions."""

import json
from typing import Any

from agent.config import load_config
from agent.llm_client import ModelClient
from agent.reliability import run_outage_lookup
from agent.tools import OUTAGE_STATUS_TOOL


SYSTEM_PROMPT = """You are a utilities outage assistant.
Use the outage-status tool before making any claim about current outage status.
Treat tool output as the only source of live outage information.
If the tool reports an unknown status or asks for human help, say that current
status is unavailable and direct the customer to a human operator.
Keep the final answer short and do not invent restoration times.
Prompt version: outage-assistant-v2
"""


FALLBACK_RESULT = {
    "status": "unknown",
    "needs_human": True,
    "message": "Current outage status is unavailable. Contact a human operator.",
}


def _tool_result(message: Any, timeout_seconds: float) -> tuple[str, dict]:
    """Validate a model tool request and execute the guarded lookup."""
    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return "missing-tool-call", dict(FALLBACK_RESULT)

    tool_call = tool_calls[0]
    tool_call_id = getattr(tool_call, "id", "missing-tool-call")
    function = getattr(tool_call, "function", None)
    if function is None or getattr(function, "name", None) != "get_outage_status":
        return tool_call_id, dict(FALLBACK_RESULT)

    try:
        arguments = json.loads(function.arguments)
        if not isinstance(arguments, dict) or set(arguments) != {"area_code"}:
            raise ValueError("unexpected tool arguments")
        area_code = arguments["area_code"]
        if not isinstance(area_code, str) or not area_code.strip():
            raise ValueError("area_code must be a non-empty string")
    except (json.JSONDecodeError, AttributeError, KeyError, ValueError, TypeError):
        return tool_call_id, dict(FALLBACK_RESULT)

    return tool_call_id, run_outage_lookup(area_code.strip(), timeout_seconds)


def answer_outage_question(question: str) -> str:
    """Run one real model and tool interaction for an outage question."""
    config = load_config(require_key=True)
    client = ModelClient(config)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    first_message = client.complete(messages, tools=[OUTAGE_STATUS_TOOL])
    if not getattr(first_message, "tool_calls", None):
        return first_message.content or "Please contact a human operator."

    tool_call_id, result = _tool_result(
        first_message, config.tool_timeout_seconds
    )
    messages.append(first_message.model_dump(exclude_none=True))
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(result),
        }
    )
    final_message = client.complete(messages)
    return final_message.content or "Please contact a human operator."


def main() -> None:
    question = input("Describe the outage and include your service area: ").strip()
    if not question:
        raise SystemExit("A customer question is required.")
    print(answer_outage_question(question))


if __name__ == "__main__":
    main()
