"""HTTP client for the chitin-sidecar. Same semantics as the C ABI."""

import json
import urllib.error
import urllib.request
from typing import Any

from chitin._types import ChitinError, Decision, ExplainResult

# Status codes (match C ABI)
CHITIN_OK = 0
CHITIN_ERR_INVALID = -1
CHITIN_ERR_DENIED = -2
CHITIN_ERR_ESCALATED = -3
CHITIN_ERR_INTERNAL = -4
CHITIN_ERR_NOT_FOUND = -5


class _ChitinHTTP:
    """HTTP backend that talks to chitin-sidecar. Uses CHITIN_SIDECAR_URL."""

    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                if resp.status == 204 or not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = {}
            status = payload.get("status", CHITIN_ERR_INTERNAL)
            msg = payload.get("error", str(e))
            raise ChitinError(status, msg) from e
        except urllib.error.URLError as e:
            raise ChitinError(CHITIN_ERR_INTERNAL, str(e.reason)) from e

    def ingest(
        self,
        content: str,
        trust_level: int,
        metadata: dict | None,
    ) -> int:
        body: dict[str, Any] = {
            "content": content,
            "trust": trust_level,
        }
        if metadata is not None:
            body["metadata"] = metadata
        out = self._post("/ingest", body)
        status = out.get("status", CHITIN_OK)
        if status != CHITIN_OK:
            raise ChitinError(status, out.get("error", "ingest failed"))
        return int(out["event_id"])

    def propose(
        self,
        tool: str,
        params: str,
        agent_id: str | None,
        input_sources: list[int] | None,
    ) -> Decision:
        body: dict[str, Any] = {"tool": tool, "params": params}
        if agent_id is not None:
            body["agent_id"] = agent_id
        if input_sources is not None:
            body["input_sources"] = input_sources
        out = self._post("/propose", body)
        # Sidecar always returns 200 with status in body
        return Decision(
            allowed=bool(out.get("allowed", False)),
            outcome=out.get("outcome", "deny"),
            event_id=int(out["event_id"]),
            rule_id=out.get("rule_id"),
            reason=out.get("reason"),
        )

    def record_result(
        self,
        tool_call_id: int,
        output: str,
        exit_code: int,
    ) -> int:
        out = self._post(
            "/record_result",
            {"tool_call_id": tool_call_id, "output": output, "exit_code": exit_code},
        )
        status = out.get("status", CHITIN_OK)
        if status != CHITIN_OK:
            raise ChitinError(status, out.get("error", "record_result failed"))
        return int(out["event_id"])

    def is_traced(self, event_id: int, label: str) -> bool:
        out = self._post("/is_traced", {"event_id": event_id, "label": label})
        if out.get("status") != CHITIN_OK:
            raise ChitinError(
                out.get("status", CHITIN_ERR_INTERNAL),
                out.get("error", "is_traced failed"),
            )
        return bool(out.get("traced", False))

    def explain(self, event_id: int) -> ExplainResult:
        out = self._post("/explain", {"event_id": event_id})
        status = out.get("status", CHITIN_OK)
        if status != CHITIN_OK:
            raise ChitinError(status, out.get("error", "explain failed"))
        return ExplainResult(
            text=out.get("text") or "",
            trace_chain=out.get("trace_chain") or [],
        )

    def register_tool(
        self,
        name: str,
        risk: str,
        category: str | None,
    ) -> None:
        body: dict[str, Any] = {"tool_name": name, "risk": risk}
        if category is not None:
            body["category"] = category
        self._post("/register_tool", body)
        # 204 No Content → _post returns {}
