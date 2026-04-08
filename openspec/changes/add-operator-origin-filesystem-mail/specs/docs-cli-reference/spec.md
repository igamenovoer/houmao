## MODIFIED Requirements

### Requirement: CLI reference for `agents mail` reflects the unified email-comms skill boundary

The CLI reference page `docs/reference/cli/agents-mail.md` SHALL describe the current `agents mail` command surface as the operator-facing mailbox follow-up family that pairs with the unified `houmao-agent-email-comms` packaged system skill.

That page SHALL state that ordinary shared-mailbox operations and no-gateway fallback guidance live in `houmao-agent-email-comms`, while notifier-driven unread-mail rounds live in `houmao-process-emails-via-gateway`. It SHALL NOT continue to describe the pre-unification split-mailbox skill names as current packaged skills.

That page SHALL keep the documented subcommands (`resolve-live`, `status`, `check`, `send`, `post`, `reply`, `mark-read`) accurate to the current `srv_ctrl/commands/agents/mail.py` Click decorators, and SHALL preserve the existing targeting-rules and authority-aware result semantics requirements from the prior pass.

That page SHALL explain that:

- ordinary `send` remains mailbox participation as the managed mailbox principal,
- `post` is the distinct operator-origin one-way mailbox action,
- operator-origin `post` uses the reserved sender `HOUMAO-operator@houmao.localhost`,
- operator-origin `post` is supported only for filesystem-backed mailboxes in v1.

#### Scenario: agents-mail page references the unified email-comms skill

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** the page describes `houmao-agent-email-comms` as the unified ordinary mailbox-operations skill paired with the `agents mail` family
- **AND THEN** the page does not list the pre-unification split skill names as current

#### Scenario: agents-mail subcommand list still matches the live CLI

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** the page documents `resolve-live`, `status`, `check`, `send`, `post`, `reply`, and `mark-read`
- **AND THEN** the option tables match the current `srv_ctrl/commands/agents/mail.py` Click decorators

#### Scenario: agents-mail page distinguishes ordinary send from operator-origin post

- **WHEN** a reader opens `docs/reference/cli/agents-mail.md`
- **THEN** the page explains that `send` composes mail as the managed mailbox principal while `post` delivers one-way operator-origin mail
- **AND THEN** the page identifies `HOUMAO-operator@houmao.localhost` as the reserved sender for `post`
- **AND THEN** the page states that `post` is filesystem-only in v1

