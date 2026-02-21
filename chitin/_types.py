"""Public types for the Chitin Python API."""

from dataclasses import dataclass


class TrustLevel:
    """Trust level for ingested content."""

    SYSTEM = 0
    OPERATOR = 1
    USER = 2
    EXTERNAL = 3
    UNKNOWN = 4


@dataclass
class Decision:
    """Result of proposing a tool call."""

    allowed: bool
    outcome: str  # "allow" | "deny" | "escalate"
    event_id: int
    rule_id: str | None  # which policy rule fired
    reason: str | None  # human-readable reason


@dataclass
class ExplainResult:
    """Result of explaining an event's trace."""

    text: str  # human-readable explanation
    trace_chain: list  # structured trace data (parsed from JSON)


class ChitinError(Exception):
    """Raised when an engine call fails (other than deny/escalate from propose)."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"[{status}] {message}")
