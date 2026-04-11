# docs-system-skills-overview-guide Specification

## Purpose

Define the getting-started narrative-guide requirements for the packaged Houmao-owned system skills: a single page that bridges the README catalog row view and the CLI reference page by walking readers through each shipped skill, the CLI families it routes to, and the managed-home auto-install versus external-home CLI-default install distinction.
## Requirements
### Requirement: Getting-started guide narrates the packaged system skills

The docs site SHALL include a getting-started guide at `docs/getting-started/system-skills-overview.md` that walks through the packaged Houmao-owned system skills. The guide SHALL bridge the README skill catalog table and the CLI reference page `docs/reference/cli/system-skills.md` by explaining when each skill fires and how the operator and the agent see them.

That guide SHALL list every system skill currently shipped under `src/houmao/agents/assets/system_skills/`. At minimum, that list SHALL include:

- `houmao-project-mgr` — project overlay lifecycle, project layout explanation, project-aware command effects, explicit launch-profile management, and project-scoped easy-instance inspection or stop routing,
- `houmao-specialist-mgr` — specialist authoring and specialist-scoped launch/stop entry,
- `houmao-credential-mgr` — dedicated credential management for project overlays and plain agent-definition directories,
- `houmao-agent-definition` — low-level role and recipe administration,
- `houmao-agent-instance` — managed-agent instance lifecycle (`launch`, `join`, `list`, `stop`, `cleanup`),
- `houmao-agent-messaging` — prompt, interrupt, queue, raw input, mailbox routing, and reset-context guidance for already-running managed agents,
- `houmao-agent-gateway` — gateway lifecycle, gateway discovery, wakeups, notifier guidance for attached managed agents,
- `houmao-agent-email-comms` — ordinary shared-mailbox operations and no-gateway fallback guidance,
- `houmao-process-emails-via-gateway` — notifier-driven unread-mail rounds,
- `houmao-adv-usage-pattern` — advanced supported workflow compositions layered on top of the direct-operation skills, including self-wakeup through self-mail plus notifier-driven rounds.

For each skill the guide SHALL state:

- a one-sentence description of what the skill enables,
- the canonical CLI families it routes to,
- whether the skill is auto-installed into managed homes by `agents join` and `agents launch`, or only available through `houmao-mgr system-skills install` against an external tool home,
- a link to the corresponding reference coverage in `docs/reference/cli/system-skills.md`.

The guide SHALL distinguish managed-home auto-install behavior from external-home CLI-default install behavior in one short subsection. That subsection SHALL describe the auto-install set used by `agents join` / `agents launch` and the CLI-default set used by `system-skills install` when both `--set` and `--skill` are omitted, deriving both lists from the current `srv_ctrl/commands/system_skills.py` defaults rather than from prior README text.

The guide SHALL explain that the system-skills surface is how an agent itself drives Houmao management without requiring the operator to invoke `houmao-mgr` manually, and SHALL link to:

- `docs/reference/cli/system-skills.md` for the full reference,
- `docs/getting-started/easy-specialists.md` for the user-facing flow that exercises `houmao-specialist-mgr`,
- `docs/getting-started/launch-profiles.md` for the launch-side concepts the agent skills observe,
- `docs/getting-started/agent-definitions.md` and `docs/reference/agents/operations/project-aware-operations.md` for project layout and project-aware overlay follow-up,
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

#### Scenario: Guide lists the packaged project-management skill

- **WHEN** a reader checks the system-skills overview for project-oriented skills
- **THEN** the guide lists `houmao-project-mgr` as the packaged project-management skill
- **AND THEN** it describes overlay lifecycle, project layout, project-aware command effects, and project-scoped launch-profile or easy-instance inspection routing

#### Scenario: Guide lists the unified email-comms skill

- **WHEN** a reader checks the system-skills overview for mailbox-related skills
- **THEN** the guide lists `houmao-agent-email-comms` as the ordinary mailbox operations skill
- **AND THEN** the guide lists `houmao-process-emails-via-gateway` as the notifier-driven unread-mail rounds skill
- **AND THEN** the guide does not list the pre-unification split mailbox skill names as current

#### Scenario: Guide lists the advanced-usage skill

- **WHEN** a reader checks the system-skills overview for higher-level workflow guidance
- **THEN** the guide lists `houmao-adv-usage-pattern` as the packaged advanced-usage skill
- **AND THEN** it describes that skill as the entrypoint for supported multi-skill usage patterns rather than as a replacement for the direct-operation skills

### Requirement: System-skills overview guide includes the packaged mailbox-admin skill and mailbox set distinction
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-mailbox-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-mailbox-mgr` as the mailbox-administration skill for mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late managed-agent filesystem mailbox binding.

When the guide explains the named sets, it SHALL distinguish `mailbox-core` from `mailbox-full` by describing `mailbox-core` as the narrow mailbox worker pair and `mailbox-full` as the broader mailbox set that also includes `houmao-mailbox-mgr`.

#### Scenario: Reader sees the packaged mailbox-admin skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-mailbox-mgr` among the shipped packaged system skills
- **AND THEN** it describes that skill as the mailbox-administration entrypoint rather than as the ordinary mailbox-operations skill

#### Scenario: Reader sees that `mailbox-full` is broader than `mailbox-core`
- **WHEN** a reader checks the named-set explanation in the system-skills overview guide
- **THEN** the guide explains that `mailbox-core` is the narrow mailbox worker pair
- **AND THEN** it explains that `mailbox-full` also includes `houmao-mailbox-mgr`

### Requirement: System-skills overview guide lists the manual guided touring skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-touring` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-touring` as the manual guided-tour skill for first-time or re-orienting users. That description SHALL explain that the skill orients on current state and helps the user branch across project setup, mailbox setup, specialist/profile authoring, agent launch, post-launch operations, and lifecycle follow-up.

The guide SHALL state that `houmao-touring` is manual-invocation-only and SHALL NOT present it as the default routing choice for ordinary direct-operation requests.

When the guide explains the packaged named sets or default install selections, it SHALL mention the dedicated `touring` named set.

#### Scenario: Reader sees the touring skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-touring` among the packaged Houmao-owned system skills
- **AND THEN** it describes the skill as a guided first-user tour rather than as a direct-operation skill

#### Scenario: Reader sees that touring is manual-only and branching
- **WHEN** a reader checks the `houmao-touring` entry in the narrative guide
- **THEN** the guide explains that the skill is manual-invocation-only
- **AND THEN** it explains that the tour can revisit branches such as creating more specialists, launching more agents, or following up with stop, relaunch, or cleanup

### Requirement: System-skills overview guide uses the dedicated credential-management routing
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL describe `houmao-credential-mgr` as routing through the dedicated credential-management families rather than through `project agents tools <tool> auth ...`.

At minimum, the guide SHALL state that `houmao-credential-mgr` routes credential work through:

- `houmao-mgr project credentials <tool> ...` for active project overlays,
- `houmao-mgr credentials <tool> ... --agent-def-dir <path>` for explicit plain agent-definition directories.

The guide SHALL continue to describe `houmao-credential-mgr` as the credential-management skill distinct from specialist authoring, role/recipe authoring, instance lifecycle, and mailbox administration.

#### Scenario: Reader sees the new credential routing in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the `houmao-credential-mgr` entry points to `project credentials ...` and `credentials ... --agent-def-dir <path>` as the supported command families
- **AND THEN** the guide does not present `project agents tools <tool> auth ...` as the canonical credential-management route

### Requirement: Overview guide table enumerates every catalog entry
`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table (or an equivalently titled catalog table). Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

- `houmao-touring`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`
- `houmao-mailbox-mgr`
- `houmao-agent-email-comms`
- `houmao-process-emails-via-gateway`
- `houmao-adv-usage-pattern`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-generic`

The guide MAY group these skills into concern-oriented subsections (for example "guided touring", "project, specialist, and credential authoring", "agent definition and instance management", "communication, gateway, and mailbox", "loop authoring and master-run control"), provided every catalog entry appears in exactly one subsection.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Stable and v2 pairwise skills appear in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains distinct rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** the stable row describes the simpler restored pairwise run-control surface
- **AND THEN** the v2 row describes the enriched versioned pairwise workflow and distinguishes it from the stable pairwise skill

#### Scenario: Loop skills appear in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains rows for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic`
- **AND THEN** the "canonical CLI routing" column for each loop skill points the reader at the supported operating and authoring command paths actually shipped by the packaged skill assets

#### Scenario: Generic loop planner replaces relay-only row
- **WHEN** a reader opens the overview guide after the generic replacement
- **THEN** the catalog table contains `houmao-agent-loop-generic`
- **AND THEN** it does not contain `houmao-agent-loop-relay` as a current shipped skill

### Requirement: Overview guide auto-install description includes both pairwise variants when `user-control` includes both
The "Auto-Install vs Explicit Install" section of `docs/getting-started/system-skills-overview.md` SHALL explain that managed launch, managed join, and CLI-default installation all include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` whenever the current `user-control` set resolves both skills.

#### Scenario: Overview auto-install wording reflects both pairwise variants
- **WHEN** a reader inspects the overview guide's auto-install narrative or diagram
- **THEN** the guide includes both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` wherever it expands the current `user-control` set
- **AND THEN** it does not imply that only one pairwise variant is auto-installed when the catalog includes both

### Requirement: Overview guide narrative count matches the catalog
The overview guide narrative SHALL NOT state a frozen skill count (for example "twelve system skills" or "eleven auto-installed skills") that does not match the current `catalog.toml` entry count and the resolved `[auto_install]` set contents.

Where the guide references how many skills exist, how many are auto-installed by `agents launch` or `agents join`, or how many are installed by `system-skills install` when no `--set` or `--skill` is supplied, those numbers SHALL be computed from the current catalog rather than copied as literal text.

#### Scenario: Overview narrative stays consistent with the catalog
- **WHEN** a reader reads the overview guide paragraphs that introduce the packaged system skills
- **THEN** those paragraphs do not assert a total skill count that contradicts `catalog.toml`
- **AND THEN** they do not assert an auto-install skill count that contradicts the resolved `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets` expansions

#### Scenario: Overview auto-install diagram tracks the catalog
- **WHEN** a reader inspects the "Auto-Install vs Explicit Install" section of the overview guide
- **THEN** the ASCII diagram, prose, and per-set expansion table reflect the current resolved contents of `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` in `catalog.toml`
- **AND THEN** the diagram includes `houmao-agent-loop-generic` through `user-control` when the catalog includes it
- **AND THEN** the diagram does not leave `houmao-agent-loop-pairwise` or `houmao-agent-loop-generic` out of the managed-launch auto-install column unless the catalog removes them from the `user-control` set

### Requirement: Overview guide routes credential management through the dedicated CLI

The overview guide's `houmao-credential-mgr` row SHALL reference `houmao-mgr credentials <tool> ...` and the project-scoped `houmao-mgr project credentials <tool> ...` wrappers as the canonical credential-management surfaces, and SHALL NOT direct readers to manage credentials through the retired `project agents tools <tool> auth ...` subtree.

#### Scenario: Reader is routed at the supported credential CLI
- **WHEN** a reader opens the overview guide row for `houmao-credential-mgr`
- **THEN** the canonical CLI column names `credentials ...` and `project credentials ...` as the supported credential-management surfaces
- **AND THEN** it does not present `project agents tools <tool> auth ...` as a maintained credential CRUD path

