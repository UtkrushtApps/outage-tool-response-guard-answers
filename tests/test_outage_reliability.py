import time

import agent.reliability as reliability


AREA = "NORTH-17"
OTHER_AREA = "SOUTH-04"
PAYLOAD = {
    "area_code": AREA,
    "status": "investigating",
    "needs_human": False,
    "message": "Crews are checking the reported outage.",
}
WRONG_AREA_PAYLOAD = {
    "area_code": OTHER_AREA,
    "status": "investigating",
    "needs_human": False,
    "message": "Crews are checking the reported outage.",
}
INCOMPLETE_PAYLOAD = {
    "area_code": AREA,
    "status": "investigating",
}
SAFE_RESULT = {
    "status": "unknown",
    "needs_human": True,
    "message": "Current outage status is unavailable. Contact a human operator.",
}
LIMIT = 0.04
DELAY = 0.30
MAX_ELAPSED = 0.12
ALLOWED_ATTEMPTS = 2
INVALID_AREA = "   "


def test_slow_lookup_returns_safe_result_without_waiting(monkeypatch):
    def slow_lookup(area_code):
        time.sleep(DELAY)
        return PAYLOAD

    monkeypatch.setattr(reliability, "lookup_outage_status", slow_lookup)

    started = time.monotonic()
    result = reliability.run_outage_lookup(AREA, LIMIT)
    elapsed = time.monotonic() - started

    assert result == SAFE_RESULT
    assert elapsed < MAX_ELAPSED


def test_brief_error_can_recover(monkeypatch):
    calls = []

    def unstable_lookup(area_code):
        calls.append(area_code)
        if len(calls) == 1:
            raise ConnectionError("brief status service error")
        return PAYLOAD

    monkeypatch.setattr(reliability, "lookup_outage_status", unstable_lookup)

    result = reliability.run_outage_lookup(AREA, LIMIT)

    assert result == PAYLOAD
    assert len(calls) == ALLOWED_ATTEMPTS


def test_repeated_service_errors_return_safe_result(monkeypatch):
    calls = []

    def failed_lookup(area_code):
        calls.append(area_code)
        raise ConnectionError("status service unavailable")

    monkeypatch.setattr(reliability, "lookup_outage_status", failed_lookup)

    result = reliability.run_outage_lookup(AREA, LIMIT)

    assert result == SAFE_RESULT
    assert len(calls) == ALLOWED_ATTEMPTS


def test_incomplete_result_is_not_trusted(monkeypatch):
    monkeypatch.setattr(
        reliability,
        "lookup_outage_status",
        lambda area_code: INCOMPLETE_PAYLOAD,
    )

    result = reliability.run_outage_lookup(AREA, LIMIT)

    assert result == SAFE_RESULT


def test_result_for_another_area_is_not_trusted(monkeypatch):
    monkeypatch.setattr(
        reliability,
        "lookup_outage_status",
        lambda area_code: WRONG_AREA_PAYLOAD,
    )

    result = reliability.run_outage_lookup(AREA, LIMIT)

    assert result == SAFE_RESULT


def test_invalid_area_does_not_reach_service(monkeypatch):
    called = False

    def tracked_lookup(area_code):
        nonlocal called
        called = True
        return PAYLOAD

    monkeypatch.setattr(reliability, "lookup_outage_status", tracked_lookup)

    result = reliability.run_outage_lookup(INVALID_AREA, LIMIT)

    assert result == SAFE_RESULT
    assert not called


def test_available_status_is_preserved(monkeypatch):
    monkeypatch.setattr(
        reliability,
        "lookup_outage_status",
        lambda area_code: PAYLOAD,
    )

    result = reliability.run_outage_lookup(AREA, LIMIT)

    assert result == PAYLOAD
