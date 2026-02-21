"""Engine class: dispatches to FFI or HTTP backend."""

import os
from typing import Any

from chitin._types import ChitinError, Decision, ExplainResult


class Engine:
    """
    Chitin security engine. Uses the native library if available,
    otherwise the sidecar at CHITIN_SIDECAR_URL.
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Create engine. None = default config (embedded policies only)."""
        self._backend: str = "none"
        self._ffi: Any = None
        self._handle: Any = None
        self._http: Any = None

        # 1. Try FFI
        try:
            from chitin import _ffi
            ffi = _ffi.load_ffi()
            handle = ffi.engine_new(config_path)
            self._ffi = ffi
            self._handle = handle
            self._backend = "ffi"
            return
        except (ChitinError, OSError):
            pass

        # 2. Fall back to HTTP sidecar
        url = os.environ.get("CHITIN_SIDECAR_URL")
        if url:
            from chitin import _http
            self._http = _http._ChitinHTTP(url)
            self._backend = "http"
            return

        raise ChitinError(
            -1,
            "Chitin engine unavailable: native library failed to load and CHITIN_SIDECAR_URL is not set.",
        )

    def _ensure_open(self) -> None:
        if self._backend == "none":
            raise ChitinError(-1, "Engine is closed")

    def ingest(
        self,
        content: str,
        trust_level: int,
        metadata: dict | None = None,
    ) -> int:
        """Record a message. Returns event_id."""
        self._ensure_open()
        if self._backend == "ffi":
            return self._ffi.ingest(self._handle, content, trust_level, metadata)
        return self._http.ingest(content, trust_level, metadata)

    def propose(
        self,
        tool: str,
        params: str,
        agent_id: str | None = None,
        input_sources: list[int] | None = None,
    ) -> Decision:
        """Propose a tool call. Returns Decision (never raises for deny/escalate)."""
        self._ensure_open()
        if self._backend == "ffi":
            return self._ffi.propose(
                self._handle, tool, params, agent_id, input_sources
            )
        return self._http.propose(tool, params, agent_id, input_sources)

    def record_result(
        self,
        tool_call_id: int,
        output: str,
        exit_code: int = 0,
    ) -> int:
        """Record tool result. Returns event_id."""
        self._ensure_open()
        if self._backend == "ffi":
            return self._ffi.record_result(
                self._handle, tool_call_id, output, exit_code
            )
        return self._http.record_result(tool_call_id, output, exit_code)

    def is_traced(self, event_id: int, label: str) -> bool:
        """Check if event traces to a label."""
        self._ensure_open()
        if self._backend == "ffi":
            return self._ffi.is_traced(self._handle, event_id, label)
        return self._http.is_traced(event_id, label)

    def set_label(self, event_id: int, label: str) -> None:
        """Set a trace label on an event and propagate downstream."""
        self._ensure_open()
        if self._backend == "ffi":
            self._ffi.set_label(self._handle, event_id, label)
        else:
            self._http.set_label(event_id, label)

    def explain(self, event_id: int) -> ExplainResult:
        """Get trace chain and explanation for an event."""
        self._ensure_open()
        if self._backend == "ffi":
            return self._ffi.explain(self._handle, event_id)
        return self._http.explain(event_id)

    def register_tool(
        self,
        name: str,
        risk: str = "medium",
        category: str | None = None,
    ) -> None:
        """Register a tool with risk level and optional category."""
        self._ensure_open()
        if self._backend == "ffi":
            self._ffi.register_tool(self._handle, name, risk, category)
        else:
            self._http.register_tool(name, risk, category)

    def close(self) -> None:
        """Destroy engine. Do not use after calling this."""
        if self._backend == "ffi" and self._handle is not None:
            self._ffi.engine_free(self._handle)
            self._handle = None
        self._backend = "none"
        self._ffi = None
        self._http = None

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
