# Spec Delta

## MODIFIED Requirements

### Requirement: The demo creates provider-specific local auth aliases at run time

The demo SHALL prepare a private external project run from the selected generic API case and materialize its provider-specific credential under a run-local alias such as `default`. Credentials SHALL come from selected local references, without a repository-local auth symlink or personal bundle default. Tracked inputs SHALL remain secret-free.

#### Scenario: Claude run aliases local fixture auth
- **WHEN** an operator runs the demo for `claude_code` with a configured API case
- **THEN** its private project receives a Claude credential derived from that selected case
- **AND THEN** a demo-local `default` credential selection can resolve without a link to the reusable credential source

#### Scenario: Codex run aliases local fixture auth
- **WHEN** an operator runs the demo for `codex` with a configured API case
- **THEN** its private project receives a Codex credential and matching Responses endpoint configuration
- **AND THEN** the tracked preset requires no fixed Yunwu routing or bundle name

#### Scenario: Missing fixture auth fails during preflight
- **WHEN** a selected case is missing a required credential or endpoint input
- **THEN** the demo fails before launching a client
- **AND THEN** the error identifies the missing configuration reference and how to supply it without printing secrets

### Requirement: The demo launches the same role selector through either supported provider

The demo SHALL use the shared `minimal-launch` role for Claude and Codex. It SHALL create a fresh project specialist from the demo's tracked inputs and launch through `houmao-mgr project agents launch`, preserving TUI/headless selection and unattended posture. Follow-up operations SHALL use scoped selected-agent or maintained gateway/passive-server surfaces.

#### Scenario: Claude headless demo run succeeds through the shared role selector
- **WHEN** an operator selects `claude_code` and the headless lane
- **THEN** the prepared project specialist uses the shared `minimal-launch` prompt and Claude seed preset
- **AND THEN** the run launches through the maintained project headless surface

#### Scenario: Codex headless demo run succeeds through the shared role selector
- **WHEN** an operator selects `codex` and the headless lane
- **THEN** the prepared project specialist uses the shared `minimal-launch` prompt and Codex seed preset with selected API routing
- **AND THEN** the run launches through the maintained project headless surface

### Requirement: The demo remains tutorial-shaped and records reproducible outputs

The supported demo SHALL include:
- one tutorial markdown document,
- one tracked prompt input,
- one runnable script,
- one private generated outputs area for the produced working tree and command artifacts.

The tutorial SHALL explain prerequisites, provider and case selection, model/endpoint configuration, generated outputs, verification steps, and common failure modes. It SHALL direct credential setup to local env references or the shared external credential discovery/import flow.

The maintained runner and tutorial SHALL describe one generated project-aware overlay root for each run as the local Houmao-owned state anchor. Credential-bearing outputs SHALL live outside the checkout. The demo SHALL NOT require separate root env overrides for agent-definition and runtime placement merely to keep the run self-contained.

Important generated outputs relative to the private run root SHALL include:
- `workdir/.houmao/agents/`: generated project launch projection
- `workdir/.houmao/runtime/`: built homes, manifests, and session artifacts
- `workdir/.houmao/jobs/`: overlay-local per-session job directories when materialized
- `logs/preflight-stop.log`: scoped best-effort cleanup when explicitly reusing a demo identity
- `logs/launch.log`
- `logs/state.log`
- `summary.json`

Headless-only generated outputs SHALL include:
- `logs/prompt.log`
- `logs/stop.log`

Command logs and summaries SHALL exclude key values and raw auth contents. Explicitly exported shareable summaries SHALL remain separate from private credential-bearing state.

#### Scenario: Reader follows the tutorial document
- **WHEN** a reader opens the minimal demo tutorial
- **THEN** they find its question, prerequisites, implementation idea, supported run commands, representative outputs, verification guidance, and troubleshooting notes
- **AND THEN** the runnable flow points to the tracked script and explains the external private run root

## ADDED Requirements

### Requirement: The minimal demo selects backend cases independently of provider and transport

The runner SHALL expose generic `self-hosted` and `cloud-api` case selection independently of its existing Claude/Codex and TUI/headless choices. Case resolution SHALL use the shared fixture helper and SHALL NOT require editing the tracked demo inputs to switch model or endpoint.

#### Scenario: Same demo lane uses a different backend case
- **WHEN** an operator changes only the configured case for one supported provider/transport lane
- **THEN** the demo preserves its role and transport behavior while resolving the selected model, endpoint, and credential source for the new run
