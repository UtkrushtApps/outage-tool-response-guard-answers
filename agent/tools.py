"""Local outage-status business service and its model tool contract."""

import os
import time


OUTAGE_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_outage_status",
        "description": "Get the current utility outage status for a service area.",
        "parameters": {
            "type": "object",
            "properties": {
                "area_code": {
                    "type": "string",
                    "description": "The service area printed on the utility account.",
                }
            },
            "required": ["area_code"],
            "additionalProperties": False,
        },
    },
}


def lookup_outage_status(area_code: str) -> dict:
    """Simulate the existing remote status service used by the agent."""
    delay_ms = int(os.getenv("OUTAGE_TOOL_DELAY_MS", "1200"))
    time.sleep(max(delay_ms, 0) / 1000)

    return {
        "area_code": area_code,
        "status": "investigating",
        "needs_human": False,
        "message": "Crews are checking the reported outage.",
    }
