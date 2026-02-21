# chitin-engine-lib

Python bindings for the [Chitin](https://github.com/datagoboom/chitin-engine) security engine.

This package is the backend for [Chitin](https://github.com/datagoboom/chitin) — the agent runtime uses it internally for policy evaluation, trace tracking, and tool-call gating. You don't need to install this directly if you're using the Chitin agent.

If you're building your own agent or integrating Chitin's security engine into an existing system, this is the right package. It gives you direct access to the engine with no opinions about how you orchestrate tools or talk to LLMs.

## Install

```bash
pip install chitin-engine-lib
```

Platform wheels bundle the shared library for Linux (x86_64, aarch64), macOS (x86_64, arm64), and Windows (x86_64). If you install the pure wheel, point `CHITIN_LIB_PATH` at the shared library or set `CHITIN_SIDECAR_URL` for the HTTP fallback.

## Usage

```python
from chitin import Engine, TrustLevel

engine = Engine()

event_id = engine.ingest("user input here", trust_level=TrustLevel.USER)

decision = engine.propose(
    tool="http_fetch",
    params='{"url": "https://example.com"}',
    input_sources=[event_id]
)

if decision.allowed:
    result = call_your_tool()
    engine.record_result(decision.event_id, result, exit_code=0)
else:
    print(decision.outcome)  # "deny" or "escalate"
    print(decision.reason)   # which policy fired and why
```

## API

| Method | What it does |
|--------|-------------|
| `Engine(config_path=None)` | Create an engine. `None` loads embedded default policies. |
| `engine.ingest(content, trust_level, metadata=None)` | Record a message. Returns `event_id`. |
| `engine.propose(tool, params, agent_id=None, input_sources=None)` | Check a tool call against policies. Returns `Decision`. |
| `engine.record_result(tool_call_id, output, exit_code=0)` | Record what a tool returned. Returns `event_id`. |
| `engine.is_traced(event_id, label)` | Check if an event traces to a trust label. |
| `engine.explain(event_id)` | Get the trace chain for an event. |
| `engine.register_tool(name, risk="medium", category=None)` | Register a tool's risk level and category. |
| `engine.close()` | Destroy the engine. Also works as a context manager. |

`Decision` has: `allowed` (bool), `outcome` ("allow" / "deny" / "escalate"), `event_id`, `rule_id`, `reason`.

## Links

- Chitin agent: https://github.com/datagoboom/chitin
- Chitin engine (Rust): https://github.com/datagoboom/chitin-engine
- Engine C ABI reference: [`chitin.h`](https://github.com/datagoboom/chitin-engine/blob/main/crates/chitin-ffi/include/chitin.h)

## License

Apache 2.0
