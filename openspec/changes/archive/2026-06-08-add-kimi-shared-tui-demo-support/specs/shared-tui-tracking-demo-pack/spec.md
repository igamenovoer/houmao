## ADDED Requirements

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
