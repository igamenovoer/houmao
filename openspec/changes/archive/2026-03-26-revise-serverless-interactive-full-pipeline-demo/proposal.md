## Why

The current `houmao-server-interactive-full-pipeline-demo` still teaches a pair-managed startup and control path even though the newer Houmao design already supports launching and operating managed agents locally without `houmao-server`. That makes the demo misleading for the current recommended architecture and keeps its persisted identity and route contract anchored to an older `agent_ref = session_name` model.

## What Changes

- Revise `scripts/demo/houmao-server-interactive-full-pipeline-demo/` to launch one managed agent locally without starting a demo-owned `houmao-server`.
- Replace the demo's startup contract so it builds the brain, starts the runtime session, and persists the local managed-agent identity and manifest details needed for later control.
- Replace pair HTTP follow-up actions with local registry-first and controller-backed inspection, prompt, interrupt, verify, and stop behavior.
- Update the persisted demo state and operator-facing docs so `agent_name`, `agent_id`, and `tmux_session_name` are reported distinctly instead of treating the tmux session handle as the managed-agent reference.
- **BREAKING**: Change the demo's persisted state schema, run-root artifact layout, and README contract away from demo-owned `houmao-server` process artifacts and server-route terminology.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-server-interactive-full-pipeline-demo`: Change the demo pack requirements from pair-managed `houmao-server` launch and route-driven follow-up control to a local serverless managed-agent workflow that uses the shared registry and local runtime surfaces.

## Impact

- Affected demo code under `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/` and shell wrappers under `scripts/demo/houmao-server-interactive-full-pipeline-demo/`
- Updated demo spec under `openspec/specs/houmao-server-interactive-full-pipeline-demo/spec.md`
- Updated unit and integration coverage for the demo's startup, persisted state, and control workflow
- No intended changes to `mail-ping-pong-gateway-demo-pack` or to the public `houmao-mgr` launch/control requirements themselves
