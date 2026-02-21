"""ctypes bindings to the chitin C ABI (chitin.h)."""

import ctypes
from ctypes import POINTER, c_char_p, c_int32, c_uint64, c_void_p, c_size_t

from chitin._resolve import resolve_chitin_lib, _load_lib_error_message
from chitin._types import ChitinError, Decision, ExplainResult

# Status codes from chitin.h
CHITIN_OK = 0
CHITIN_ERR_INVALID = -1
CHITIN_ERR_DENIED = -2
CHITIN_ERR_ESCALATED = -3
CHITIN_ERR_INTERNAL = -4
CHITIN_ERR_NOT_FOUND = -5


def _to_buf(s: str | None) -> tuple[bytes | None, int]:
    if s is None:
        return None, 0
    b = s.encode("utf-8")
    return b, len(b)


def _load_lib() -> ctypes.CDLL:
    path = resolve_chitin_lib()
    try:
        return ctypes.CDLL(path)
    except OSError as e:
        raise OSError(_load_lib_error_message()) from e


class _ChitinFFI:
    """Holds the loaded library and wraps C ABI calls."""

    def __init__(self) -> None:
        self._lib = _load_lib()
        self._setup_signatures()

    def _setup_signatures(self) -> None:
        lib = self._lib

        # chitin_engine_t chitin_engine_new(const char* config_path, size_t config_path_len);
        lib.chitin_engine_new.argtypes = [c_char_p, c_size_t]
        lib.chitin_engine_new.restype = c_void_p

        # void chitin_engine_free(chitin_engine_t engine);
        lib.chitin_engine_free.argtypes = [c_void_p]
        lib.chitin_engine_free.restype = None

        # chitin_status_t chitin_ingest(...);
        lib.chitin_ingest.argtypes = [
            c_void_p,
            c_char_p,
            c_size_t,
            c_int32,
            c_char_p,
            c_size_t,
            POINTER(c_uint64),
        ]
        lib.chitin_ingest.restype = c_int32

        # chitin_status_t chitin_propose(...);
        lib.chitin_propose.argtypes = [
            c_void_p,
            c_char_p,
            c_size_t,
            c_char_p,
            c_size_t,
            c_char_p,
            c_size_t,
            POINTER(c_uint64),
            c_size_t,
            POINTER(c_uint64),
        ]
        lib.chitin_propose.restype = c_int32

        # chitin_status_t chitin_record_result(...);
        lib.chitin_record_result.argtypes = [
            c_void_p,
            c_uint64,
            c_char_p,
            c_size_t,
            c_int32,
            POINTER(c_uint64),
        ]
        lib.chitin_record_result.restype = c_int32

        # chitin_status_t chitin_is_traced(...);
        lib.chitin_is_traced.argtypes = [
            c_void_p,
            c_uint64,
            c_char_p,
            c_size_t,
            POINTER(c_int32),
        ]
        lib.chitin_is_traced.restype = c_int32

        # chitin_status_t chitin_explain(...);
        lib.chitin_explain.argtypes = [
            c_void_p,
            c_uint64,
            POINTER(c_char_p),
            POINTER(c_size_t),
        ]
        lib.chitin_explain.restype = c_int32

        # chitin_status_t chitin_last_error(char** out_json, size_t* out_json_len);
        lib.chitin_last_error.argtypes = [POINTER(c_char_p), POINTER(c_size_t)]
        lib.chitin_last_error.restype = c_int32

        # void chitin_free_string(char* ptr, size_t len);
        lib.chitin_free_string.argtypes = [c_char_p, c_size_t]
        lib.chitin_free_string.restype = None

        # chitin_status_t chitin_register_tool(...);
        lib.chitin_register_tool.argtypes = [
            c_void_p,
            c_char_p,
            c_size_t,
            c_char_p,
            c_size_t,
        ]
        lib.chitin_register_tool.restype = c_int32

    def _last_error(self) -> str:
        out_json = c_char_p()
        out_len = c_size_t(0)
        st = self._lib.chitin_last_error(ctypes.byref(out_json), ctypes.byref(out_len))
        if st == CHITIN_ERR_NOT_FOUND or out_json.value is None:
            return "unknown error"
        try:
            raw = ctypes.string_at(out_json.value, out_len.value)
            return raw.decode("utf-8")
        finally:
            self._lib.chitin_free_string(out_json.value, out_len.value)

    def engine_new(self, config_path: str | None) -> c_void_p:
        path_buf, path_len = _to_buf(config_path)
        engine = self._lib.chitin_engine_new(path_buf, path_len or 0)
        if engine is None:
            raise ChitinError(CHITIN_ERR_INTERNAL, self._last_error())
        return engine

    def engine_free(self, engine: c_void_p) -> None:
        self._lib.chitin_engine_free(engine)

    def ingest(
        self,
        engine: c_void_p,
        content: str,
        trust_level: int,
        metadata: dict | None,
    ) -> int:
        content_buf, content_len = _to_buf(content)
        meta_str = None
        meta_len = 0
        if metadata is not None:
            import json
            meta_str = json.dumps(metadata)
            meta_buf, meta_len = _to_buf(meta_str)
        else:
            meta_buf = None
        out_id = c_uint64(0)
        st = self._lib.chitin_ingest(
            engine,
            content_buf,
            content_len,
            c_int32(trust_level),
            meta_buf,
            meta_len,
            ctypes.byref(out_id),
        )
        if st != CHITIN_OK:
            raise ChitinError(st, self._last_error())
        return out_id.value

    def propose(
        self,
        engine: c_void_p,
        tool: str,
        params: str,
        agent_id: str | None,
        input_sources: list[int] | None,
    ) -> Decision:
        tool_buf, tool_len = _to_buf(tool)
        params_buf, params_len = _to_buf(params)
        agent_buf, agent_len = _to_buf(agent_id)
        sources_arr = None
        sources_len = 0
        if input_sources:
            arr_type = c_uint64 * len(input_sources)
            sources_arr = arr_type(*input_sources)
            sources_len = len(input_sources)
        out_id = c_uint64(0)
        st = self._lib.chitin_propose(
            engine,
            tool_buf,
            tool_len,
            params_buf,
            params_len,
            agent_buf,
            agent_len,
            sources_arr,
            sources_len,
            ctypes.byref(out_id),
        )
        if st == CHITIN_OK:
            return Decision(allowed=True, outcome="allow", event_id=out_id.value, rule_id=None, reason=None)
        if st in (CHITIN_ERR_DENIED, CHITIN_ERR_ESCALATED):
            err_json = self._last_error()
            import json
            try:
                obj = json.loads(err_json)
                rule_id = obj.get("rule_id")
                reason = obj.get("reason", "")
            except Exception:
                rule_id = None
                reason = err_json
            outcome = "deny" if st == CHITIN_ERR_DENIED else "escalate"
            return Decision(
                allowed=False,
                outcome=outcome,
                event_id=out_id.value,
                rule_id=rule_id,
                reason=reason,
            )
        raise ChitinError(st, self._last_error())

    def record_result(
        self,
        engine: c_void_p,
        tool_call_id: int,
        output: str,
        exit_code: int,
    ) -> int:
        out_buf, out_len = _to_buf(output)
        out_id = c_uint64(0)
        st = self._lib.chitin_record_result(
            engine,
            c_uint64(tool_call_id),
            out_buf,
            out_len,
            c_int32(exit_code),
            ctypes.byref(out_id),
        )
        if st != CHITIN_OK:
            raise ChitinError(st, self._last_error())
        return out_id.value

    def is_traced(self, engine: c_void_p, event_id: int, label: str) -> bool:
        label_buf, label_len = _to_buf(label)
        out_result = c_int32(0)
        st = self._lib.chitin_is_traced(
            engine,
            c_uint64(event_id),
            label_buf,
            label_len,
            ctypes.byref(out_result),
        )
        if st != CHITIN_OK:
            raise ChitinError(st, self._last_error())
        return out_result.value != 0

    def explain(self, engine: c_void_p, event_id: int) -> ExplainResult:
        out_json = c_char_p()
        out_len = c_size_t(0)
        st = self._lib.chitin_explain(
            engine,
            c_uint64(event_id),
            ctypes.byref(out_json),
            ctypes.byref(out_len),
        )
        if st != CHITIN_OK:
            raise ChitinError(st, self._last_error())
        if out_json.value is None or out_len.value == 0:
            return ExplainResult(text="", trace_chain=[])
        try:
            raw = ctypes.string_at(out_json.value, out_len.value)
            text = raw.decode("utf-8")
        finally:
            self._lib.chitin_free_string(out_json.value, out_len.value)
        import json
        try:
            obj = json.loads(text)
            return ExplainResult(
                text=obj.get("text", ""),
                trace_chain=obj.get("trace_chain", []),
            )
        except Exception:
            return ExplainResult(text=text, trace_chain=[])

    def register_tool(
        self,
        engine: c_void_p,
        name: str,
        risk: str,
        category: str | None,
    ) -> None:
        import json
        config = {"risk": risk}
        if category is not None:
            config["category"] = category
        config_json = json.dumps(config)
        name_buf, name_len = _to_buf(name)
        config_buf, config_len = _to_buf(config_json)
        st = self._lib.chitin_register_tool(
            engine,
            name_buf,
            name_len,
            config_buf,
            config_len,
        )
        if st != CHITIN_OK:
            raise ChitinError(st, self._last_error())


def load_ffi() -> _ChitinFFI:
    """Load the chitin library and return the FFI wrapper. Raises ChitinError if load fails."""
    return _ChitinFFI()
