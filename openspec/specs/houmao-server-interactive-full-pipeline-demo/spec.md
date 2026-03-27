# houmao-server-interactive-full-pipeline-demo Specification

## Purpose
TBD - created by archiving change add-houmao-server-interactive-full-pipeline-demo. Update Purpose after archive.
## Requirements

### Requirement: Repository SHALL provide a standalone Houmao-server interactive full-pipeline demo pack under `scripts/demo/`
The repository SHALL continue to include a demo-pack directory at `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `launch_alice.sh`
- `send_prompt.sh`
- `interrupt_demo.sh`
- `inspect_demo.sh`
- `verify_demo.sh`
- `stop_demo.sh`

The pack SHALL expose the tracked native agent-definition inputs needed for demo startup at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`.

That `agents` entry SHALL be a repository-tracked symlink that resolves to `tests/fixtures/agents/`.

The pack SHALL implement its own workflow and SHALL NOT delegate startup, follow-up interaction, inspection, verification, or teardown to the older CAO interactive demo pack or to a sibling demo pack.

The pack SHALL document itself as a local serverless managed-agent demo that keeps the historical directory name for continuity.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-interactive-full-pipeline-demo/`
- **THEN** the required files are present
- **AND THEN** the startup `agents` entry is present
- **AND THEN** that `agents` entry resolves to `tests/fixtures/agents/`
- **AND THEN** the pack can be understood and run from that directory without depending on sibling demo wrappers for its core workflow
- **AND THEN** the README describes the pack as a local managed-agent workflow rather than as a demo-owned `houmao-server` workflow

### Requirement: Demo startup SHALL use pair-managed native-selector launch with a demo-owned `houmao-server`
The startup workflow SHALL resolve one tracked native launch selector under the demo-local agent-definition root at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`, build the brain locally, and launch one detached local interactive managed-agent session without starting `houmao-server`.

The demo-local `agents` path SHALL resolve to `tests/fixtures/agents/` through the tracked symlink shipped with the demo pack.

Demo startup SHALL NOT require a separate `houmao-mgr install` step or a tracked compatibility profile Markdown file as its startup source of truth.

The demo SHALL provision a demo-owned working tree for the session under the run root rather than pointing the launched session directly at the repository checkout.

The local launch flow SHALL run with the same demo-owned runtime, registry, jobs, and home roots used for that run, so launch artifacts and related state remain owned by the run root rather than ambient Houmao directories.

Demo startup SHALL use explicit demo-owned local startup budgets rather than relying on generic defaults. At minimum, the demo-owned startup profile SHALL continue to cover provider shell readiness, provider interactive readiness, and any provider-specific warmup needed for the selected tool lane.

The demo SHALL expose a startup override surface for those local startup budgets through the demo CLI and shell wrappers so automation can tune them without patching repository code.

When the operator does not provide a provider override, startup SHALL use `claude_code` as the implicit default provider.

When the operator provides `--provider codex`, startup SHALL launch the Codex-backed interactive variant through the same tracked native launch selector.

The tracked native launch selector used by startup SHALL be `gpu-kernel-coder`.

When the operator does not provide an explicit managed-agent name override, startup SHALL derive a stable default `agent_name` from the selected demo variant.

When the operator provides `--session-name`, startup SHALL pass that value as the requested tmux session name and SHALL NOT treat it as the authoritative managed-agent reference.

The persisted startup state SHALL include at minimum:

- `provider`
- `tool`
- `agent_profile`
- `variant_id`
- `agent_name`
- `agent_id`
- `requested_session_name`
- `session_manifest_path`
- `session_root`
- `tmux_session_name`
- `runtime_root`
- `registry_root`
- `jobs_root`
- `workspace_dir`
- `workdir`

The persisted startup state SHALL NOT require `api_base_url`, demo-owned server pid metadata, server stdout/stderr log paths, or a `houmao_server` bridge section.

#### Scenario: Default startup uses the tracked Claude provider and local interactive launch
- **WHEN** the operator runs the demo startup command without a provider override
- **THEN** the demo launches one detached local interactive managed-agent session without starting `houmao-server`
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs instead of running `houmao-mgr install`
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
- **AND THEN** the local startup uses the documented demo-owned startup budgets instead of generic defaults
- **AND THEN** the launched session uses `provider = claude_code`
- **AND THEN** persisted startup state records `tool = claude`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = claude-gpu-kernel-coder`

#### Scenario: Startup accepts an explicit Codex provider
- **WHEN** the operator runs startup with `--provider codex`
- **THEN** the demo launches one detached local interactive managed-agent session without starting `houmao-server`
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
- **AND THEN** the local startup uses the documented demo-owned startup budgets, including any documented Codex warmup override
- **AND THEN** the launched session uses `provider = codex`
- **AND THEN** persisted startup state records `tool = codex`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = codex-gpu-kernel-coder`

#### Scenario: launch_alice keeps managed-agent and tmux identities distinct
- **WHEN** the operator runs `launch_alice.sh`
- **THEN** startup publishes the friendly managed-agent name `alice`
- **AND THEN** startup records `tmux_session_name = alice`
- **AND THEN** persisted startup state records the effective `agent_id` used for local exact targeting
- **AND THEN** the demo does not imply that the tmux session handle replaced the managed-agent identity

#### Scenario: Local startup remains owned by the demo run root
- **WHEN** the operator starts the demo for a fresh run root
- **THEN** the local launch flow runs with demo-owned runtime, registry, jobs, and home roots
- **AND THEN** launch artifacts for that run are written under the selected run root rather than ambient Houmao directories
- **AND THEN** the run root does not need a demo-owned `houmao-server` process or server log directory in order to complete startup

#### Scenario: Operator overrides local startup budgets
- **WHEN** the operator or automation supplies explicit local startup timeout overrides
- **THEN** the demo passes those override values into the local launch flow as appropriate
- **AND THEN** the demo does not require source edits to tune the startup budget for slow environments
- **AND THEN** the revised startup surface does not require server-start or server-stop timeout overrides

### Requirement: Startup SHALL rely on pair-managed delegated launch artifacts and auto-registration
After the interactive local launch succeeds, the demo SHALL discover the runtime-owned manifest and local shared-registry record produced by the local startup flow.

The demo SHALL use the local session manifest path and the shared registry publication as the startup-to-follow-up data bridge.

The demo SHALL persist the effective `agent_name`, `agent_id`, `tmux_session_name`, and `session_manifest_path` needed for later local control without requiring a second ad hoc discovery flow.

The demo SHALL resolve the session manifest and related runtime artifacts from the demo-owned runtime root for that run rather than from ambient shared runtime roots.

The demo SHALL NOT require any `houmao-server` registration or bridge metadata after a successful local startup.

The demo MAY additionally persist live tracked terminal metadata discovered during inspect, but follow-up commands SHALL NOT depend on server-owned terminal registration before first use.

#### Scenario: Local startup publishes the launched session to the shared registry
- **WHEN** the operator completes a successful demo startup
- **THEN** the locally launched session becomes addressable through shared-registry discovery
- **AND THEN** the demo does not send a `houmao-server` registration request
- **AND THEN** follow-up commands can resolve the managed agent from persisted local identity data

#### Scenario: Startup persists both manifest and local identity data
- **WHEN** startup completes successfully
- **THEN** demo state records the runtime-owned `session_manifest_path`, `session_root`, and `tmux_session_name`
- **AND THEN** demo state records the effective `agent_name` and `agent_id`
- **AND THEN** follow-up commands use those persisted identifiers instead of rediscovering the launch from scratch

#### Scenario: Startup finds the session manifest under the demo-owned runtime root
- **WHEN** startup completes successfully for a selected demo run root
- **THEN** the session manifest path used by follow-up commands resolves under that run root's runtime directory
- **AND THEN** startup does not need to search ambient shared Houmao runtime roots to continue

### Requirement: Post-launch demo interaction SHALL use direct `houmao-server` HTTP routes only
After startup completes, the demo SHALL use local registry-first resolution and resumed local runtime control for inspect, prompt submission, interrupt submission, and stop.

`send-turn` SHALL submit prompts through the default local managed-agent prompt path for the persisted agent identity rather than through `houmao-server` HTTP routes.

`interrupt` SHALL submit interrupts through the local runtime controller path for the persisted agent identity rather than through `houmao-server` HTTP routes.

`inspect` SHALL read managed-agent summary, detail, and history through the local managed-agent control surfaces. When the demo exposes optional parser-derived text or deeper tracked-terminal inspection, it SHALL read that information through local shared TUI tracking and SHALL expose parser-derived dialog tail only behind an explicit operator opt-in.

The demo SHALL NOT call post-launch control commands through `houmao-server` routes.

The demo SHALL NOT require post-launch CLI shell-outs to `houmao-mgr` or `houmao-cli` as its normal control path.

The pack SHALL NOT provide a raw control-input `send-keys` equivalent in this revised contract.

#### Scenario: Prompt submission uses the local managed-agent prompt surface
- **WHEN** the operator runs `send-turn` after a successful startup
- **THEN** the demo submits the prompt through the local managed-agent prompt path for the persisted agent identity
- **AND THEN** the prompt is not submitted through `houmao-server` HTTP routes
- **AND THEN** the prompt is not submitted through a raw control-input `send-keys` equivalent

#### Scenario: Interrupt submission uses the local managed-agent interrupt surface
- **WHEN** the operator runs the demo interrupt action while a launched session is active
- **THEN** the demo submits the interrupt through the local managed-agent interrupt path for the persisted agent identity
- **AND THEN** the interrupt is not delivered through `houmao-server` HTTP routes
- **AND THEN** the interrupt is not delivered through a raw control-input `send-keys` equivalent

#### Scenario: Inspect reads local managed-agent and tracked-terminal state
- **WHEN** the operator runs `inspect` for an active demo run
- **THEN** the demo queries local managed-agent state, detail, and history for the persisted agent identity
- **AND THEN** any optional parsed dialog or tracked-terminal surface comes from local shared TUI tracking
- **AND THEN** the demo does not require a `houmao-server` authority or `api_base_url` to inspect the live run

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
- `agent_name`
- `agent_id`
- `tmux_session_name`
- `session_manifest_path`
- the resolved local runtime metadata needed to connect the report to the live run

Successful verification SHALL be based on accepted prompt actions and local tracked state or history evidence rather than on exact assistant reply text.

#### Scenario: Verification records the selected variant and local agent identity
- **WHEN** the operator runs `verify` after a successful interactive run
- **THEN** `report.json` records the startup-selected `provider`
- **AND THEN** `report.json` records the resolved `tool`
- **AND THEN** `report.json` records the tracked `agent_profile`
- **AND THEN** `report.json` records the stable `variant_id`
- **AND THEN** `report.json` records the effective `agent_name`, `agent_id`, and `tmux_session_name`
- **AND THEN** `report.json` records the `session_manifest_path` used for local inspection and control

#### Scenario: Verification does not require exact assistant reply text
- **WHEN** the demo verifies prompts executed under the default local interactive TUI posture
- **THEN** the verification flow does not require an exact assistant transcript string
- **AND THEN** it validates the run through accepted prompt actions plus local tracked state or history evidence

### Requirement: Demo SHALL provide explicit server-backed teardown and mark local state inactive
The demo SHALL provide an explicit stop command that tears down the active local interactive session through the local runtime controller path and then marks demo state inactive.

For TUI sessions in this revised contract, the stop flow SHALL target the resolved local managed agent rather than `houmao-server` routes, post-launch pair CLI stop, or raw CAO session deletion.

If the session is already gone locally, the stop flow SHALL still clear local active state as long as the failure matches a stale-session outcome.

During partial-start cleanup before registry publication is guaranteed, the demo MAY still use best-effort local runtime or tmux cleanup for run-owned resources as an internal fallback.

#### Scenario: Stop tears down the active session through the local runtime path
- **WHEN** the operator runs the demo stop command with an active session
- **THEN** the demo stops the resolved local managed agent through the local runtime controller path
- **AND THEN** it does not call `houmao-server` stop routes
- **AND THEN** it does not require post-launch pair CLI stop as the normal stop path
- **AND THEN** subsequent prompt or inspect actions fail until startup is run again

#### Scenario: Stop is safe when the local session is already gone
- **WHEN** the operator runs stop and the recorded managed agent no longer exists in the selected local runtime
- **THEN** the demo exits gracefully for that stale-session condition
- **AND THEN** it updates local demo state to inactive
