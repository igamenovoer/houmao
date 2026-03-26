## Context

Runtime-owned managed gateways already have two internal execution modes: a detached subprocess path and a same-session tmux auxiliary-window path. The tmux-window path is mature enough to launch the gateway in the foreground, tee its console output into the stable gateway log, persist the tmux execution handle, and shut the gateway down by killing only the auxiliary window rather than the whole tmux session.

Today that same-session path is only enabled for pair-managed `houmao_server_rest` sessions. `houmao-mgr`-launched tmux-backed sessions still attach gateways through the detached-process branch, so operators cannot watch gateway logs directly in the managed session even though the tmux window machinery already exists. The change is therefore not about building a new gateway runner; it is about exposing and normalizing the existing foreground tmux-window path for runtime-owned managed sessions while preserving the invariant that window `0` remains the agent surface.

## Goals / Non-Goals

**Goals:**

- Provide an explicit foreground gateway mode for `houmao-mgr agents gateway attach`.
- Keep tmux window `0` reserved for the agent surface and require the foreground gateway to live in tmux window `>=1`.
- Reuse the existing `tmux_auxiliary_window` runtime machinery instead of inventing a parallel launcher.
- Surface execution-mode and tmux-window metadata through gateway status so operators can discover the foreground gateway surface directly.
- Preserve durable gateway logs and deterministic detach/recovery behavior in foreground mode.

**Non-Goals:**

- Making foreground mode the default for every gateway attach in this change.
- Changing the agent surface contract so the gateway becomes the primary attach target.
- Reworking gateway request semantics, TUI tracking, or gateway log storage format.
- Introducing a second console-streaming mechanism outside tmux for runtime-owned gateways.

## Decisions

### 1. Public CLI uses an explicit `--foreground` attach option while reusing the existing internal execution mode

`houmao-mgr agents gateway attach` will gain an explicit `--foreground` option. That public option will map to the existing internal `tmux_auxiliary_window` execution mode rather than introducing a new third execution-mode enum.

The detached-process path remains the initial default for runtime-owned sessions in this change. Pair-managed `houmao_server_rest` sessions already using same-session tmux-window gateway execution can treat `--foreground` as redundant but valid.

This keeps the operator surface simple while minimizing internal churn: the runtime already knows how to record, validate, and stop `tmux_auxiliary_window` instances.

**Alternatives considered:**

- Make foreground tmux-window mode the immediate default for all `houmao-mgr` gateway attaches. Rejected for this change because it silently changes attach behavior and tmux topology for existing operator workflows.
- Introduce a new internal enum such as `foreground_tmux_window`. Rejected because the existing `tmux_auxiliary_window` mode already encodes the needed lifecycle semantics.

### 2. Foreground gateways for runtime-owned tmux-backed sessions reuse the same-session tmux-window lifecycle

Runtime-owned tmux-backed sessions launched through `houmao-mgr` will become eligible to use the same-session tmux auxiliary-window path when foreground mode is requested.

In that mode:

- the gateway runs in the managed session's tmux session,
- the window name remains `gateway`,
- the actual tmux window index must be `>=1`,
- window `0` remains reserved for the agent surface, and
- liveness, readiness, detach, and crash cleanup use the authoritative auxiliary tmux pane plus gateway health responses rather than a detached subprocess handle.

This extends the same operational model already used for pair-managed `houmao_server_rest` sessions instead of creating a runtime-owned special case.

**Alternatives considered:**

- Start a second detached process and tail its logs into a tmux pane. Rejected because it creates two execution surfaces for one gateway instance and weakens shutdown/liveness authority.
- Run the gateway inside pane splits on window `0`. Rejected because the contract explicitly reserves window `0` for the agent surface.

### 3. Desired gateway execution mode is persisted alongside desired host and port

Gateway desired-config will persist the preferred execution mode in addition to desired host and desired port. Explicit CLI input still takes precedence, but persisted desired-config lets later attach or restart flows reuse the same operator-selected gateway surface mode instead of falling back to detached execution unexpectedly.

This matches the existing desired listener contract and keeps attach behavior stable across reattach and runtime recovery.

**Alternatives considered:**

- Treat foreground mode as a one-shot transient flag only. Rejected because later attach/restart would then silently change gateway topology unless the operator remembered to repeat the flag every time.
- Persist the mode only in the live current-instance record. Rejected because current-instance is ephemeral and disappears exactly when reattach needs a durable preference source.

### 4. Gateway status becomes foreground-aware

Gateway status will expose execution-mode metadata and, when the gateway is running in `tmux_auxiliary_window` mode, the authoritative tmux execution handle needed for operator discovery and runtime lifecycle management.

At minimum the published status should include:

- `execution_mode`
- `gateway_tmux_window_id` when present
- `gateway_tmux_window_index` when present
- optionally `gateway_tmux_pane_id`

`houmao-mgr agents gateway attach` and `houmao-mgr agents gateway status` can then return the concrete tmux window index the operator should inspect for live gateway logs.

**Alternatives considered:**

- Leave tmux-window details only in internal runtime artifacts. Rejected because a foreground mode is not operable if the operator cannot discover which tmux window owns it.
- Surface only a boolean `foreground=true`. Rejected because that still leaves the operator guessing which window to inspect.

## Risks / Trade-offs

- **Foreground mode adds visible tmux topology to local sessions** → Keep it explicit behind `--foreground` first, and preserve detached mode as the initial default for runtime-owned attach.
- **Persisted execution-mode preference can surprise callers after old attaches** → Use clear precedence rules: explicit CLI flag first, then persisted desired-config, then backend default.
- **Multiple auxiliary windows may already exist in a session** → Keep the hard invariant that the gateway window index must not be `0`, and rely on the authoritative current-instance record rather than heuristic discovery over arbitrary auxiliary windows.
- **Operators may assume window `1` exactly instead of `>=1`** → Status output must return the actual window index and docs/help text must say `>=1`, not `1`.

## Migration Plan

1. Extend gateway desired-config and status models to carry execution-mode and tmux-window metadata.
2. Add `--foreground` to `houmao-mgr agents gateway attach` and thread that preference into runtime attach.
3. Generalize same-session tmux auxiliary-window attach from pair-managed `houmao_server_rest` to runtime-owned tmux-backed managed sessions when foreground mode is requested.
4. Update attach/status output and help text so operators can discover the foreground gateway window directly.
5. Add focused tests for foreground attach, status metadata, window-`0` protection, and detach cleanup of the auxiliary window.

Rollback is straightforward: stop honoring foreground mode for runtime-owned sessions and fall back to detached-process attach, while leaving durable log storage and current-instance cleanup behavior intact.

## Open Questions

- Should runtime-owned tmux-backed gateway attach eventually default to foreground mode after the explicit mode proves stable?
- Do we want to expose `gateway_tmux_pane_id` publicly immediately, or keep the first operator contract at window-level metadata only?
