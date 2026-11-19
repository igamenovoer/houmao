# Persistent DSH ACP Provider

The provider initializes ACP protocol 1 and binds one exact native session before reporting readiness. An explicit resume requires DSH's negotiated resume capability and a matching workspace/session. The native process keeps its stdio connection across managed prompts. Houmao sends `session/close` when stopping the owner and reaps that captured process tree.

The local source at `39163dd30f703a79079e2d2446545cff3c453738` shows that ACP calls `agent.followup` before inbox admission. The companion rechecks the current service incarnation, owner and worker birth identities, shared operation reservation, and the caller's revocable permission at that boundary. It writes handoff evidence after the inbox insertion. The correlated ACP reply and the operation's exact journal terminal record must agree before completion. Raw ACP and stderr remain private.

ACP `session/update` carries a session ID alone. The provider drains updates continuously and reads semantic text from the exact operation's flushed native journal interval. A late update from the same session has no independent authority to settle a different request. Houmao declines remaining interactive permission requests for the bound prompt through the native reject or cancel option. Native permission defaults and hard denials remain in force. Reverse-request handling has a fixed capacity and fails the connection if that capacity is exceeded.

Temporary settings use the native advertised opaque values. The owner holds admission through apply, prompt settlement, and verified restoration. A timed-out setting whose wire operation is still outstanding leaves the service unavailable. Houmao avoids issuing a conflicting restore while an unresolved setting might still mutate the session.

The service manifest publishes a native session in `backend_state` and omits the headless state compartment. Accounting binds to that session and attributes journal rows to the distinct request's admitted input and worker birth. Native stderr and unbound ACP updates do not become accounting records.

## Controlled Verification

- **67 passed** across persistent adapter, ACP connection, historical ACP driver, and DSH journal unit suites. Cases include interleaved permission requests and responses, stale cancellation, native arm revocation, cancelled prompt settings, a rejected setter, unresolved setter timeout, and restore failure. Ruff, scoped strict mypy, JavaScript syntax, and `git diff --check` passed.
- **1 passed in 10.70 seconds** with DSH `0.2.2-rc.3` and a controlled local Messages endpoint. Independent manager calls used `controlled` and a temporary `controlled-alternate`. The signed gateway's next prompt used `controlled`, confirming restoration. A fourth signed gateway operation held the provider open and a separate manager interrupt settled that exact operation. All requests kept the same native session, service incarnation, process ID and birth token. Each completed request charged 16 synthetic tokens exactly once. The captured native process was gone after stop.
- The first real model-switch case used an 8192-token context and hit the native 65,536-token compaction headroom check. DSH returned a correlated error and acknowledged restoration of the original model. The passing case uses the same 262144-token context size as the self-hosted fixture and exercises the actual model transition and following restored prompt.

The controlled verification used an isolated tmux socket and synthetic credentials. The separate live fixture uses self-hosted Qwen 3.8.
