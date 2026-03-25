## MODIFIED Requirements

### Requirement: Demo startup SHALL use pair-managed `houmao-mgr` install and launch with a demo-owned `houmao-server`
The startup workflow SHALL install one tracked compatibility profile into the demo-owned server through top-level `houmao-mgr install`, launch one detached TUI session through the explicit compatibility surface `houmao-mgr cao launch --headless`, and persist the selected demo variant in local demo state.

The demo SHALL provision one demo-owned `houmao-server` listener on loopback for the run and SHALL persist the resolved `api_base_url` in demo state rather than assuming an unrelated server instance already exists.

The demo SHALL provision a demo-owned working tree for the session under the run root rather than pointing the launched session directly at the repository checkout.

The pair install and detached launch subprocesses SHALL run with the same demo-owned runtime, registry, jobs, and home roots used for that run, so delegated artifacts and related state remain owned by the run root rather than ambient Houmao directories.

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
- **AND THEN** the delegated session uses `provider = claude_code`
- **AND THEN** persisted startup state records `tool = claude`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = claude-gpu-kernel-coder`

#### Scenario: Startup accepts an explicit Codex provider
- **WHEN** the operator runs startup with `--provider codex`
- **THEN** the demo installs the tracked `gpu-kernel-coder` profile through top-level `houmao-mgr install`
- **AND THEN** the demo launches the interactive session through `houmao-mgr cao launch --headless`
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
