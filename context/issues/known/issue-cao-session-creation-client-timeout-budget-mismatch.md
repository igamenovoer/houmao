# Issue: CAO Session Creation Times Out — Client Budget vs. Server-Side Synchronous Init

## Priority
P1 — The detached session launch path is unusable for both `claude_code` and `codex` providers. The demo's full pipeline and any headless automation that creates sessions through `houmao-server` are blocked.

## Status
Open as of 2026-03-25.

## Summary

Creating a CAO-compatible session through `POST /cao/sessions` fails with a connection timeout before the server finishes initializing the terminal. The client enforces a flat 15-second HTTP timeout, but the server-side `create_session()` path performs a chain of synchronous waits (shell readiness, optional provider warmup sleep, provider input-readiness polling) that can easily exceed that budget even on a healthy system.

The timeout is provider-agnostic: it reproduced for both `claude_code` and `codex` during automatic testing on 2026-03-25.

## What Is Wrong Today

The `CaoRestClient` uses a single `timeout_seconds = 15.0` for every HTTP call, including session creation. On the server side, `CompatibilityControlCore.create_session()` blocks the HTTP response until `_initialize_terminal()` completes, which includes:

| Server-side step | Max budget | Source |
|---|---|---|
| `wait_for_shell()` | 10 s | `tmux_controller.py:191` |
| Codex warmup sleep | 2 s (fixed, codex only) | `core.py:485` |
| `wait_until_ready()` | 45 s | `provider_adapters.py:81` |
| **Aggregate worst case** | **~57 s** | |

The client's 15 s wall fires well before the server finishes, regardless of whether the agent would have booted successfully given enough time.

## Evidence

### 1. Automatic test reproduction (2026-03-25)

Three automatic test runs all failed at the same point:

- `claude_code` provider on default output root — timeout during detached launch.
- `codex` provider on unique output root — same timeout during detached launch.
- `codex` provider on default output root — blocked by stale worktree from first failure (secondary issue).

Error messages:

```text
Pair-managed detached TUI launch failed via houmao-mgr cao launch --headless
Failed to connect to houmao-server ... Connection failed after 15.0s: timed out
```

Primary test artifacts:

- `.agent-automation/hacktest/houmao-server-interactive-full-pipeline-demo/outputs/case-start-inspect-stop/result.json`
- `.agent-automation/hacktest/houmao-server-interactive-full-pipeline-demo/outputs/case-start-inspect-stop-codex-control/result.json`

Full findings document:

- `.agent-automation/hacktest/houmao-server-interactive-full-pipeline-demo/issues/automatic-test-20260325.md`

### 2. Client timeout is flat across all endpoints

`CaoRestClient.__init__()` sets one timeout for all HTTP calls:

- `src/houmao/cao/rest_client.py:68` — `timeout_seconds: float = 15.0`
- `src/houmao/cao/rest_client.py:312` — `urlopen(req, timeout=self.timeout_seconds)`

Health checks, session listing, and session creation all share the same 15 s budget.

### 3. Server-side create_session is fully synchronous

`CompatibilityControlCore.create_session()` calls `_initialize_terminal()` inline before returning the HTTP response:

- `src/houmao/server/control_core/core.py:121–190` — `create_session()` blocks on `_initialize_terminal()` at line 169.
- `src/houmao/server/control_core/core.py:459–504` — `_initialize_terminal()` runs `wait_for_shell()`, optional codex sleep, provider command send, and `wait_until_ready()` sequentially.

### 4. Server-side wait chain has generous individual budgets

- `wait_for_shell()`: up to 10 s, polling every 0.5 s — `src/houmao/server/control_core/tmux_controller.py:186–205`
- Codex warmup: fixed 2 s `time.sleep(2.0)` — `src/houmao/server/control_core/core.py:485`
- `wait_until_ready()`: up to 45 s, polling every 1.0 s — `src/houmao/server/control_core/provider_adapters.py:75–97`

Each timeout is individually reasonable, but their sum far exceeds the client's budget.

## Root Cause

The design assumes that `create_session()` completes fast enough for a generic HTTP timeout, but the actual server-side work includes waiting for a real CLI agent process to boot inside tmux. Agent boot time (loading configs, initializing MCP servers, downloading assets) is inherently variable and can easily exceed 15 s even when nothing is broken.

The mismatch has two contributing factors:

1. **Single flat timeout**: `CaoRestClient` does not distinguish between lightweight queries (health, list) and heavyweight mutations (session creation).
2. **Synchronous-to-completion response model**: The server holds the HTTP response until the agent is input-ready. There is no intermediate "creating" state the client can poll.

## Secondary Impact

The timeout failure triggers two additional issues documented in the automatic test findings:

### Stale git worktree registration after failed startup

The demo provisions a git worktree before the launch call. When launch times out, the worktree directory is cleaned up but the git worktree registration is not pruned. Subsequent reruns on the same output root fail with `missing but already registered worktree`.

- Worktree provisioning: `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/commands.py:485`
- No worktree unregister/prune in failure cleanup path.

### Orphaned tmux sessions after failed startup with auto-generated names

The server creates the tmux session (step 3 of `create_session()` succeeds) before the timeout fires during `_initialize_terminal()`. Because the demo discovers the auto-generated session name only after a successful launch, `actual_session_name` stays `None` and `_best_effort_kill_tmux_session()` cannot target the orphan.

- Cleanup code: `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/commands.py:87`
- Session name discovery requires `_wait_for_launched_session_name()` to succeed first.

## Current Workaround

No reliable workaround exists for headless/automatic testing. The launch path is blocked.

For manual interactive use, operators can retry with `--attach` mode (which bypasses the detached launch timeout) or increase the client timeout by patching `rest_client.py` locally.

## Desired Direction

### Option A: Raise the client timeout for session creation (quick fix)

Allow `create_session()` to pass a longer timeout (e.g., 60–90 s) to `CaoRestClient`, or add a `create_timeout_seconds` parameter to the client constructor. This unblocks testing without changing the server architecture.

Downside: the client still blocks for the full agent boot time, and the timeout must be tuned conservatively.

### Option B: Make session creation asynchronous (proper fix)

The server returns immediately with session info in a "creating" state. Terminal initialization runs in a background thread. The client polls `GET /cao/sessions/{name}` until the status transitions to "ready" (or a terminal error state).

Benefits:

- Client controls its own polling cadence and total timeout.
- Server knows the session name from the start and can clean up on failure, fixing the orphaned-tmux-session problem.
- The HTTP timeout becomes irrelevant for session creation latency.

Downside: requires changes across the server control core, the REST API layer, and the client.

## Acceptance Criteria

1. A `codex` or `claude_code` session can be created through the detached launch path without timing out on a healthy system.
2. The automatic test case `case-start-inspect-stop` passes end-to-end for at least one provider.
3. Failed startups do not leave orphaned tmux sessions or stale git worktree registrations.
4. The chosen timeout or polling strategy is documented in the client or server API contract.

## Connections

- Automatic test findings: `.agent-automation/hacktest/houmao-server-interactive-full-pipeline-demo/issues/automatic-test-20260325.md`
- Related demo repair change: `openspec/changes/repair-houmao-server-interactive-demo-pack/`
- Related resolved issue: `context/issues/resolved/issue-cao-interactive-full-pipeline-demo-default-run-requires-workarounds.md`
