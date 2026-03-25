## MODIFIED Requirements

### Requirement: Repository SHALL provide a standalone Houmao-server interactive full-pipeline demo pack under `scripts/demo/`
The repository SHALL include a demo-pack directory at `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `launch_alice.sh`
- `send_prompt.sh`
- `stop_demo.sh`

The pack SHALL expose the tracked native agent-definition inputs needed for pair-managed startup at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`.

That `agents` entry SHALL be a repository-tracked symlink that resolves to `tests/fixtures/agents/`.

The pack SHALL implement its own workflow and SHALL NOT delegate post-launch interaction to the older CAO interactive demo pack.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-interactive-full-pipeline-demo/`
- **THEN** the required files are present
- **AND THEN** the startup `agents` entry is present
- **AND THEN** that `agents` entry resolves to `tests/fixtures/agents/`
- **AND THEN** the pack can be understood and run from that directory without depending on sibling demo wrappers for its core workflow

### Requirement: Demo startup SHALL use pair-managed native-selector launch with a demo-owned `houmao-server`
The startup workflow SHALL resolve one tracked native launch selector under the demo-local agent-definition root at `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`, launch one detached TUI session through the explicit compatibility surface `houmao-mgr cao launch --headless`, and persist the selected demo variant in local demo state.

The demo-local `agents` path SHALL resolve to `tests/fixtures/agents/` through the tracked symlink shipped with the demo pack.

Demo startup SHALL NOT require a separate `houmao-mgr install` step or a tracked compatibility profile Markdown file as its startup source of truth.

The demo SHALL provision one demo-owned `houmao-server` listener on loopback for the run and SHALL persist the resolved `api_base_url` in demo state rather than assuming an unrelated server instance already exists.

The demo SHALL provision a demo-owned working tree for the session under the run root rather than pointing the launched session directly at the repository checkout.

The detached launch subprocess SHALL run with the same demo-owned runtime, registry, jobs, and home roots used for that run, so delegated artifacts and related state remain owned by the run root rather than ambient Houmao directories.

Demo startup SHALL use explicit demo-owned compatibility startup budgets rather than relying on the generic pair defaults. At minimum, the demo-owned startup profile SHALL include:

- compatibility shell-ready timeout = `20s`
- compatibility provider-ready timeout = `120s`
- compatibility Codex warmup = `10s`
- detached compatibility create timeout = `180s`

The detached compatibility create timeout SHALL remain larger than the bounded demo-owned server compatibility startup chain.

The demo SHALL expose a startup override surface for those demo-owned compatibility timeout values through the demo CLI and shell wrapper so automation can tune them without patching repository code.

When the operator does not provide a provider override, startup SHALL use `claude_code` as the implicit default provider.

When the operator provides `--provider codex`, startup SHALL launch the Codex-backed interactive variant through the same tracked native launch selector.

The tracked native launch selector used by startup SHALL be `gpu-kernel-coder`.

In the first cut, that selector SHALL resolve through the selected tool lane's recipe store rather than through blueprint-by-name matching.

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

#### Scenario: Default startup uses the tracked Claude provider and detached native-selector launch
- **WHEN** the operator runs the demo startup command without a provider override
- **THEN** the demo launches the interactive session through `houmao-mgr cao launch --headless`
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs instead of running `houmao-mgr install`
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
- **AND THEN** the demo-owned `houmao-server` startup uses the documented demo compatibility startup budgets instead of generic pair defaults
- **AND THEN** the detached launch uses the documented demo create-timeout budget instead of the generic pair default
- **AND THEN** the delegated session uses `provider = claude_code`
- **AND THEN** persisted startup state records `tool = claude`
- **AND THEN** persisted startup state records `agent_profile = gpu-kernel-coder`
- **AND THEN** persisted startup state records `variant_id = claude-gpu-kernel-coder`

#### Scenario: Startup accepts an explicit Codex provider
- **WHEN** the operator runs startup with `--provider codex`
- **THEN** the demo launches the interactive session through `houmao-mgr cao launch --headless`
- **AND THEN** startup resolves the tracked `gpu-kernel-coder` selector from native agent-definition inputs instead of compatibility profile install state
- **AND THEN** those startup assets are resolved through `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- **AND THEN** that demo-local path resolves to `tests/fixtures/agents/` through the tracked symlink
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
- **THEN** the detached launch command runs with demo-owned runtime, registry, jobs, and home roots
- **AND THEN** delegated launch artifacts for that run are written under the selected run root rather than ambient Houmao directories

#### Scenario: Operator overrides demo compatibility startup budgets
- **WHEN** the operator or automation supplies explicit demo startup timeout overrides
- **THEN** the demo passes those override values into both the demo-owned `houmao-server` startup command and the detached `houmao-mgr cao launch --headless` command as appropriate
- **AND THEN** the demo does not require source edits to tune the startup budget for slow environments
