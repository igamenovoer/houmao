# Design

## Context

Kimi's foreground Web host serves the browser and authenticated REST API. Its stock prompt handler may resume a cold session and change model or profile settings before calling `submit`. It snapshots readiness but calls `submit` in either state. The condition only controls whether the response waits for launch. `--no-open` suppresses browser opening, while the native startup banner can still contain a bearer token. [Web launcher](../../../extern/orphan/kimi-code/apps/kimi-code/src/cli/sub/web/run.ts) and [native prompt routes](../../../extern/orphan/kimi-code/packages/kap-server/src/routes/prompts.ts).

## Goals / Non-Goals

Run the actual Kimi Web application and let operators and authenticated Houmao clients work in the same bound conversation. Maintain independent client lifetimes, protect native credentials, and enforce the 02 immediate-delivery contract even when a human submits directly in the browser.

## Decisions

### Bind a Private Native Host and Human Surface

Launch `kimi web --no-open` on an owner-local loopback listener with an isolated native home, selected workspace, and normal auth. Capture the startup stream privately before filtering any log or pane output. Verify process, listener, build, home and native session before authenticating or publishing readiness. Public handoff contains a clean browser origin/session or remote connection instructions. An explicit owner-authorized open can bootstrap its local browser privately. Kimi's home-wide bearer stays in the owner context. Independent browser and machine clients may use Kimi's native auth model without publishing that token. [Native auth middleware](../../../extern/orphan/kimi-code/packages/kap-server/src/middleware/auth.ts).

### Require a Conditional Operation at the Native Input Boundary

Select a qualified native operation or supported in-process Kimi integration that can compare the captured host/session incarnation, active or pending work, and dispatch permission, then commit a ready-only prompt atomically against browser input. The condition must cover cold activation, profile/model changes, prepared attachments, queue insertion, and any retry after stale-state reload. A protected reservation may cover the transaction if every native submitter respects it and failure releases it with no prompt effects. A Houmao mutex plus GET and unconditional POST leaves the browser race open. Version-gate the hook or operation. A stock build offering only the inspected behavior reports unsupported before advertising the managed pair.

### Correlate Native Work and Bound Observation

Associate each managed request with its native session, prompt ID and host incarnation. Preserve the difference between queued, launched, settled, cancelled and uncertain. Mark browser work as human or external to the extent supported by native evidence. A targeted abort uses the verified active prompt ID. Inspection uses a non-mutating live source or cached observations with freshness. Some stock reads call `resumeSessionById`; do not issue those reads to inspect a cold session. Reconnect to the same host and recover attributable facts without replay.

### Prove the Race Through Both Clients

Use the supported native extension or build with a real browser and the managed gateway against the same native host. Pause before managed dispatch, let the browser acquire the turn, then release the managed request. Verify conflict at the gateway, no latent queue entry, no override change, no eventual provider request after the browser finishes, and correct human versus managed event/usage attribution. Repeat with gateway restart, stale host binding, and ordinary plugin or mail delivery. DSH Web tests supply a harness pattern, not Kimi protocol evidence. [Existing browser test harness](../../../tests/integration/agents/dsh/web/test_browser_coexistence.py).

## Risks / Trade-offs

- A supposedly rejected input can be queued or mutate the next turn's configuration. Exercise the native journal, queue, model settings and final provider traffic under a deterministic race.
- A native launcher may print `#token=` even without opening a browser. Check logs, tmux diagnostics, startup errors, discovery, passive state, and gateway responses for credential disclosure.

## Migration Plan

After 02, qualify the native admission integration first. Record the exact installed Kimi build and how the atomic operation is obtained. If the available build lacks a qualifying integration, record that limitation and keep this pair unavailable. Enable Web mode only when the real-browser and managed-control acceptance run passes. Changes 03–06 do not gate this adapter.
