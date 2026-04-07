## ADDED Requirements

### Requirement: README skill catalog lists the unified email-comms skill

The `README.md` system-skills subsection SHALL list `houmao-agent-email-comms` as one of the packaged skill families, alongside the existing entries documented by the prior pass.

The catalog row SHALL describe `houmao-agent-email-comms` as the ordinary shared-mailbox operations skill that pairs with `houmao-process-emails-via-gateway` (which handles notifier-driven unread-mail rounds).

The README SHALL NOT continue to describe the pre-unification split mailbox skill names as the current packaged skills.

#### Scenario: Reader sees the unified email-comms skill in the README catalog

- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find a row for `houmao-agent-email-comms` with a one-line description
- **AND THEN** the row distinguishes ordinary mailbox operations from notifier-driven unread-mail rounds

#### Scenario: README skill catalog does not list pre-unification split skill names as current

- **WHEN** a reader greps the README system-skills subsection for the pre-unification split mailbox skill names
- **THEN** none of those names appear as current packaged skills

### Requirement: README mentions the managed prompt header in the join/launch outcome

The `README.md` "What You Get After Joining" section (or the equivalent section that summarizes the operator-facing capabilities of a managed agent) SHALL include one short note explaining that managed launches and joins prepend a Houmao-owned prompt header by default, and SHALL link to the new managed prompt header reference page (`docs/reference/run-phase/managed-prompt-header.md`).

The note SHALL state that the header is opt-out via `--no-managed-header` on the launch surfaces and is persisted in stored launch profiles, deferring the full explanation to the linked reference page.

#### Scenario: Reader notices the managed prompt header from the README

- **WHEN** a reader scans the README "What You Get After Joining" section
- **THEN** they find one short note explaining that managed launches prepend a Houmao-owned prompt header by default
- **AND THEN** the note links to `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the note states that the header is opt-out via `--no-managed-header`

### Requirement: README CLI Entry Points table reflects `houmao-mgr --version`

The `README.md` CLI Entry Points table (or the equivalent paragraph that introduces `houmao-mgr`) SHALL note the existence of the `houmao-mgr --version` flag, either as a dedicated row, a footnote on the `houmao-mgr` row, or an inline mention immediately following the table.

The note SHALL state that `houmao-mgr --version` prints the packaged Houmao version and exits successfully without requiring a subcommand.

#### Scenario: Reader can find `--version` from the README CLI entry-points coverage

- **WHEN** a reader scans the README CLI Entry Points section
- **THEN** they see a mention of `houmao-mgr --version`
- **AND THEN** the mention explains what the flag prints and that it does not require a subcommand

### Requirement: README default-install paragraph matches current system_skills.py defaults

The `README.md` paragraph that explains which skills `agents join` and `agents launch` auto-install by default into managed homes SHALL match the current set declared in `src/houmao/srv_ctrl/commands/system_skills.py` (and any companion `agents/system_skills.py` source) as of this change. The paragraph SHALL be reverified during implementation rather than reused verbatim from the prior pass.

When the auto-install set or the CLI-default external-install set changes during implementation discovery, the README SHALL be updated to match, and any divergence between the README paragraph and the current source SHALL be treated as a doc bug.

#### Scenario: README auto-install set agrees with current source

- **WHEN** a reader compares the README "auto-install" paragraph with the current `system_skills.py` defaults
- **THEN** the listed auto-install set matches the live source
- **AND THEN** any skill that was added to or removed from the auto-install set after the prior doc pass is reflected in the README

#### Scenario: README CLI-default install set agrees with current source

- **WHEN** a reader compares the README explanation of `system-skills install` defaults with the current `system_skills.py` defaults
- **THEN** the listed CLI-default set matches the live source

### Requirement: README links the system-skills overview narrative guide

The `README.md` system-skills subsection SHALL link to the new narrative guide at `docs/getting-started/system-skills-overview.md` so that readers who want more than a catalog row can reach the walkthrough in one click.

The link SHALL be presented alongside the existing link to `docs/reference/cli/system-skills.md` rather than replacing it. Catalog → narrative → reference SHALL be the documented progression.

#### Scenario: Reader can navigate from the README catalog to the narrative overview

- **WHEN** a reader scans the README system-skills subsection
- **THEN** they find a link to `docs/getting-started/system-skills-overview.md`
- **AND THEN** they also find the existing link to `docs/reference/cli/system-skills.md`
- **AND THEN** the README presents catalog, narrative, and reference as the three layers of system-skills coverage
