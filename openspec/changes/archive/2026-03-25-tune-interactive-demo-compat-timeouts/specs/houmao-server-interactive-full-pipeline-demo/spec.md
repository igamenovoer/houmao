## MODIFIED Requirements

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
