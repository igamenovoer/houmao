# minimal-agent-launch-demo Specification

## Purpose
Define the maintained minimal runnable demo surface, its tracked agent assets, and the overlay-local execution contract used for the tutorial workflow.

## Requirements

### Requirement: `scripts/demo/` publishes a supported minimal launch tutorial surface

The repository SHALL publish one supported runnable tutorial demo under `scripts/demo/minimal-agent-launch/` and SHALL present it from `scripts/demo/README.md` as the maintained demo surface. Historical material under `scripts/demo/legacy/` SHALL remain clearly labeled as archived reference content.

#### Scenario: Maintainer inspects the top-level demo directory
- **WHEN** a maintainer reads `scripts/demo/README.md`
- **THEN** the README identifies `minimal-agent-launch/` as a supported runnable demo
- **AND THEN** it identifies `legacy/` as archived historical material rather than the primary demo surface

### Requirement: The tracked demo assets use the canonical minimal agent-definition layout

The tracked minimal demo SHALL include only the secret-free files needed to explain the canonical preset-backed launch shape:
- `inputs/agents/skills/`
- `inputs/agents/roles/minimal-launch/system-prompt.md`
- `inputs/agents/presets/minimal-launch-claude-default.yaml`
- `inputs/agents/presets/minimal-launch-codex-default.yaml`
- `inputs/agents/tools/claude/adapter.yaml`
- `inputs/agents/tools/claude/setups/default/...`
- `inputs/agents/tools/codex/adapter.yaml`
- `inputs/agents/tools/codex/setups/default/...`

The tracked demo tree SHALL NOT commit plaintext auth contents under `inputs/agents/tools/<tool>/auth/`.

#### Scenario: Maintainer inspects the tracked demo tree
- **WHEN** a maintainer inspects `scripts/demo/minimal-agent-launch/inputs/agents/`
- **THEN** they find the canonical `skills/`, `roles/`, `presets/`, and `tools/` layout for one shared role with Claude and Codex presets
- **AND THEN** the tracked tree does not contain committed plaintext auth bundles

### Requirement: The demo creates provider-specific local auth aliases at run time

The demo run workflow SHALL create a generated working tree under the demo output root and SHALL materialize one demo-local auth alias named `default` for the selected provider by symlinking to the corresponding local fixture auth bundle under `tests/fixtures/agents/tools/<tool>/auth/`.

#### Scenario: Claude run aliases local fixture auth
- **WHEN** an operator runs the demo for provider `claude_code`
- **THEN** the generated working tree contains `tools/claude/auth/default` as a symlink to `tests/fixtures/agents/tools/claude/auth/kimi-coding`
- **AND THEN** the tracked Claude preset may continue to declare `auth: default`

#### Scenario: Codex run aliases local fixture auth
- **WHEN** an operator runs the demo for provider `codex`
- **THEN** the generated working tree contains `tools/codex/auth/default` as a symlink to `tests/fixtures/agents/tools/codex/auth/yunwu-openai`
- **AND THEN** the tracked Codex preset may continue to declare `auth: default`

#### Scenario: Missing fixture auth fails during preflight
- **WHEN** an operator runs the demo for one provider
- **AND WHEN** the expected source fixture auth bundle for that provider is absent on the host
- **THEN** the demo fails before launch with a clear error identifying the missing fixture auth path

### Requirement: The demo launches the same role selector through either supported provider

The demo SHALL use one shared role selector, `minimal-launch`, and SHALL support launching that role through either `claude_code` or `codex` in headless mode via `houmao-mgr agents launch`.

#### Scenario: Claude headless demo run succeeds through the shared role selector
- **WHEN** an operator runs the supported demo for provider `claude_code`
- **THEN** the demo launches `houmao-mgr agents launch` using selector `minimal-launch`
- **AND THEN** the resolved preset comes from `presets/minimal-launch-claude-default.yaml`
- **AND THEN** the launch runs in headless mode

#### Scenario: Codex headless demo run succeeds through the shared role selector
- **WHEN** an operator runs the supported demo for provider `codex`
- **THEN** the demo launches `houmao-mgr agents launch` using selector `minimal-launch`
- **AND THEN** the resolved preset comes from `presets/minimal-launch-codex-default.yaml`
- **AND THEN** the launch runs in headless mode

### Requirement: The demo remains tutorial-shaped and records reproducible outputs

The supported demo SHALL include:
- one tutorial markdown document,
- one tracked prompt input,
- one runnable script,
- one generated outputs area for the produced working tree and command artifacts.

The tutorial SHALL explain prerequisites, the provider selection input, the generated outputs, verification steps, and common failure modes.

The maintained runner and tutorial SHALL describe one generated project-aware overlay root for each run as the local Houmao-owned state anchor. The maintained demo SHALL NOT require separate root env overrides for agent-definition and runtime placement merely to keep the run self-contained.

Important generated outputs for every lane SHALL include:
- `workdir/.houmao/agents/`: generated launch tree with the demo-local auth alias
- `workdir/.houmao/runtime/`: built homes, manifests, and session artifacts
- `workdir/.houmao/jobs/`: overlay-local per-session job directories when the run materializes them
- `logs/preflight-stop.log`: best-effort cleanup of a stale agent with the same demo name
- `logs/launch.log`
- `logs/state.log`
- `summary.json`

Headless-only generated outputs SHALL include:
- `logs/prompt.log`
- `logs/stop.log`

#### Scenario: Reader follows the tutorial document
- **WHEN** a reader opens the minimal demo tutorial
- **THEN** they find an explicit question, prerequisites, implementation idea, run command, representative outputs, verification guidance, and troubleshooting notes
- **AND THEN** the full runnable flow points to the tracked script rather than embedding the entire implementation inline

### Requirement: The minimal demo uses one generated overlay root for local Houmao-owned state

The maintained `scripts/demo/minimal-agent-launch/` runner SHALL select one generated overlay root for each run and rely on that overlay-local default contract for agent definitions, runtime state, and jobs placement.

The maintained runner MAY continue to use one explicit `HOUMAO_PROJECT_OVERLAY_DIR` override to point the CLI at that generated overlay when the selected output root is outside the repository tree, but it SHALL NOT require separate agent-definition or runtime-root env overrides only to keep the demo self-contained.

#### Scenario: One overlay selector anchors the generated run tree
- **WHEN** an operator runs the maintained minimal demo for any supported lane
- **THEN** the generated run tree selects one project-aware overlay root under that lane's output root
- **AND THEN** the launch resolves agent definitions, runtime state, and jobs state from that one selected overlay rather than from separate root env overrides
