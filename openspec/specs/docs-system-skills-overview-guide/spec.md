# docs-system-skills-overview-guide Specification

## Purpose

Define the getting-started narrative-guide requirements for the packaged Houmao-owned system skills: a single page that bridges the README catalog row view and the CLI reference page by walking readers through each shipped skill, the CLI families it routes to, and the managed-home auto-install versus external-home CLI-default install distinction.
## Requirements
### Requirement: Getting-started guide narrates the packaged system skills

The docs site SHALL include a getting-started guide at `docs/getting-started/system-skills-overview.md` that walks through the packaged Houmao-owned system skills. The guide SHALL bridge the README skill catalog table and the CLI reference page `docs/reference/cli/system-skills.md` by explaining when each skill fires and how the operator and the agent see them.

That guide SHALL list every system skill currently shipped under `src/houmao/agents/assets/system_skills/`. At minimum, that list SHALL include:

- `houmao-project-mgr` — project overlay lifecycle, project layout explanation, project-aware command effects, explicit launch-profile management, and project-scoped easy-instance inspection or stop routing,
- `houmao-specialist-mgr` — specialist authoring (create and set/edit), inspection, removal, and specialist-scoped launch/stop entry,
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
`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table or an equivalently titled catalog table. Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing or utility workflow the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-llm-wiki`
- `houmao-utils-workspace-mgr`
- `houmao-touring`
- `houmao-mailbox-mgr`
- `houmao-memory-mgr`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-generic`
- `houmao-agent-instance`
- `houmao-agent-inspect`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

The guide MAY group these skills into concern-oriented subsections such as automation, control, and utils, provided every catalog entry appears in exactly one subsection.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Workspace manager appears in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains a row for `houmao-utils-workspace-mgr`
- **AND THEN** the row describes workspace planning and execution before managed agents are launched

### Requirement: Overview guide narrative count matches the catalog
The overview guide narrative SHALL NOT state a frozen skill count that does not match the current `catalog.toml` entry count and the resolved `[auto_install]` set contents.

Where the guide references how many skills exist, how many are auto-installed by `agents launch` or `agents join`, or how many are installed by `system-skills install` when no `--skill-set` or `--skill` is supplied, those numbers SHALL be computed from the current catalog rather than copied as literal text.

The guide SHALL describe managed launch and join as resolving `core`, and omitted-selection CLI installs as resolving `all`.

#### Scenario: Overview narrative stays consistent with the catalog
- **WHEN** a reader reads the overview guide paragraphs that introduce the packaged system skills
- **THEN** those paragraphs do not assert a total skill count that contradicts `catalog.toml`
- **AND THEN** they do not assert an auto-install skill count that contradicts the resolved `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets` expansions

#### Scenario: Overview auto-install wording tracks core and all
- **WHEN** a reader inspects the auto-install guidance in the overview guide
- **THEN** the guide states that managed launch and join use `core`
- **AND THEN** it states that omitted-selection `houmao-mgr system-skills install` uses `all`
- **AND THEN** it does not describe removed granular set names as current installable sets

### Requirement: Overview guide routes credential management through the dedicated CLI

The overview guide's `houmao-credential-mgr` row SHALL reference `houmao-mgr credentials <tool> ...` and the project-scoped `houmao-mgr project credentials <tool> ...` wrappers as the canonical credential-management surfaces, and SHALL NOT direct readers to manage credentials through the retired `project agents tools <tool> auth ...` subtree.

#### Scenario: Reader is routed at the supported credential CLI
- **WHEN** a reader opens the overview guide row for `houmao-credential-mgr`
- **THEN** the canonical CLI column names `credentials ...` and `project credentials ...` as the supported credential-management surfaces
- **AND THEN** it does not present `project agents tools <tool> auth ...` as a maintained credential CRUD path

### Requirement: System-skills overview guide includes the packaged memory-management skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-memory-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-memory-mgr` as the managed-memory skill for reading, editing, appending, pruning, and organizing the fixed `houmao-memo.md` file and contained `pages/` files through supported Houmao memory surfaces.

When the guide explains named sets and default installation, it SHALL mention the dedicated managed-memory set and SHALL state that managed launch, managed join, and CLI-default installation include `houmao-memory-mgr` through that set.

#### Scenario: Reader sees the packaged memory-management skill in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-memory-mgr` among the shipped packaged system skills
- **AND THEN** it describes that skill as the managed memo and pages editing entrypoint

#### Scenario: Reader sees memory-management auto-install behavior
- **WHEN** a reader checks the named-set or auto-install explanation in the system-skills overview guide
- **THEN** the guide explains that the managed-memory set includes `houmao-memory-mgr`
- **AND THEN** it explains that managed launch, managed join, and CLI-default installation include that set

### Requirement: System-skills overview mentions Copilot installation
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL mention Copilot as a supported explicit external-home installation target for Houmao-owned system skills.

The guide SHALL explain that omitted-home Copilot installs land under `.github/skills/` in the current repository, while explicit personal installs can target `~/.copilot` with `--home ~/.copilot`.

The guide SHALL distinguish Copilot skill discovery from local Houmao runtime availability: Copilot surfaces may discover repository skills, but operational use of Houmao management skills requires an environment where `houmao-mgr` and the relevant local project, tmux, gateway, mailbox, or runtime resources are available.

#### Scenario: Reader sees Copilot in explicit install guidance
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide includes Copilot in the explicit external install guidance
- **AND THEN** it explains the `.github/skills/` default projection path for repository-local Copilot skills

#### Scenario: Reader understands Copilot runtime caveat
- **WHEN** a reader reviews Copilot system-skill guidance
- **THEN** the guide states that discoverability does not guarantee local Houmao runtime resources are available
- **AND THEN** it points readers to local or appropriately provisioned environments for operational Houmao skill use

### Requirement: System-skills overview guide explains uninstall behavior
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL mention `houmao-mgr system-skills uninstall` as the supported way to remove the current Houmao-owned system-skill surface from resolved external or project-scoped tool homes.

The guide SHALL state that uninstall removes all current catalog-known Houmao system skills for the resolved tool home and does not mirror install's `--skill` or `--skill-set` selection behavior.

The guide SHALL include at least one uninstall example for a single tool and MAY point readers to `docs/reference/cli/system-skills.md` for the full flag and output surface.

The guide SHALL explain the removal boundary at a narrative level: uninstall removes current Houmao-owned skill projection paths and preserves unrelated user skills, parent roots, legacy paths, and obsolete install-state files.

#### Scenario: Reader sees how to remove installed system skills
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide mentions `houmao-mgr system-skills uninstall`
- **AND THEN** it explains that uninstall removes all current known Houmao system skills for the resolved tool home

#### Scenario: Reader understands uninstall differs from selective install
- **WHEN** a reader compares install and uninstall guidance in the overview guide
- **THEN** the guide explains that install can select sets or explicit skills
- **AND THEN** it explains that uninstall is intentionally all-current-known-Houmao-skills for the target home

#### Scenario: Reader sees uninstall's deletion boundary
- **WHEN** a reader checks the overview guide's uninstall guidance
- **THEN** the guide states that unrelated user skills, parent roots, legacy paths, and obsolete install-state files are outside the uninstall deletion boundary

### Requirement: System-skills overview guide includes the LLM Wiki utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-utils-llm-wiki` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe the skill as a general utility for building and maintaining persistent Markdown LLM Wiki knowledge bases with scaffold, ingest, compile, query, lint, audit, and local viewer workflows.

The guide SHALL place `houmao-utils-llm-wiki` in a utility group or equivalent section distinct from managed-agent lifecycle, messaging, gateway, mailbox, memory, project authoring, and loop-control skills.

The guide SHALL explain that the `utils` set is explicit-only and not included in managed launch, managed join, or CLI-default install selections.

#### Scenario: Reader finds the utility skill in the overview
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** they find `houmao-utils-llm-wiki` in the packaged skill overview
- **AND THEN** the description frames it as a knowledge-base utility rather than a managed-agent control skill

#### Scenario: Reader sees explicit-only utility default behavior
- **WHEN** a reader checks the overview guide's named-set or default-selection explanation
- **THEN** it lists `utils` as a named set containing `houmao-utils-llm-wiki`
- **AND THEN** it explains that default selections do not include `utils`

### Requirement: System-skills overview guide explains organization groups and installable sets
The system-skills overview guide SHALL explain that automation, control, and utils are organization groups used for documentation readability.

The guide SHALL explain that the current installable named sets are only `core` and `all`.

The guide SHALL state that `core` is the managed launch/join default and `all` is the omitted-selection CLI install default.

#### Scenario: Reader understands groups versus sets
- **WHEN** a reader opens the system-skills overview guide
- **THEN** they can distinguish automation/control/utils organization groups from the installable `core` and `all` set names
- **AND THEN** install examples use `core`, `all`, or explicit skill names

### Requirement: System-skills overview guide includes the workspace manager utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-utils-workspace-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-utils-workspace-mgr` as the utility skill for planning or executing multi-agent workspace layouts before agent launch, including in-repo and out-of-repo workspace flavors, worktrees, local-only shared repos, safe local-state symlink decisions, tracked-submodule materialization, launch-profile cwd updates, and optional memo seed augmentation.

The guide SHALL state that the workspace manager is part of the utility group, is included by `all`, and is not included by managed launch or managed join defaults unless explicitly selected.

#### Scenario: Reader sees workspace manager utility behavior
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-utils-workspace-mgr`
- **AND THEN** it describes the skill as workspace preparation guidance rather than an agent launch skill
