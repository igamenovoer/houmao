# docs-cli-reference Specification

## Purpose
Define the documentation requirements for Houmao CLI reference content.

## Requirements

### Requirement: houmao-mgr reference documents all command groups

The CLI reference SHALL include a page for `houmao-mgr` documenting its active command groups (`admin`, `agents`, `brains`, `mailbox`, `project`, and `server`) with subcommand summaries derived from `srv_ctrl/commands/` module docstrings, Click decorators, and live help output.

The CLI reference SHALL make the major nested managed-agent and project command families discoverable either inline or through dedicated linked pages. At minimum, that coverage SHALL include:

- `agents launch`, `join`, `list`, `state`, `prompt`, `stop`, `interrupt`, and `relaunch`,
- `agents turn`,
- `agents gateway`,
- `agents mail`,
- `agents mailbox`,
- `agents cleanup`,
- `project agents`,
- `project easy`,
- `project mailbox`,
- `admin cleanup`.

#### Scenario: Reader finds current agent lifecycle and project command groups

- **WHEN** a reader looks up `houmao-mgr`
- **THEN** they find documented subcommands for `agents`, `brains`, `mailbox`, `project`, `server`, and `admin`
- **AND THEN** the CLI reference does not present removed or outdated project group names such as `agent-tools` as the supported public project surface

#### Scenario: Reader can discover nested managed-agent and project command families

- **WHEN** a reader needs details for `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `project agents`, `project easy`, `project mailbox`, or `admin cleanup`
- **THEN** the CLI reference provides a direct path to formal reference coverage for those nested families
- **AND THEN** the reader does not need to reconstruct those command surfaces only from source code or scattered prose pages

#### Scenario: Reader finds brain management commands

- **WHEN** a reader looks up `houmao-mgr brains`
- **THEN** they find documented subcommands for load, list, and build operations

### Requirement: houmao-server reference documents serve and query commands

The CLI reference SHALL include a page for `houmao-server` documenting its commands (`serve`, `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`) derived from `server/commands/` module docstrings and live help output.

The `serve` reference SHALL describe the implemented startup behavior and the current flag surface, including compatibility readiness and warmup flags when those flags are present in the live CLI.

#### Scenario: Reader understands server startup

- **WHEN** a reader looks up `houmao-server serve`
- **THEN** they find the current startup behavior plus the live configuration options for startup-child behavior, compatibility readiness timeouts or poll intervals, warmup timing, runtime root, API base URL, and supported TUI process overrides

#### Scenario: Reader finds query commands

- **WHEN** a reader looks up `houmao-server` query commands
- **THEN** they find documented coverage for `health`, `current-instance`, `register-launch`, `sessions`, and `terminals`
- **AND THEN** the page reflects the current command tree rather than a partial or stale subset

### Requirement: houmao-passive-server reference documents registry-driven model

The CLI reference SHALL include a page for `houmao-passive-server` documenting its registry-driven discovery model, serve command, and API surface derived from `passive_server/` module docstrings. The page SHALL position passive-server as the clean, CAO-free server path.

#### Scenario: Reader understands passive vs active server difference

- **WHEN** a reader compares passive-server and houmao-server pages
- **THEN** they understand that passive-server is stateless/registry-driven with no CAO dependency, while houmao-server is the CAO-compatible path

### Requirement: Deprecated entrypoints noted briefly

The CLI reference SHALL note that `houmao-cli` and `houmao-cao-server` are deprecated compatibility entrypoints. This SHALL be a brief note (1–2 sentences), not a full page.

#### Scenario: Deprecated CLIs not prominently featured

- **WHEN** a reader scans the CLI reference section
- **THEN** `houmao-cli` and `houmao-cao-server` appear only as deprecation notes, not as primary documentation

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference docs that describe agent-definition-directory resolution for active commands, or that mention deprecated compatibility entrypoints, SHALL describe ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. default fallback `<cwd>/.houmao/agents`.

When the CLI reference explains the discovered project path, it SHALL describe `.houmao/houmao-config.toml` as the overlay discovery anchor and `.houmao/agents/` as the compatibility projection used by file-tree consumers.
It SHALL NOT present `<cwd>/.agentsys/agents` as a supported default or fallback path.
The CLI reference SHALL keep `houmao-cli` and `houmao-cao-server` in explicit deprecation-only posture rather than re-elevating them to primary operator workflows.

#### Scenario: Reader sees `.houmao` ambient fallback in the CLI reference
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes the `.houmao`-based precedence contract
- **AND THEN** it does not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Deprecated entrypoints remain deprecation-only while using current precedence
- **WHEN** a reader scans the CLI reference for mentions of `houmao-cli` or `houmao-cao-server`
- **THEN** those mentions remain brief legacy and deprecation notes
- **AND THEN** any documented ambient agent-definition resolution uses the `.houmao`-based fallback contract rather than preserving `.agentsys`
