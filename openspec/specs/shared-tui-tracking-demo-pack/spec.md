# shared-tui-tracking-demo-pack Specification

## Purpose
Define the supported shared TUI tracking demo-pack surface, its demo-local launch assets, and its run-local agent bootstrap contract.
## Requirements
### Requirement: `scripts/demo/` SHALL publish a supported shared TUI tracking demo pack

The repository SHALL publish a supported runnable shared TUI tracking demo under `scripts/demo/shared-tui-tracking-demo-pack/` and SHALL present it from `scripts/demo/README.md` as part of the maintained demo surface.

Historical material under `scripts/demo/legacy/shared-tui-tracking-demo-pack/` MAY remain as archival reference content, but the maintained operator workflow SHALL point to the supported non-legacy demo location.

#### Scenario: Maintainer inspects the supported demo directory
- **WHEN** a maintainer reads `scripts/demo/README.md`
- **THEN** the README identifies `shared-tui-tracking-demo-pack/` as a supported runnable demo
- **AND THEN** the README continues to treat `legacy/` as archival reference content rather than the maintained operator surface

### Requirement: The restored demo pack SHALL own a tracked secret-free agent-definition tree

The restored demo pack SHALL include a tracked secret-free agent-definition tree under `scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/`.

That tracked tree SHALL use the canonical minimal layout:

- `skills/`
- `roles/<role>/system-prompt.md`
- `roles/<role>/presets/<tool>/<setup>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`

The tracked demo tree SHALL NOT commit plaintext auth contents under `inputs/agents/tools/<tool>/auth/`.

#### Scenario: Maintainer inspects the tracked demo assets
- **WHEN** a maintainer inspects `scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/`
- **THEN** they find the canonical secret-free `skills/`, `roles/`, and `tools/` layout for the restored demo
- **AND THEN** the tracked demo tree does not contain committed plaintext auth bundles

### Requirement: The restored demo SHALL generate a run-local agent-definition directory for each run
Each live-watch or recorded-capture run SHALL generate a local working tree under the run root and SHALL build from a generated agent-definition directory inside that working tree instead of building directly from a repository-wide plain direct-dir fixture root.

The generated agent-definition directory SHALL be derived from the tracked demo-local `inputs/agents/` tree.

#### Scenario: Live watch builds from the generated local agent tree
- **WHEN** an operator starts a live-watch run for Claude or Codex
- **THEN** the workflow creates a generated agent-definition directory under that run’s working tree
- **AND THEN** the runtime build for that run uses the generated local agent-definition directory rather than a repository-wide plain direct-dir fixture root

#### Scenario: Recorded capture builds from the generated local agent tree
- **WHEN** an operator starts a recorded-capture run for one configured scenario
- **THEN** the workflow creates a generated agent-definition directory under that run’s working tree
- **AND THEN** the runtime build for that run uses the generated local agent-definition directory rather than a repository-wide plain direct-dir fixture root

### Requirement: The restored demo SHALL materialize a demo-local `default` auth alias for the selected tool
The restored demo run workflow SHALL create a generated working tree for each run and SHALL materialize one demo-local auth alias named `default` for the selected tool by linking or projecting to a host-local fixture auth bundle under `tests/fixtures/auth-bundles/<tool>/`.

Tracked demo presets MAY therefore continue to declare `auth: default`.

If the expected host-local auth source for the selected tool is absent, the demo SHALL fail before launch with a clear error identifying the missing path.

#### Scenario: Claude run creates a local default auth alias
- **WHEN** an operator starts the restored demo for Claude
- **THEN** the generated working tree contains `tools/claude/auth/default` for that run
- **AND THEN** that alias resolves to one host-local fixture auth source under `tests/fixtures/auth-bundles/claude/`

#### Scenario: Codex run creates a local default auth alias
- **WHEN** an operator starts the restored demo for Codex
- **THEN** the generated working tree contains `tools/codex/auth/default` for that run
- **AND THEN** that alias resolves to one host-local fixture auth source under `tests/fixtures/auth-bundles/codex/`

#### Scenario: Missing local auth source fails during preflight
- **WHEN** an operator starts the restored demo for one supported tool
- **AND WHEN** the expected host-local fixture auth source for that tool is absent
- **THEN** the demo fails before launch
- **AND THEN** the error identifies the missing auth source path

### Requirement: The restored demo pack SHALL support Kimi as a first-class demo tool
The restored shared TUI tracking demo pack SHALL admit `kimi` as a supported tool alongside Claude and Codex in demo-local type catalogs, command routing, run manifests, fixture manifests, scenario definitions, ownership metadata, and tests.

The Kimi demo tool SHALL use the shared tracker app id resolved by the normal registry mapping for `tool = kimi`; it SHALL NOT introduce a demo-only detector path or refer to the `kimi_headless` backend name as the tracker app id.

#### Scenario: Maintainer starts a Kimi demo workflow
- **WHEN** a maintainer invokes a supported shared TUI tracking demo workflow with `tool = kimi`
- **THEN** the workflow accepts Kimi as a supported demo tool
- **AND THEN** persisted run metadata records the tool as `kimi`
- **AND THEN** tracker resolution uses the normal `kimi_code` shared tracker profile family

### Requirement: The restored demo pack SHALL include secret-free Kimi launch assets
The restored demo pack SHALL include secret-free Kimi agent-definition assets under `scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/`.

Those assets SHALL include a Kimi tool adapter compatible with the current Kimi brain-builder contract, a default Kimi setup directory, and an `interactive-watch-kimi-default.yaml` preset that launches Kimi through the demo-local `default` auth alias.

The tracked Kimi assets SHALL NOT commit plaintext Kimi OAuth credentials, Kimi API keys, or user-global Kimi Code state.

#### Scenario: Maintainer inspects Kimi demo assets
- **WHEN** a maintainer inspects the demo-local tracked agent-definition tree
- **THEN** it contains Kimi adapter and preset assets sufficient for a Kimi interactive-watch launch
- **AND THEN** the tracked tree contains no plaintext Kimi credential material

### Requirement: The restored demo SHALL materialize a Kimi default auth alias from host-local state
The restored demo run workflow SHALL materialize `tools/kimi/auth/default` in the generated run-local agent-definition tree from a host-local Kimi auth bundle.

The default Kimi auth-bundle convention SHALL be documented and SHALL support importing or linking a logged-in Kimi Code home without committing secrets. At minimum, the documented bundle shape SHALL cover `config.toml`, `credentials/kimi-code.json`, and optional Kimi env values accepted by the Kimi adapter.

If the expected host-local Kimi auth source is absent, the workflow SHALL fail before launching tmux and SHALL identify the missing path.

#### Scenario: Kimi run creates a local default auth alias
- **WHEN** an operator starts the restored demo for Kimi and the expected host-local Kimi auth bundle exists
- **THEN** the generated working tree contains `tools/kimi/auth/default` for that run
- **AND THEN** the alias resolves to the host-local Kimi auth source

#### Scenario: Missing Kimi auth source fails during preflight
- **WHEN** an operator starts the restored demo for Kimi
- **AND WHEN** the expected host-local Kimi auth bundle is absent
- **THEN** the demo fails before launching tmux
- **AND THEN** the error identifies the missing Kimi auth source path

### Requirement: Kimi demo process metadata SHALL recognize `kimi-code` and `kimi`
The restored demo pack SHALL recognize live Kimi TUI processes for runtime observations and deliberate diagnostics-loss actions.

The maintained Kimi process-name set for the demo SHALL include both `kimi-code` and `kimi`.

#### Scenario: Runtime observation sees a Kimi Code process
- **WHEN** a demo-owned tmux pane process tree contains a Kimi TUI process named `kimi-code`
- **THEN** runtime observation reports a supported Kimi process pid as alive

#### Scenario: Runtime observation sees a Kimi executable process
- **WHEN** a demo-owned tmux pane process tree contains a Kimi TUI process named `kimi`
- **THEN** runtime observation reports a supported Kimi process pid as alive

