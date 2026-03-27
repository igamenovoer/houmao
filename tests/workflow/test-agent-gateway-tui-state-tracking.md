# Serverless Agent Gateway TUI State Tracking Workflow

This workflow documents how to run a no-`houmao-server` experiment for one local interactive TUI agent, attach a live gateway to that agent, and inspect the supported gateway-owned tracking surface for that session.

The goal is to compare two observation paths without relying on retired local history surfaces:

1. the gateway-owned tracked current state, plus explicit prompt-note provenance, for the attached session
2. the serverless `houmao-mgr agents state` CLI path

For runtime-owned `local_interactive` sessions, repo-owned local/serverless guidance now treats `GET /v1/control/tui/state` plus explicit prompt-note evidence as the supported gateway tracking surface. `GET /v1/control/tui/history` may still exist for compatibility callers, but this workflow does not rely on it.

## Scope

This workflow is specifically for:

- `houmao-mgr agents launch ...` without `houmao-server`
- backend `local_interactive`
- one tmux-backed Codex TUI session
- explicit gateway attach through `houmao-mgr agents gateway attach`
- gateway-owned current state via `GET /v1/control/tui/state`
- explicit prompt-note evidence via `POST /v1/control/tui/note-prompt` or automatic prompt-note capture during `submit_prompt`

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

For serverless local sessions, `houmao-mgr agents state/gateway ...` resolves local records by:

- shared-registry `agent_id`, or
- raw creation-time `agent_name`

It does not reliably resolve by tmux session name alone in this workflow.

After launch, prefer the raw creation-time agent name from `agents list`. Example:

```bash
pixi run houmao-mgr agents list
```

In the example run below, the agent name was `projection-demo-codex`, while the tmux session name was `hm-gw-track-codex`. If `--session-name` were omitted, the default tmux handle would be `AGENTSYS-projection-demo-codex-<epoch-ms>`.

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
  --agent-name projection-demo-codex \
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

Use the raw agent name from `agents list`. Example:

```bash
pixi run houmao-mgr agents state --agent-name projection-demo-codex
pixi run houmao-mgr agents gateway status --agent-name projection-demo-codex
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

In the documented run, the serverless CLI path showed:

- `transport_state: "tmux_up"`
- `process_state: "tui_up"`
- `parse_status: "parsed"`
- `turn.phase: "ready"`
- `last_turn.result: "none"`

## Attach The Gateway

Attach a live gateway to the local interactive session:

```bash
pixi run houmao-mgr agents gateway attach --agent-name projection-demo-codex
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
pixi run houmao-mgr agents gateway status --agent-name projection-demo-codex
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
  --agent-name projection-demo-codex \
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

Successful `submit_prompt` execution already records explicit prompt-note evidence on the same gateway-owned tracker. Use `POST /v1/control/tui/note-prompt` only when you need that provenance without routing a prompt through the gateway queue.

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

## Query The Gateway-Owned Tracked State

The live gateway exposes its own tracked current state for attached TUI sessions:

```bash
curl -s http://127.0.0.1:<gateway-port>/health
curl -s http://127.0.0.1:<gateway-port>/v1/status
curl -s http://127.0.0.1:<gateway-port>/v1/control/tui/state
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
- `last_turn.source`
- `recent_transitions`

If you need to record explicit input provenance without actually executing a prompt, you can also call:

```bash
curl -s \
  -H 'content-type: application/json' \
  -d '{"prompt":"TRACKING_NOTE_ONLY"}' \
  http://127.0.0.1:<gateway-port>/v1/control/tui/note-prompt
```

That route returns the updated tracked state and uses the same gateway-owned authority as `submit_prompt`.

## Expected Gateway-Owned Tracking Behavior

In the documented run, the gateway-owned tracked state showed:

- initial `ready` posture
- transition to `active` at prompt-submission time
- transition back to `ready` immediately afterward

That evidence appeared in the state payload through `recent_transitions`, together with the updated `last_turn` fields.

This is the supported repo-owned local/serverless inspection path for attached `local_interactive` sessions.

## Compare Against The Serverless CLI State Path

After the same prompt submission, query the serverless CLI path again:

```bash
pixi run houmao-mgr agents state --agent-name projection-demo-codex
```

In the documented run, the serverless `agents state` call showed the current posture correctly but did not preserve the same gateway-owned prompt-transition evidence across independent invocations.

That difference matters:

- the attached gateway owns the continuous tracked state for the lifetime of the live gateway
- the current serverless `houmao-mgr agents state` path refreshes local tracking per invocation

So this workflow should treat gateway-owned tracked state as the authoritative local/serverless observer for attached-session prompt lifecycle evidence.

`/v1/control/tui/history` may still be callable directly, but this workflow treats it as compatibility-only and does not rely on it.

## Current Findings To Record

When this workflow succeeds, record the following separately:

1. Gateway attach status: `healthy`, `connected`, `request_admission=open`, `terminal_surface_eligibility=ready`
2. Gateway request lifecycle: accepted, executed, completed
3. Gateway-owned tracked-state evidence: whether `recent_transitions` records `ready -> active -> ready`
4. Explicit prompt provenance: whether tracked state reflects the prompt submission through `last_turn` fields or note-prompt evidence
5. Live pane behavior: whether the prompt is only staged in the input surface or whether a real assistant turn visibly runs
6. Serverless CLI behavior: whether `agents state` reflects the current posture without preserving the same gateway-owned transition record

## Cleanup

Stop the session when done:

```bash
pixi run houmao-mgr agents stop --agent-name projection-demo-codex
```

Expected cleanup result:

- tmux session `hm-gw-track-codex` is deleted
- the shared registry record for the agent is removed
- the runtime session artifacts remain on disk for later inspection under `~/.houmao/runtime/sessions/local_interactive/...`

Useful checks:

```bash
tmux has-session -t hm-gw-track-codex; echo rc:$?
pixi run houmao-mgr agents list | rg 'projection-demo-codex|hm-gw-track-codex' || true
```

## Interpretation

This workflow demonstrates two distinct facts:

1. serverless gateway attach and gateway-owned tracked current state do work for `local_interactive` sessions
2. the serverless `houmao-mgr agents state` path is not an equivalent observer for the same attached-session transition evidence

If this workflow is used during debugging, treat gateway-owned tracked state plus explicit prompt-note evidence as the authoritative local/serverless surface for attached-session prompt lifecycle inspection.
