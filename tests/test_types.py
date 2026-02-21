"""Tests for public types."""

import pytest

from chitin import ChitinError, Decision, ExplainResult, TrustLevel


def test_trust_level_constants() -> None:
    assert TrustLevel.SYSTEM == 0
    assert TrustLevel.OPERATOR == 1
    assert TrustLevel.USER == 2
    assert TrustLevel.EXTERNAL == 3
    assert TrustLevel.UNKNOWN == 4


def test_decision_dataclass() -> None:
    d = Decision(
        allowed=True,
        outcome="allow",
        event_id=1,
        rule_id=None,
        reason=None,
    )
    assert d.allowed is True
    assert d.outcome == "allow"
    assert d.event_id == 1


def test_explain_result_dataclass() -> None:
    e = ExplainResult(text="foo", trace_chain=[1, 2, 3])
    assert e.text == "foo"
    assert e.trace_chain == [1, 2, 3]


def test_chitin_error() -> None:
    err = ChitinError(-1, "invalid")
    assert err.status == -1
    assert err.message == "invalid"
    assert "[-1]" in str(err)
