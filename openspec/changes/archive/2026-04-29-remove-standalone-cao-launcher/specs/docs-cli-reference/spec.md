## ADDED Requirements

### Requirement: CLI reference lists only retained server binaries
The CLI reference SHALL present `houmao-server` and `houmao-passive-server` as the retained server binaries.

The CLI reference SHALL NOT list `houmao-cao-server` as an active, deprecated, or installable package entrypoint. Historical references MAY mention the removed launcher only when explicitly framed as removed history or migration context.

#### Scenario: Reader sees retained server binaries
- **WHEN** a reader scans CLI reference entrypoint tables or server comparison sections
- **THEN** the retained server binaries are `houmao-server` and `houmao-passive-server`
- **AND THEN** `houmao-cao-server` is not presented as a command the current package installs

## MODIFIED Requirements

### Requirement: houmao-server reference documents serve and query commands
The CLI reference SHALL include a page for `houmao-server` documenting its commands (`serve`, `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`) derived from `server/commands/` module docstrings and live help output.

The `serve` reference SHALL describe the implemented startup behavior and the current flag surface, including compatibility readiness and warmup flags when those flags are present in the live CLI. It SHALL NOT document child-CAO startup flags or child-CAO process configuration.

#### Scenario: Reader understands server startup

- **WHEN** a reader looks up `houmao-server serve`
- **THEN** they find the current startup behavior plus the live configuration options for compatibility readiness timeouts or poll intervals, warmup timing, runtime root, API base URL, and supported TUI process overrides
- **AND THEN** they do not find `startup-child` options documented as live configuration

#### Scenario: Reader finds query commands

- **WHEN** a reader looks up `houmao-server` query commands
- **THEN** they find documented coverage for `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`
- **AND THEN** the page reflects the current command tree rather than a partial or stale subset

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference docs that describe agent-definition-directory resolution for active commands, or that mention deprecated or removed compatibility entrypoints, SHALL describe ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `HOUMAO_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. ambient project-overlay discovery controlled by `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`,
5. default fallback `<cwd>/.houmao/agents`.

When the CLI reference describes `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, it SHALL state that:

- `ancestor` is the default mode,
- `ancestor` resolves the nearest ancestor `.houmao/houmao-config.toml`,
- `cwd_only` restricts ambient lookup to `<cwd>/.houmao/houmao-config.toml`,
- the mode affects ambient discovery only and does not override `HOUMAO_PROJECT_OVERLAY_DIR`.

The CLI reference SHALL describe `HOUMAO_PROJECT_OVERLAY_DIR` as an absolute-path env override that selects the overlay directory directly for CI and controlled automation.
When the CLI reference explains the discovered project path, it SHALL describe `houmao-config.toml` as the discovery anchor at the selected overlay root and `agents/` as the compatibility projection used by file-tree consumers beneath that overlay root.
It SHALL NOT present `<cwd>/.agentsys/agents` as a supported default or fallback path.
The CLI reference SHALL keep `houmao-cli` in explicit deprecation-only posture and SHALL keep `houmao-cao-server` only in explicit removed, historical, or migration context rather than presenting either surface as an active operator workflow.

#### Scenario: Reader sees the project-overlay env contract in the CLI precedence documentation
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes `HOUMAO_PROJECT_OVERLAY_DIR` as the explicit overlay-root selector
- **AND THEN** the page describes `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` as the ambient discovery-mode selector used only when no explicit overlay root is set
- **AND THEN** the page explains the `ancestor` and `cwd_only` modes

#### Scenario: Reader sees `.houmao` ambient fallback in the CLI reference
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes the `.houmao`-based precedence contract
- **AND THEN** it explains that cwd-only mode still falls back to `<cwd>/.houmao/agents`
- **AND THEN** it does not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Deprecated and removed entrypoints remain historical while using current precedence
- **WHEN** a reader scans the CLI reference for mentions of `houmao-cli` or `houmao-cao-server`
- **THEN** `houmao-cli` remains a brief deprecated compatibility note where needed
- **AND THEN** `houmao-cao-server` appears only as a removed historical launcher, not as an installable current command
- **AND THEN** any documented ambient agent-definition resolution uses the current `.houmao` precedence contract including the discovery-mode env rather than preserving `.agentsys`

## REMOVED Requirements

### Requirement: Deprecated entrypoints noted briefly
**Reason**: `houmao-cao-server` is no longer a packaged deprecated entrypoint after this change, so the docs must not require it to appear as a current deprecated command.

**Migration**: Keep `houmao-cli` deprecation notes where relevant. Mention `houmao-cao-server` only as removed history or migration context, and point server workflows to `houmao-server`, `houmao-passive-server`, and `houmao-mgr server`.

#### Scenario: Deprecated server launcher note is removed
- **WHEN** a reader scans the active CLI reference section
- **THEN** `houmao-cao-server` is not listed as a deprecated command installed by the current package
- **AND THEN** retained server workflow documentation points to `houmao-server` and `houmao-passive-server`
