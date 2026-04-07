## ADDED Requirements

### Requirement: CLI reference removes retired `--yolo` launch option from all pages

The CLI reference SHALL NOT present `--yolo` as a supported option on `houmao-mgr agents launch`, `houmao-mgr project easy instance launch`, or any other live launch surface. Any remaining `--yolo` references in `docs/reference/cli/houmao-mgr.md`, `docs/reference/cli/agents-gateway.md`, `docs/reference/cli/system-skills.md`, or other CLI reference pages SHALL be removed during this resync pass.

The CLI reference SHALL state that prompt-mode posture is now controlled exclusively through `launch.prompt_mode` in stored profiles (`unattended` or `as_is`) and the corresponding launch-profile flags, not through a separate `--yolo` toggle.

#### Scenario: Reader does not see `--yolo` as a current option in CLI reference

- **WHEN** a reader greps the CLI reference pages for `--yolo`
- **THEN** zero matches appear as supported options on live launch commands
- **AND THEN** any remaining mention is in an explicit "removed in 0.3.x" or migration-note context

#### Scenario: Reader learns the current way to control prompt-mode posture

- **WHEN** a reader looks up how to launch an agent without provider startup prompts
- **THEN** the CLI reference points the reader at `launch.prompt_mode: unattended` in stored profiles or the equivalent launch-profile flags
- **AND THEN** the reference does not present `--yolo` as the way to achieve that posture

### Requirement: CLI reference documents the unified `--model` selection on launch surfaces

The `houmao-mgr` CLI reference SHALL document `--model` as a unified model-selection flag on the relevant managed launch and launch-profile commands.

At minimum, that coverage SHALL include the launch surfaces that accept model selection directly (`houmao-mgr agents launch`, `houmao-mgr project easy specialist create`, `houmao-mgr project easy instance launch`, and the corresponding `project agents launch-profiles` administration commands when those commands accept stored model defaults).

That coverage SHALL describe `--model` as a tool-agnostic selector that resolves to the appropriate per-tool model identifier through the supported provider mapping, and SHALL state that `--model` does not bypass tool authentication or provider configuration.

That coverage SHALL link to the underlying tool-specific model identifiers documented in the relevant tool reference rather than restating every supported model name on the CLI reference page.

#### Scenario: Reader finds the unified `--model` flag on the launch surfaces

- **WHEN** a reader looks up `houmao-mgr agents launch` or `project easy instance launch`
- **THEN** the CLI reference documents `--model` as a current option
- **AND THEN** the page explains that `--model` is a tool-agnostic selector resolved through the provider mapping

#### Scenario: Reader understands that `--model` is not an auth or provider override

- **WHEN** a reader looks up the `--model` flag
- **THEN** the CLI reference states that `--model` does not bypass tool authentication or provider configuration

### Requirement: CLI reference for `agents mail` reflects the unified email-comms skill boundary

The CLI reference page `docs/reference/cli/agents-mail.md` SHALL describe the current `agents mail` command surface as the operator-facing mailbox follow-up family that pairs with the unified `houmao-agent-email-comms` packaged system skill.

That page SHALL state that ordinary shared-mailbox operations and no-gateway fallback guidance live in `houmao-agent-email-comms`, while notifier-driven unread-mail rounds live in `houmao-process-emails-via-gateway`. It SHALL NOT continue to describe the pre-unification split-mailbox skill names as current packaged skills.

That page SHALL keep the documented subcommands (`resolve-live`, `status`, `check`, `send`, `reply`, `mark-read`) accurate to the current `srv_ctrl/commands/agents/mail.py` Click decorators, and SHALL preserve the existing targeting-rules and authority-aware result semantics requirements from the prior pass.

#### Scenario: agents-mail page references the unified email-comms skill

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** the page describes `houmao-agent-email-comms` as the unified ordinary mailbox-operations skill paired with the `agents mail` family
- **AND THEN** the page does not list the pre-unification split skill names as current

#### Scenario: agents-mail subcommand list still matches the live CLI

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** the page documents `resolve-live`, `status`, `check`, `send`, `reply`, and `mark-read`
- **AND THEN** the option tables match the current `srv_ctrl/commands/agents/mail.py` Click decorators

### Requirement: CLI reference resync against current Click decorators for stale `agents` and `admin` pages

The CLI reference pages `docs/reference/cli/agents-mailbox.md`, `docs/reference/cli/agents-turn.md`, `docs/reference/cli/admin-cleanup.md`, and `docs/reference/cli/houmao-server.md` SHALL be reverified against the current Click decorators in `src/houmao/srv_ctrl/commands/` (and `src/houmao/server/commands/` for the server page) and updated to match the live CLI shape as of this change.

For each of those pages:

- the documented subcommands SHALL match the live Click groups,
- the option tables SHALL list every flag exposed by the current decorators with the current default values,
- removed or renamed flags from the post-`2026-04-04` feature commits SHALL be removed or renamed in the docs accordingly,
- existing prose that remains accurate SHALL be preserved.

#### Scenario: agents-mailbox option tables match current Click decorators

- **WHEN** a reader opens `docs/reference/cli/agents-mailbox.md`
- **THEN** every option in the option tables corresponds to a current Click decorator in `srv_ctrl/commands/agents/mailbox.py`
- **AND THEN** no removed or renamed option remains in the page

#### Scenario: agents-turn page reflects current submit/inspect commands

- **WHEN** a reader opens `docs/reference/cli/agents-turn.md`
- **THEN** the documented subcommands match the live Click groups in `srv_ctrl/commands/agents/turn.py`
- **AND THEN** the option tables match current decorators

#### Scenario: admin-cleanup page reflects current registry and runtime commands

- **WHEN** a reader opens `docs/reference/cli/admin-cleanup.md`
- **THEN** the documented subcommands match the live Click groups in `srv_ctrl/commands/admin.py`
- **AND THEN** the option tables match current decorators

#### Scenario: houmao-server page reflects current server commands

- **WHEN** a reader opens `docs/reference/cli/houmao-server.md`
- **THEN** the documented subcommands match the live Click groups in `src/houmao/server/commands/`
- **AND THEN** the option tables match current decorators

### Requirement: CLI reference cross-links the managed prompt header reference page

The `houmao-mgr` CLI reference and the relevant launch-surface coverage in `docs/reference/cli/houmao-mgr.md` SHALL link to the managed prompt header reference page (`docs/reference/run-phase/managed-prompt-header.md`) wherever they document `--managed-header`, `--no-managed-header`, or related stored launch-profile policy flags.

The link SHALL be a direct cross-reference, not a tooltip or footnote, so a reader looking up the flag from the CLI reference can navigate in one click to the conceptual page that explains what the header contains.

#### Scenario: Reader can navigate from `--managed-header` flag coverage to the conceptual page

- **WHEN** a reader looks up `--managed-header` or `--no-managed-header` on `agents launch` in the CLI reference
- **THEN** the page contains a direct link to `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the link is presented inline with the flag coverage rather than only at the bottom of the page

### Requirement: CLI reference cross-links the system-skills overview guide

The CLI reference page `docs/reference/cli/system-skills.md` SHALL link to the new getting-started guide `docs/getting-started/system-skills-overview.md` from its introduction so that readers reaching the reference page have a single click into the narrative tour.

#### Scenario: Reader can navigate from system-skills CLI reference to the narrative overview

- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the introduction or top section of the page contains a link to `docs/getting-started/system-skills-overview.md`
- **AND THEN** the link is presented as a "see also" or "narrative overview" pointer rather than buried in the bottom of the page
