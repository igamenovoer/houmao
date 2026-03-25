# Serverless Agent Gateway TUI State Tracking Workflow

This workflow documents how to run a no-`houmao-server` experiment for a local interactive TUI agent, attach a live gateway to that agent, and inspect the gateway-owned TUI state tracking behavior.

The goal is not only to verify that gateway attach works for a serverless local TUI session, but also to compare two different observation paths:

1. the gateway-owned persistent tracker exposed by the live gateway HTTP routes
2. the serverless `houmao-mgr agents state/show/history` CLI path

In the current implementation, those two paths do not retain the same turn-tracking information for local interactive sessions. This workflow is useful both as an operator recipe and as a debugging checklist.

## Scope

This workflow is specifically for:

- `houmao-mgr agents launch ...` without `houmao-server`
- backend `local_interactive`
- one tmux-backed Codex TUI session
- explicit gateway attach through `houmao-mgr agents gateway attach`
- gateway-owned TUI tracking via `GET /v1/control/tui/state` and `GET /v1/control/tui/history`

This is not the pair-managed `houmao-server + houmao-mgr` workflow.

## Preconditions

- Run from the repository root.
- `pixi` is installed and the default environment is usable.
- `tmux` is installed and available on `PATH`.
- `codex` is installed and available on `PATH`.
- The local fixture agent definitions exist under `tests/fixtures/agents`.
- The local Codex credential profile exists under `tests/fixtures/agents/brains/api-creds/codex/personal-a-default/`.

Useful checks:

```bash
command -v tmux
command -v codex
pixi run houmao-mgr agents launch --help
```

## Important Identity Note

For serverless local sessions, `houmao-mgr agents state/show/history/gateway ...` currently resolves local records by:

- shared-registry `agent_id`, or
- canonical `agent_name`

It does not reliably resolve by tmux session name alone in this workflow.

After launch, prefer the canonical agent name from the registry, for example:

```bash
pixi run houmao-mgr agents list
```

In the example run below, the canonical agent ref was `AGENTSYS-projection-demo-codex`, while the tmux session name was `hm-gw-track-codex`.

## Launch The Local TUI Agent

Set the fixture agent-definition directory explicitly:

```bash
export AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents"
```

Launch one serverless local interactive Codex session:

```bash
pixi run houmao-mgr agents launch \
  --agents projection-demo \
  --provider codex \
  --session-name hm-gw-track-codex \
  --yolo
```

Expected result:

- launch completes successfully
- one tmux session named `hm-gw-track-codex` exists
- window `0` is the stable `agent` surface
- the launch prints a runtime manifest path under `~/.houmao/runtime/sessions/local_interactive/.../manifest.json`

Useful checks:

```bash
tmux list-windows -t hm-gw-track-codex
pixi run houmao-mgr agents list
```

## Observe Baseline State Before Gateway Attach

Use the canonical agent ref from `agents list`. Example:

```bash
pixi run houmao-mgr agents state AGENTSYS-projection-demo-codex
pixi run houmao-mgr agents show AGENTSYS-projection-demo-codex
pixi run houmao-mgr agents history --limit 8 AGENTSYS-projection-demo-codex
pixi run houmao-mgr agents gateway status AGENTSYS-projection-demo-codex
```

Expected baseline observations:

- managed-agent availability is `available`
- gateway status is `not_attached`
- gateway request admission is blocked because no live gateway exists yet
- the local tracker sees the TUI as up and parsed
- the parsed surface usually shows Codex in an idle prompt posture such as:
  - `business_state: "idle"`
  - `input_mode: "freeform"`
  - `ui_context: "normal_prompt"`

In the example run, the serverless CLI path showed:

- `transport_state: "tmux_up"`
- `process_state: "tui_up"`
- `parse_status: "parsed"`
- `turn.phase: "ready"`
- `last_turn.result: "none"`

## Attach The Gateway

Attach a live gateway to the local interactive session:

```bash
pixi run houmao-mgr agents gateway attach AGENTSYS-projection-demo-codex
```

Expected result:

- attach succeeds
- the returned gateway status shows:
  - `gateway_health: "healthy"`
  - `managed_agent_connectivity: "connected"`
  - `request_admission: "open"`
  - `terminal_surface_eligibility: "ready"`
- a live gateway listener is bound on `127.0.0.1:<port>`

Confirm status again:

```bash
pixi run houmao-mgr agents gateway status AGENTSYS-projection-demo-codex
```

The runtime-owned gateway artifacts should now exist under the session root:

```text
<session-root>/gateway/
  attach.json
  desired-config.json
  events.jsonl
  logs/gateway.log
  queue.sqlite
  run/current-instance.json
  run/gateway.pid
  state.json
```

## Submit One Prompt Through The Gateway

Send a simple prompt through the explicit gateway path:

```bash
pixi run houmao-mgr agents gateway prompt \
  AGENTSYS-projection-demo-codex \
  --prompt 'Reply with exactly TRACKING_OK and nothing else.'
```

Expected immediate result:

- the gateway accepts the request
- the response contains a `request_id`
- `queue_depth` may briefly increase

The gateway logs should record the request lifecycle:

```bash
tail -n 50 <session-root>/gateway/logs/gateway.log
tail -n 50 <session-root>/gateway/events.jsonl
```

Expected gateway log sequence:

- `accepted public gateway request`
- `executing gateway request`
- `completed gateway request`

## Inspect The Live Pane

Capture the tmux pane directly:

```bash
tmux capture-pane -p -t hm-gw-track-codex:agent | tail -n 80
```

Observe whether:

- the prompt text appears in the Codex input surface
- Codex visibly transitions into a working state
- Codex emits an answer
- the pane returns to a ready prompt

In the documented run, the prompt text was visible in the input surface, but no assistant answer was visible in the captured pane.

## Query The Gateway-Owned Persistent TUI Tracker

The live gateway exposes its own persistent tracker for attached TUI sessions:

```bash
curl -s http://127.0.0.1:<gateway-port>/health
curl -s http://127.0.0.1:<gateway-port>/v1/status
curl -s http://127.0.0.1:<gateway-port>/v1/control/tui/state
curl -s 'http://127.0.0.1:<gateway-port>/v1/control/tui/history?limit=12'
```

Replace `<gateway-port>` with the port returned by `gateway attach` or `gateway status`.

What to observe in `/v1/control/tui/state`:

- `tracked_session.tracked_session_id`
- `tracked_session.tmux_session_name`
- `diagnostics.transport_state`
- `diagnostics.process_state`
- `diagnostics.parse_status`
- `parsed_surface.business_state`
- `parsed_surface.input_mode`
- `surface.accepting_input`
- `surface.editing_input`
- `turn.phase`
- `last_turn.result`
- `recent_transitions`

What to observe in `/v1/control/tui/history`:

- whether prompt submission caused a transition from `ready` to `active`
- whether the tracker later returned to `ready`
- whether the transition timestamps line up with the gateway request execution

## Expected Gateway-Owned Tracking Behavior

In the documented run, the gateway-owned persistent tracker showed:

- initial `ready` state
- transition to `active` at prompt-submission time
- transition back to `ready` immediately afterward

The recorded transitions looked like:

- `2026-03-25T18:18:29+00:00`: initial ready posture
- `2026-03-25T18:18:42+00:00`: `turn_phase: 'ready' -> 'active'`
- `2026-03-25T18:18:43+00:00`: `turn_phase: 'active' -> 'ready'`

This indicates that the live gateway tracker did retain prompt-submission evidence and gateway-driven turn-phase transitions for a `local_interactive` session.

## Compare Against The Serverless CLI Tracking Path

After the same prompt submission, query the serverless CLI path again:

```bash
pixi run houmao-mgr agents state AGENTSYS-projection-demo-codex
pixi run houmao-mgr agents show AGENTSYS-projection-demo-codex
pixi run houmao-mgr agents history --limit 12 AGENTSYS-projection-demo-codex
```

In the documented run, this path did not retain the same turn history. It showed only a fresh baseline sample such as:

- `turn.phase: "ready"`
- `last_turn.result: "none"`
- one short history beginning from the newest poll

That difference matters:

- the gateway-owned HTTP tracker is persistent for the lifetime of the attached gateway
- the current serverless `houmao-mgr agents state/show/history` path rebuilds a fresh local tracker per invocation

So this workflow should explicitly compare both paths rather than assuming they are equivalent.

## Current Findings To Record

When this workflow succeeds, record the following separately:

1. Gateway attach status:
   `healthy`, `connected`, `request_admission=open`, `terminal_surface_eligibility=ready`
2. Gateway request lifecycle:
   accepted, executed, completed
3. Gateway-owned TUI tracker behavior:
   whether it records `ready -> active -> ready`
4. Live pane behavior:
   whether the prompt is only staged in the input surface or whether a real assistant turn visibly runs
5. Serverless CLI tracker behavior:
   whether `agents state/show/history` retains the same turn history or loses it across calls

In the documented run:

- items 1 through 3 succeeded
- item 4 was suspicious because the pane showed staged prompt text but no visible answer
- item 5 exposed a mismatch because the CLI path did not retain the gateway-owned turn transitions

## Cleanup

Stop the session when done:

```bash
pixi run houmao-mgr agents stop AGENTSYS-projection-demo-codex
```

Expected cleanup result:

- tmux session `hm-gw-track-codex` is deleted
- the shared registry record for the agent is removed
- the runtime session artifacts remain on disk for later inspection under `~/.houmao/runtime/sessions/local_interactive/...`

Useful checks:

```bash
tmux has-session -t hm-gw-track-codex; echo rc:$?
pixi run houmao-mgr agents list | rg 'AGENTSYS-projection-demo-codex|hm-gw-track-codex' || true
```

## Interpretation

This workflow currently demonstrates two distinct facts:

1. serverless gateway attach and gateway-owned TUI tracking do work for `local_interactive` sessions
2. the serverless `houmao-mgr agents state/show/history` path is not yet an equivalent observer for that same live tracking state

If this workflow is used during debugging, treat the gateway HTTP routes as the authoritative source for persistent gateway-owned TUI tracking behavior in this scenario.
