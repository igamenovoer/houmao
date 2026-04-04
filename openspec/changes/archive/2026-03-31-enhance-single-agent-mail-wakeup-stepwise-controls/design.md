## Context

The supported `single-agent-mail-wakeup` demo currently exposes a minimal stepwise surface: `start`, `manual-send`, `inspect`, `verify`, and `stop`. That is enough to prove the flow, but not enough to make the demo feel like an operator-facing interactive tutorial. In practice, users want to:

- re-attach to the live agent session after `start`,
- watch the gateway console without entering tmux manually,
- send additional mailbox work into the running demo,
- manage the gateway mail notifier while the demo is live.

The current implementation already has two useful building blocks:

- the demo persists enough state to resolve the current tool lane and session root,
- the underlying gateway attach surface already supports running the gateway in an auxiliary tmux window with authoritative window metadata.

At the same time, the current demo does not persist a `gateway.stdout` file. The stable gateway artifacts today are structured state and event files under the session's `gateway/` directory, not a demo-owned console log.

## Goals / Non-Goals

**Goals:**
- Make the stepwise/manual demo feel like a supported interactive operator workflow rather than a thin test harness.
- Add first-class commands for agent attach, message sending, gateway console observation, and notifier lifecycle control.
- Keep the existing `auto` and `matrix` flows stable and non-interactive.
- Reuse existing gateway attach and mail-notifier operations rather than inventing a demo-specific control protocol.

**Non-Goals:**
- Add a new gateway protocol surface or a new mailbox transport.
- Introduce a persistent `gateway.stdout` logging subsystem for the broader runtime.
- Change the pass/fail verification contract for the demo's automatic workflow.
- Remove `inspect` or `verify` as persisted evidence/report surfaces.

## Decisions

### Decision: Stepwise `start` will use a foreground auxiliary tmux gateway window, while `auto` stays detached

For stepwise/manual runs, `start` will attach the gateway in foreground auxiliary-window mode so that the gateway has a watchable live console separate from the agent TUI. For `auto` and `matrix`, the demo will keep the existing detached gateway behavior to avoid destabilizing the already-working canonical automation path.

Why this approach:
- it gives the operator a real live gateway console to observe,
- it does not require changing the automatic workflow contract,
- it uses the existing managed-agent gateway attach capability rather than a demo-only execution mode.

Alternative considered:
- using foreground mode for both `start` and `auto`.
  Rejected because `auto` is a test-like path whose primary value is stable unattended execution, not operator observation.

### Decision: `watch-gateway` will poll tmux pane output, not synthesize a pseudo-console from gateway events

The new `watch-gateway` command will resolve the current demo state, query live gateway status, locate the authoritative auxiliary gateway window/pane, and print that console output via `tmux capture-pane`. An optional follow mode will repeat that poll for live observation.

Why this approach:
- the user explicitly wants to see gateway console output,
- the current demo does not have a persisted `gateway.stdout` file,
- a pane-capture wrapper keeps the tmux dependency inside the demo command rather than on the operator.

Alternative considered:
- tailing `events.jsonl` or `queue.sqlite` as the primary `watch-gateway` surface.
  Rejected because those artifacts are structured evidence, not the live gateway console the operator asked to watch.

### Decision: Gateway mail-notifier controls will be exposed as a grouped `notifier` command surface

The demo will expose:
- `notifier status`
- `notifier on`
- `notifier off`
- `notifier set-interval`

These commands will reuse the existing gateway mail-notifier lifecycle operations already used internally by the demo. `set-interval` will use the same enable/update behavior as the underlying control surface so that interval changes are applied without inventing a separate semantics layer.

Why this approach:
- it groups related controls under one discoverable namespace,
- it lets users experiment with notifier behavior during a live stepwise run,
- it keeps the demo surface aligned with the existing gateway notifier model.

Alternative considered:
- exposing separate top-level verbs such as `notifier-on` and `notifier-off`.
  Rejected because it makes the demo surface noisier and less coherent.

### Decision: `send` becomes the taught operator verb; `manual-send` may remain as compatibility surface

The stepwise README and supported workflow will teach `send` as the operator action that injects another mailbox message into the running demo. The implementation may keep `manual-send` as a compatibility alias, but it will no longer be the primary user-facing command name.

Why this approach:
- `send` matches what the operator is trying to do,
- `manual-send` reads like a special case instead of the central interactive action,
- this keeps the stepwise command model short and memorable.

## Risks / Trade-offs

- [Stepwise and automatic modes diverge] → Keep the split narrow and explicit: only gateway execution mode and operator-facing commands differ; verification and message-processing semantics stay shared.
- [Gateway auxiliary-window metadata may be unavailable after shutdown] → Make `watch-gateway` fail clearly when no active demo or no active gateway window exists instead of trying to read stale pane identifiers.
- [Operators may confuse `watch-gateway` with persisted evidence] → Keep `inspect` and `verify` as the documented evidence/report surfaces, and document `watch-gateway` as a live observation tool only.
- [Notifier control commands could be invoked when the demo is inactive] → Resolve demo state first and fail clearly when the managed session or gateway is no longer active.

## Migration Plan

1. Extend the stepwise command parser and README without changing the existing automatic command contract.
2. Update stepwise `start` to request foreground auxiliary-window gateway attach.
3. Add `attach`, `send`, `watch-gateway`, and `notifier ...` behavior on top of persisted demo state.
4. Add unit coverage for the expanded command surface and stepwise-mode expectations.
5. Verify that `auto --tool claude` and `auto --tool codex` still pass unchanged.

Rollback is straightforward: revert the stepwise command additions and restore stepwise `start` to detached gateway attach while keeping the automatic flow intact.

## Open Questions

- None. The user has already selected the gateway-observation model: start the stepwise gateway in an auxiliary tmux foreground window and watch it by polling tmux pane output.
