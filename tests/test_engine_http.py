"""Tests for Engine with HTTP backend (requires CHITIN_SIDECAR_URL and running sidecar)."""

import os

import pytest

from chitin import Engine, TrustLevel


@pytest.mark.skipif(
    not os.environ.get("CHITIN_SIDECAR_URL"),
    reason="CHITIN_SIDECAR_URL not set",
)
def test_engine_http_ingest_propose_record() -> None:
    """Round-trip ingest → propose → record_result via HTTP."""
    with Engine() as engine:
        event_id = engine.ingest("user said hi", trust_level=TrustLevel.USER)
        assert isinstance(event_id, int)
        decision = engine.propose(
            tool="noop",
            params="{}",
            input_sources=[event_id],
        )
        assert decision.event_id >= 0
        if decision.allowed:
            event_id2 = engine.record_result(decision.event_id, "ok", exit_code=0)
            assert isinstance(event_id2, int)
