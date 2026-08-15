"""Reliability boundary for the outage-status service."""

from __future__ import annotations

import math
import queue
import threading
import time
from typing import Any

from agent.tools import lookup_outage_status


SAFE_RESULT = {
    "status": "unknown",
    "needs_human": True,
    "message": "Current outage status is unavailable. Contact a human operator.",
}

MAX_ATTEMPTS = 2
MAX_AREA_LENGTH = 100
MAX_MESSAGE_LENGTH = 500
EXPECTED_FIELDS = {"area_code", "status", "needs_human", "message"}

# Status is an identifier rather than free-form model context. The set includes
# the states supported by the local service and common production equivalents.
VALID_STATUSES = frozenset(
    {
        "reported",
        "investigating",
        "confirmed",
        "outage",
        "active",
        "crews_dispatched",
        "restoration_in_progress",
        "planned_outage",
        "restored",
        "resolved",
        "no_outage",
        "unknown",
    }
)


def _safe_result() -> dict[str, Any]:
    """Return a fresh fallback so callers cannot mutate global state."""
    return dict(SAFE_RESULT)


def _is_safe_text(value: Any, maximum_length: int) -> bool:
    """Accept bounded, non-empty text without control characters."""
    if not isinstance(value, str):
        return False
    if not value.strip() or len(value) > maximum_length:
        return False
    return all(character.isprintable() for character in value)


def _valid_area(area_code: Any) -> bool:
    return (
        _is_safe_text(area_code, MAX_AREA_LENGTH)
        and area_code == area_code.strip()
    )


def _validate_payload(payload: Any, requested_area: str) -> dict[str, Any] | None:
    """Return a defensive copy only when the service payload is trustworthy."""
    if not isinstance(payload, dict) or set(payload) != EXPECTED_FIELDS:
        return None

    if payload.get("area_code") != requested_area:
        return None

    status = payload.get("status")
    if type(status) is not str or status not in VALID_STATUSES:
        return None

    needs_human = payload.get("needs_human")
    if type(needs_human) is not bool:
        return None

    message = payload.get("message")
    if not _is_safe_text(message, MAX_MESSAGE_LENGTH):
        return None

    # An unknown result must never be represented as authoritative evidence.
    if status == "unknown" and not needs_human:
        return None

    return {
        "area_code": requested_area,
        "status": status,
        "needs_human": needs_human,
        "message": message,
    }


def _call_once(area_code: str, timeout_seconds: float) -> tuple[str, Any]:
    """Run one call in an isolated daemon thread for at most the given time.

    Python cannot forcibly cancel an arbitrary blocking function. A daemon
    thread lets this request return at its deadline, while using a fresh thread
    for every attempt prevents a timed-out call from occupying a shared worker
    pool and poisoning later requests.
    """
    outcomes: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            outcomes.put_nowait(("ok", lookup_outage_status(area_code)))
        except BaseException as exc:
            # Service failures are data at this boundary; they may be retried.
            try:
                outcomes.put_nowait(("error", exc))
            except queue.Full:
                pass

    worker = threading.Thread(
        target=invoke,
        name="outage-status-lookup",
        daemon=True,
    )
    worker.start()

    try:
        return outcomes.get(timeout=timeout_seconds)
    except queue.Empty:
        return "timeout", None


def run_outage_lookup(area_code: str, timeout_seconds: float) -> dict:
    """Return trustworthy status data within one total response limit.

    A service exception can be retried once if time remains. The deadline is
    shared by all attempts, so retries cannot multiply the configured latency.
    Slow calls are isolated from subsequent requests. Malformed, mismatched, or
    semantically unsafe data is never passed to the model.
    """
    if not _valid_area(area_code):
        return _safe_result()

    if isinstance(timeout_seconds, bool) or not isinstance(
        timeout_seconds, (int, float)
    ):
        return _safe_result()
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        return _safe_result()

    requested_area = area_code.strip()
    deadline = time.monotonic() + float(timeout_seconds)

    for _ in range(MAX_ATTEMPTS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        outcome, value = _call_once(requested_area, remaining)
        if outcome == "timeout":
            break
        if outcome == "error":
            # Retry only transient execution failures, and only within the same
            # original deadline. The next iteration checks remaining time.
            continue

        validated = _validate_payload(value, requested_area)
        if validated is not None:
            return validated

        # Invalid evidence is rejected rather than repeatedly solicited.
        break

    return _safe_result()
