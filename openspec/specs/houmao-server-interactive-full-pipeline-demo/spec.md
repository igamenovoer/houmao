# houmao-server-interactive-full-pipeline-demo Specification

## Purpose
TBD - created by archiving change add-houmao-server-interactive-full-pipeline-demo. Update Purpose after archive.
## Requirements
### Requirement: Repository SHALL provide a standalone Houmao-server interactive full-pipeline demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo-pack directory at `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `launch_alice.sh`
- `send_prompt.sh`
- `stop_demo.sh`

The pack SHALL also own the tracked compatibility-profile source needed for pair-managed startup.

The pack SHALL implement its own workflow and SHALL NOT delegate post-launch interaction to the older CAO interactive demo pack.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-interactive-full-pipeline-demo/`
- **THEN** the required files are present
- **AND THEN** the pack-owned startup assets needed for pair-managed launch are present
- **AND THEN** the pack can be understood and run from that directory without depending on sibling demo wrappers for its core workflow

### Requirement: Demo startup SHALL use pair-managed `houmao-mgr` install and launch with a demo-owned `houmao-server`
The startup workflow SHALL install one tracked compatibility profile into the demo-owned server through top-level `houmao-mgr install`, launch one detached TUI session through the explicit compatibility surface `houmao-mgr cao launch --headless`, and persist the selected demo variant in local demo state.

The demo SHALL provision one demo-owned `houmao-server` listener on loopback for the run and SHALL persist the resolved `api_base_url` in demo state rather than assuming an unrelated server instance already exists.

The demo SHALL provision a demo-owned working tree for the session under the run root rather than pointing the launched session directly at the repository checkout.

The pair install and detached launch subprocesses SHALL run with the same demo-owned runtime, registry, jobs, and home roots used for that run, so delegated artifacts and related state remain owned by the run root rather than ambient Houmao directories.

Demo startup SHALL use explicit demo-owned compatibility startup budgets rather than relying on the generic pair defaults. At minimum, the demo-owned startup profile SHALL include:

- compatibility shell-ready timeout = `20s`
- compatibility provider-ready timeout = `120s`
- compatibility Codex warmup = `10s`
- detached compatibility create timeout = `180s`

The detached compatibility create timeout SHALL remain larger than the bounded demo-owned server compatibility startup chain.

The demo SHALL expose a startup override surface for those demo-owned compatibility timeout values through the demo CLI and shell wrapper so automation can tune them without patching repository code.

When the operator does not provide a provider override, startup SHALL use `claude_code` as the implicit default provider.

When the operator provides `--provider codex`, startup SHALL launch the Codex-backed interactive variant through the same tracked compatibility profile.

The tracked compatibility profile used by startup SHALL be `gpu-kernel-coder`.

When the operator provides `--session-name`, startup SHALL use that value for the detached compatibility launch and SHALL derive the persisted `agent_identity` from it.

The persisted startup state SHALL include at minimum:

- `provider`
- `tool`
- `agent_profile`
- `variant_id`
- `api_base_url`
- `agent_identity`
- `session_manifest_path`
- `session_name`
- `terminal_id`
- `agent_ref`

#### Scenario: Default startup uses the tracked Claude provider and detached compatibility launch
- **WHEN** the operator runs the demo startup command without a provider override
- **THEN** the demo installs the tracked `gpu-kernel-coder` profile through top-level `houmao-mgr install`
- **AND THEN** the demo launches the interactive session through `houmao-mgr cao launch --headless`
- **AND THEN** the demo-owned `houmao-server` startup uses the documented demo compatibility startup budgets instead of generic pair defaults
- **AND THEN** the detached launch uses the documented demo create-timeout budget instead of the generic pair default
- **AND THEN** the delegated session uses `provider = claude_code`
- **AND THEN** persisted startup state records `tool = claude`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = claude-gpu-kernel-coder`

#### Scenario: Startup accepts an explicit Codex provider
- **WHEN** the operator runs startup with `--provider codex`
- **THEN** the demo installs the tracked `gpu-kernel-coder` profile through top-level `houmao-mgr install`
- **AND THEN** the demo launches the interactive session through `houmao-mgr cao launch --headless`
- **AND THEN** the demo-owned `houmao-server` startup uses the documented demo compatibility startup budgets, including the demo Codex warmup override
- **AND THEN** the delegated session uses `provider = codex`
- **AND THEN** persisted startup state records `tool = codex`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = codex-gpu-kernel-coder`

#### Scenario: Session-name override replaces the default generated identity
- **WHEN** the operator runs startup with `--session-name alice`
- **THEN** the detached compatibility launch uses `alice` as the requested session name
- **AND THEN** persisted startup state records the canonicalized `agent_identity` derived from `alice`

#### Scenario: Pair startup remains owned by the demo run root
- **WHEN** the operator starts the demo for a fresh run root
- **THEN** the pair install and detached launch commands run with demo-owned runtime, registry, jobs, and home roots
- **AND THEN** delegated launch artifacts for that run are written under the selected run root rather than ambient Houmao directories

#### Scenario: Operator overrides demo compatibility startup budgets
- **WHEN** the operator or automation supplies explicit demo startup timeout overrides
- **THEN** the demo passes those override values into both the demo-owned `houmao-server` startup command and the detached `houmao-mgr cao launch --headless` command as appropriate
- **AND THEN** the demo does not require source edits to tune the startup budget for slow environments

### Requirement: Startup SHALL rely on pair-managed delegated launch artifacts and auto-registration
After the interactive pair launch succeeds, the demo SHALL discover the runtime-owned manifest and delegated session artifacts produced by `houmao-mgr cao launch --headless`.

The demo SHALL use the manifest `houmao_server` section as the startup-to-follow-up data bridge.

The demo SHALL persist `session_name` as the stable v1 managed-agent `agent_ref` in demo state and SHALL use that persisted value for post-launch managed-agent routes without requiring a second discovery step.

The demo SHALL resolve the delegated manifest and related session artifacts from the demo-owned runtime root for that run rather than from ambient shared runtime roots.

The demo SHALL NOT send its own extra `POST /houmao/launches/register` after a successful delegated pair launch.

The demo MAY additionally persist a later-discovered `tracked_agent_id`, but follow-up commands SHALL NOT depend on discovering it before first use.

#### Scenario: Pair-managed launch auto-registers the delegated session
- **WHEN** the operator completes a successful demo startup
- **THEN** the session launched through `houmao-mgr cao launch --headless` becomes addressable through server-managed discovery and inspection routes
- **AND THEN** the demo does not send a second manual registration request

#### Scenario: Startup persists both delegated runtime-owned and server-facing identifiers
- **WHEN** startup completes successfully
- **THEN** demo state records the runtime-owned `session_manifest_path`, `session_name`, and `terminal_id`
- **AND THEN** demo state also records the server authority `api_base_url`
- **AND THEN** demo state records `agent_ref = session_name` for managed-agent routes
- **AND THEN** follow-up commands use those persisted identifiers instead of rediscovering the launch from scratch

#### Scenario: Startup finds the delegated manifest under the demo-owned runtime root
- **WHEN** startup completes successfully for a selected demo run root
- **THEN** the delegated manifest path used by follow-up commands resolves under that run root's runtime directory
- **AND THEN** startup does not need to search ambient shared Houmao runtime roots to continue

### Requirement: Post-launch demo interaction SHALL use direct `houmao-server` HTTP routes only
After startup completes, the demo SHALL use direct `houmao-server` HTTP calls for inspect, prompt submission, interrupt submission, and stop.

`send-turn` SHALL submit prompts through `POST /houmao/agents/{agent_ref}/requests` with `request_kind = submit_prompt`.

`interrupt` SHALL submit interrupts through `POST /houmao/agents/{agent_ref}/requests` with `request_kind = interrupt`.

`inspect` SHALL read managed-agent state through `GET /houmao/agents/{agent_ref}/state` and `GET /houmao/agents/{agent_ref}/state/detail`. When the demo exposes optional parser-derived text or deeper tracked-terminal inspection, it SHALL read that information through `GET /houmao/terminals/{terminal_id}/state`, and it SHALL expose parser-derived dialog tail only behind an explicit operator opt-in.

The demo SHALL NOT call post-launch control commands from `houmao-mgr` or `houmao-cli`.

The pack SHALL NOT provide a raw control-input `send-keys` equivalent in v1.

#### Scenario: Prompt submission uses the managed-agent request surface
- **WHEN** the operator runs `send-turn` after a successful startup
- **THEN** the demo sends the prompt through `POST /houmao/agents/{agent_ref}/requests`
- **AND THEN** the request body uses `request_kind = submit_prompt`
- **AND THEN** the request targets the persisted `agent_ref = session_name`
- **AND THEN** the prompt is not submitted through a post-launch pair CLI or runtime CLI command

#### Scenario: Interrupt submission uses the managed-agent request surface
- **WHEN** the operator runs the demo interrupt action while a launched session is active
- **THEN** the demo sends the interrupt through `POST /houmao/agents/{agent_ref}/requests`
- **AND THEN** the request body uses `request_kind = interrupt`
- **AND THEN** the request targets the persisted `agent_ref = session_name`
- **AND THEN** the interrupt is not delivered through a post-launch pair CLI or runtime CLI command

#### Scenario: Inspect reads server-owned managed-agent and tracked-terminal state
- **WHEN** the operator runs `inspect` for an active demo run
- **THEN** the demo queries the persisted `houmao-server` authority for managed-agent state
- **AND THEN** any optional parsed dialog or tracked-terminal surface comes from `houmao-server`
- **AND THEN** the demo does not run a second demo-local parser or tracker to classify live state

#### Scenario: Inspect keeps parser-derived dialog tail opt-in
- **WHEN** the operator runs `inspect` without the explicit dialog-tail option
- **THEN** the default inspect output is limited to managed-agent state and other non-text inspection fields
- **AND THEN** parser-derived dialog tail is omitted unless the operator explicitly requests it

### Requirement: Verification SHALL rely on server-tracked request and state evidence rather than transcript wording
The verification flow SHALL preserve the selected provider, tool, agent profile, and stable demo variant identity from startup state.

The generated verification artifact SHALL preserve at minimum:

- `provider`
- `tool`
- `agent_profile`
- `variant_id`
- `api_base_url`
- the resolved session or managed-agent metadata needed to connect the report to the live run

Successful verification SHALL be based on accepted prompt requests and server-tracked state or history evidence rather than on exact assistant reply text.

#### Scenario: Verification records the selected variant and server authority
- **WHEN** the operator runs `verify` after a successful interactive run
- **THEN** `report.json` records the startup-selected `provider`
- **AND THEN** `report.json` records the resolved `tool`
- **AND THEN** `report.json` records the tracked `agent_profile`
- **AND THEN** `report.json` records the stable `variant_id`
- **AND THEN** `report.json` records the `api_base_url` used for server interaction

#### Scenario: Verification does not require exact assistant reply text
- **WHEN** the demo verifies prompts executed under the default shadow-first TUI posture
- **THEN** the verification flow does not require an exact assistant transcript string
- **AND THEN** it validates the run through accepted request records plus server-tracked state or history evidence

### Requirement: Demo SHALL provide explicit server-backed teardown and mark local state inactive
The demo SHALL provide an explicit stop command that tears down the active TUI session through direct `houmao-server` HTTP authority and then marks demo state inactive.

For TUI sessions in v1, the stop flow SHALL target `POST /houmao/agents/{agent_ref}/stop` on the same persisted `houmao-server` authority rather than calling post-launch pair CLI or runtime CLI stop, and rather than using raw CAO session deletion as the normal operator stop path.

If the session is already gone remotely, the stop flow SHALL still clear local active state as long as the failure matches a stale-session outcome.

During partial-start cleanup before managed-agent registration is guaranteed, the demo MAY still use best-effort session deletion on the same `houmao-server` authority as an internal cleanup fallback.

#### Scenario: Stop tears down the active session through the managed-agent route
- **WHEN** the operator runs the demo stop command with an active session
- **THEN** the demo calls `POST /houmao/agents/{agent_ref}/stop` on the persisted `houmao-server` authority
- **AND THEN** it does not call post-launch pair CLI or runtime CLI stop
- **AND THEN** it does not use raw `DELETE /cao/sessions/{session_name}` as the normal stop path
- **AND THEN** subsequent prompt or inspect actions fail until startup is run again

#### Scenario: Stop is safe when the remote session is already gone
- **WHEN** the operator runs stop and the recorded managed agent no longer exists on the selected `houmao-server`
- **THEN** the demo exits gracefully for that stale-session condition
- **AND THEN** it updates local demo state to inactive

