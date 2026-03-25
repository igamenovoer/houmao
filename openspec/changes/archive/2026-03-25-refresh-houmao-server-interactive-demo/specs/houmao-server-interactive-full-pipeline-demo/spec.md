## MODIFIED Requirements

### Requirement: Repository SHALL provide a standalone Houmao-server interactive full-pipeline demo pack under `scripts/demo/`
The repository SHALL include a demo-pack directory at `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `launch_alice.sh`
- `send_prompt.sh`
- `stop_demo.sh`

The pack SHALL expose the tracked native agent-definition inputs needed for demo startup at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`.

That `agents` entry SHALL be a repository-tracked symlink that resolves to `tests/fixtures/agents/`.

The pack SHALL implement its own workflow and SHALL NOT delegate post-launch interaction to the older CAO interactive demo pack.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-interactive-full-pipeline-demo/`
- **THEN** the required files are present
- **AND THEN** the startup `agents` entry is present
- **AND THEN** that `agents` entry resolves to `tests/fixtures/agents/`
- **AND THEN** the pack can be understood and run from that directory without depending on sibling demo wrappers for its core workflow

### Requirement: Demo startup SHALL use pair-managed native-selector launch with a demo-owned `houmao-server`
The startup workflow SHALL resolve one tracked native launch selector under the demo-local agent-definition root at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`, launch one detached TUI session through the demo-owned `houmao-server` native headless launch API, and persist the selected demo variant in local demo state.

The demo-local `agents` path SHALL resolve to `tests/fixtures/agents/` through the tracked symlink shipped with the demo pack.

Demo startup SHALL NOT require a separate `houmao-mgr install` step or a tracked compatibility profile Markdown file as its startup source of truth.

The demo SHALL provision one demo-owned `houmao-server` listener on loopback for the run and SHALL persist the resolved `api_base_url` in demo state rather than assuming an unrelated server instance already exists.

The demo SHALL provision a demo-owned working tree for the session under the run root rather than pointing the launched session directly at the repository checkout.

The native launch flow SHALL run with the same demo-owned runtime, registry, jobs, and home roots used for that run, so launch artifacts and related state remain owned by the run root rather than ambient Houmao directories.

Demo startup SHALL use explicit demo-owned startup budgets rather than relying on generic defaults. At minimum, the demo-owned startup profile SHALL include:

- compatibility shell-ready timeout = `20s`
- compatibility provider-ready timeout = `120s`
- compatibility Codex warmup = `10s`
- native headless launch create-timeout = `180s`

The native headless launch create-timeout SHALL remain larger than the bounded demo-owned server compatibility startup chain.

The demo SHALL expose a startup override surface for those timeout values through the demo CLI and shell wrapper so automation can tune them without patching repository code.

When the operator does not provide a provider override, startup SHALL use `claude_code` as the implicit default provider.

When the operator provides `--provider codex`, startup SHALL launch the Codex-backed interactive variant through the same tracked native launch selector.

The tracked native launch selector used by startup SHALL be `gpu-kernel-coder`.

In the first cut, that selector SHALL resolve through the selected tool lane's recipe store rather than through blueprint-by-name matching.

When the operator provides `--session-name`, startup SHALL pass that value as the requested launch name and SHALL derive the persisted `agent_identity` from it.

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

#### Scenario: Default startup uses the tracked Claude provider and native headless launch
- **WHEN** the operator runs the demo startup command without a provider override
- **THEN** the demo launches the interactive session through the demo-owned `houmao-server` native headless launch API
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs instead of running `houmao-mgr install`
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
- **AND THEN** the demo-owned `houmao-server` startup uses the documented demo compatibility startup budgets instead of generic pair defaults
- **AND THEN** the native launch request uses the documented demo create-timeout budget instead of the generic client default
- **AND THEN** the delegated session uses `provider = claude_code`
- **AND THEN** persisted startup state records `tool = claude`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = claude-gpu-kernel-coder`

#### Scenario: Startup accepts an explicit Codex provider
- **WHEN** the operator runs startup with `--provider codex`
- **THEN** the demo launches the interactive session through the demo-owned `houmao-server` native headless launch API
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs instead of compatibility profile install state
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
- **AND THEN** the demo-owned `houmao-server` startup uses the documented demo compatibility startup budgets, including the demo Codex warmup override
- **AND THEN** the native launch request uses the documented demo create-timeout budget instead of the generic client default
- **AND THEN** the delegated session uses `provider = codex`
- **AND THEN** persisted startup state records `tool = codex`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = codex-gpu-kernel-coder`

#### Scenario: Session-name override replaces the default generated identity
- **WHEN** the operator runs startup with `--session-name alice`
- **THEN** the native launch request uses `alice` as the requested launch name
- **AND THEN** persisted startup state records the canonicalized `agent_identity` derived from `alice`

#### Scenario: Pair startup remains owned by the demo run root
- **WHEN** the operator starts the demo for a fresh run root
- **THEN** the native launch flow runs with demo-owned runtime, registry, jobs, and home roots
- **AND THEN** launch artifacts for that run are written under the selected run root rather than ambient Houmao directories

#### Scenario: Operator overrides demo startup budgets
- **WHEN** the operator or automation supplies explicit demo startup timeout overrides
- **THEN** the demo passes those override values into both the demo-owned `houmao-server` startup command and the native launch client request as appropriate
- **AND THEN** the demo does not require source edits to tune the startup budget for slow environments

### Requirement: Startup SHALL rely on pair-managed delegated launch artifacts and auto-registration
After the interactive launch succeeds, the demo SHALL discover the runtime-owned manifest and delegated session artifacts produced by the demo-owned `houmao-server` native headless launch API.

The demo SHALL use the manifest `houmao_server` section as the startup-to-follow-up data bridge.

The demo SHALL persist `session_name` as the stable v1 managed-agent `agent_ref` in demo state and SHALL use that persisted value for post-launch managed-agent routes without requiring a second discovery step.

The demo SHALL resolve the delegated manifest and related session artifacts from the demo-owned runtime root for that run rather than from ambient shared runtime roots.

The demo SHALL NOT send its own extra `POST /houmao/launches/register` after a successful native launch.

The demo MAY additionally persist a later-discovered `tracked_agent_id`, but follow-up commands SHALL NOT depend on discovering it before first use.

#### Scenario: Pair-managed launch auto-registers the delegated session
- **WHEN** the operator completes a successful demo startup
- **THEN** the session launched through the demo-owned `houmao-server` native headless launch API becomes addressable through server-managed discovery and inspection routes
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
