## ADDED Requirements

### Requirement: Dedicated project CLI reference page
The docs site SHALL provide `docs/reference/cli/project.md` covering all `houmao-mgr project` subcommands: `init`, `status`, `agents tools` (claude/codex/gemini with setups and auth subcommands), `agents roles` (with presets), `easy specialist` (create/list/get/remove), `easy instance` (launch/list/get/stop), and `mailbox` (init/status/register/unregister/repair/cleanup/accounts/messages). Each command group SHALL include its purpose, key options, and targeting rules.

#### Scenario: Project page covers all project subcommands
- **WHEN** a user navigates to the project CLI reference page
- **THEN** the page SHALL document every leaf command under `houmao-mgr project` with its purpose and key options

#### Scenario: Project page is discoverable from navigation
- **WHEN** the mkdocs site is built
- **THEN** `project.md` SHALL appear in the CLI reference section sidebar

### Requirement: Dedicated server CLI reference page
The docs site SHALL provide `docs/reference/cli/server.md` covering `houmao-mgr server` subcommands: `start` (with all startup options), `stop`, `status`, and `sessions` (list/show/shutdown). This page documents the manager-side server control commands, distinct from `houmao-server.md` which documents the server binary itself.

#### Scenario: Server mgr commands page exists
- **WHEN** a user looks for houmao-mgr server lifecycle commands
- **THEN** `docs/reference/cli/server.md` SHALL document start, stop, status, and sessions subcommands

### Requirement: Dedicated standalone mailbox CLI reference page
The docs site SHALL provide `docs/reference/cli/mailbox.md` covering `houmao-mgr mailbox` subcommands: `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `accounts` (list/get), and `messages` (list/get). This documents the standalone filesystem mailbox administration surface.

#### Scenario: Standalone mailbox commands page exists
- **WHEN** a user looks for standalone mailbox administration commands
- **THEN** `docs/reference/cli/mailbox.md` SHALL document all mailbox subcommands with options and usage

### Requirement: Dedicated brains CLI reference page
The docs site SHALL provide `docs/reference/cli/brains.md` covering `houmao-mgr brains build` with all build options (`--agent-def-dir`, `--tool`, `--skill`, `--setup`, `--auth`, `--preset`, `--runtime-root`, `--home-id`, `--reuse-home`, `--launch-overrides`, `--agent-name`, `--agent-id`).

#### Scenario: Brains build page exists
- **WHEN** a user looks for brain construction CLI reference
- **THEN** `docs/reference/cli/brains.md` SHALL document the `brains build` command with all options

### Requirement: Dedicated agents-cleanup CLI reference page
The docs site SHALL provide `docs/reference/cli/agents-cleanup.md` covering `houmao-mgr agents cleanup` subcommands: `session`, `logs`, and `mailbox` with their options and dry-run support.

#### Scenario: Agents cleanup page exists
- **WHEN** a user looks for agent-scoped cleanup commands
- **THEN** `docs/reference/cli/agents-cleanup.md` SHALL document session, logs, and mailbox cleanup with options

### Requirement: houmao-mgr.md becomes an overview hub
After dedicated pages are extracted, `docs/reference/cli/houmao-mgr.md` SHALL be slimmed to contain: a command tree showing the full hierarchy, brief one-line descriptions per group, and links to dedicated reference pages. It SHALL NOT duplicate the full option documentation that now lives in dedicated pages.

#### Scenario: Monolith reduced to hub
- **WHEN** a user opens `houmao-mgr.md`
- **THEN** the page SHALL show a command tree with links to dedicated pages and SHALL NOT contain full option lists for extracted command groups

#### Scenario: No information lost
- **WHEN** content is extracted from `houmao-mgr.md` to dedicated pages
- **THEN** every command, option, and behavioral note from the original SHALL appear in exactly one dedicated page
