## ADDED Requirements

### Requirement: Getting-started guide narrates the packaged system skills

The docs site SHALL include a getting-started guide at `docs/getting-started/system-skills-overview.md` that walks through the packaged Houmao-owned system skills. The guide SHALL bridge the README skill catalog table and the CLI reference page `docs/reference/cli/system-skills.md` by explaining when each skill fires and how the operator and the agent see them.

That guide SHALL list every system skill currently shipped under `src/houmao/agents/assets/system_skills/`. At minimum, that list SHALL include:

- `houmao-manage-specialist` — specialist authoring and specialist-scoped launch/stop entry,
- `houmao-manage-credentials` — project-local tool auth bundle administration,
- `houmao-manage-agent-definition` — low-level role and recipe administration,
- `houmao-manage-agent-instance` — managed-agent instance lifecycle (`launch`, `join`, `list`, `stop`, `cleanup`),
- `houmao-agent-messaging` — prompt, interrupt, queue, raw input, mailbox routing, and reset-context guidance for already-running managed agents,
- `houmao-agent-gateway` — gateway lifecycle, gateway discovery, wakeups, notifier guidance for attached managed agents,
- `houmao-agent-email-comms` — ordinary shared-mailbox operations and no-gateway fallback guidance,
- `houmao-process-emails-via-gateway` — notifier-driven unread-mail rounds.

For each skill the guide SHALL state:

- a one-sentence description of what the skill enables,
- the canonical CLI families it routes to,
- whether the skill is auto-installed into managed homes by `agents join` and `agents launch`, or only available through `houmao-mgr system-skills install` against an external tool home,
- a link to the corresponding reference coverage in `docs/reference/cli/system-skills.md`.

The guide SHALL distinguish managed-home auto-install behavior from external-home CLI-default install behavior in one short subsection. That subsection SHALL describe the auto-install set used by `agents join` / `agents launch` and the CLI-default set used by `system-skills install` when both `--set` and `--skill` are omitted, deriving both lists from the current `srv_ctrl/commands/system_skills.py` defaults rather than from prior README text.

The guide SHALL explain that the system-skills surface is how an agent itself drives Houmao management without requiring the operator to invoke `houmao-mgr` manually, and SHALL link to:

- `docs/reference/cli/system-skills.md` for the full reference,
- `docs/getting-started/easy-specialists.md` for the user-facing flow that exercises `houmao-manage-specialist`,
- `docs/getting-started/launch-profiles.md` for the launch-side concepts the agent skills observe,
- the README "System Skills" subsection for the catalog-table view.

The guide SHALL NOT restate the full CLI reference content; it SHALL keep the reference page authoritative for flag tables and effective-home resolution rules.

#### Scenario: Reader can find a narrative tour of the system skills

- **WHEN** a new operator wants to understand what system skills Houmao installs into agent tool homes
- **THEN** they find a getting-started guide at `docs/getting-started/system-skills-overview.md`
- **AND THEN** the guide describes each shipped system skill with one-sentence purpose and canonical CLI routing

#### Scenario: Guide distinguishes auto-install from CLI-default install behavior

- **WHEN** a reader needs to know which skills appear inside a managed home versus an explicit external tool home
- **THEN** the guide explains which skills `agents join` and `agents launch` auto-install
- **AND THEN** the guide explains which skills `system-skills install` adds when both `--set` and `--skill` are omitted
- **AND THEN** the two lists are derived from the current `system_skills.py` defaults rather than reused stale README copy

#### Scenario: Guide bridges README catalog and CLI reference

- **WHEN** a reader follows links from the system-skills overview guide
- **THEN** they reach the README catalog table for the 60-second view
- **AND THEN** they reach `docs/reference/cli/system-skills.md` for the full flag-level reference
- **AND THEN** they reach the easy-specialists and launch-profiles guides for the user-facing flows the skills observe

#### Scenario: Guide lists the unified email-comms skill

- **WHEN** a reader checks the system-skills overview for mailbox-related skills
- **THEN** the guide lists `houmao-agent-email-comms` as the ordinary mailbox operations skill
- **AND THEN** the guide lists `houmao-process-emails-via-gateway` as the notifier-driven unread-mail rounds skill
- **AND THEN** the guide does not list the pre-unification split mailbox skill names as current
