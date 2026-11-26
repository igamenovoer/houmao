## Purpose
Define the packaged Houmao-owned `houmao-agent-definition` system skill for low-level project-local role and preset management.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-definition` system skill

The system SHALL replace the old agent-definition skill guidance with packaged Houmao-owned guidance that separates project agent management from native-agent internals.

The canonical ordinary project guidance SHALL instruct agents to manage project-layer resources through:

- `houmao-mgr project specialist ...`
- `houmao-mgr project profile ...`
- project-scoped managed-agent lifecycle commands
- `houmao-mgr project credentials ...`
- `houmao-mgr project skills ...`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The canonical native-provider guidance SHALL instruct agents to use internal native-agent commands only when the user explicitly asks for provider-aligned native material, launch dossiers, recipes, roles, or direct native-agent root work:

- `houmao-mgr internals native-agent roles list`
- `houmao-mgr internals native-agent roles get`
- `houmao-mgr internals native-agent roles init`
- `houmao-mgr internals native-agent roles set`
- `houmao-mgr internals native-agent roles remove`
- `houmao-mgr internals native-agent recipes ...`
- `houmao-mgr internals native-agent launch-dossiers ...`
- `houmao-mgr internals native-agent tools ...`

The skill SHALL avoid using `agent definition`, `raw profile`, or `launch profile` as ordinary project terms. It SHALL define `native agent` and `launch dossier` as internal compatibility-layer terms.

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `create`
- `list`
- `get`
- `set`
- `remove`

The top-level skill guidance SHALL route ordinary user requests for reusable agent configuration to project specialists and project profiles unless the user explicitly asks for native-agent internals.

The packaged skill SHALL NOT instruct agents to use retired or unsupported low-level shapes such as:

- `houmao-mgr internals native-agent roles scaffold`
- `houmao-mgr internals native-agent roles presets ...`

#### Scenario: Ordinary specialist request routes to project commands
- **WHEN** a user asks an agent to create a reusable Codex reviewer
- **THEN** the packaged guidance routes the agent to `houmao-mgr project specialist create`
- **AND THEN** it does not route the request to native-agent roles or recipes

#### Scenario: Native launch dossier request routes to internals
- **WHEN** a user explicitly asks for a native launch dossier
- **THEN** the packaged guidance routes the agent to `houmao-mgr internals native-agent launch-dossiers ...`
- **AND THEN** it treats the request as internal provider-aligned material rather than a project profile

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-definition` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `create`, `list`, `get`, `set`, and `remove`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

### Requirement: Agent-definition skill avoids top-level target-variant commands
The packaged `houmao-agent-definition` skill SHALL route ordinary project authoring through:

```text
houmao-mgr project [--project-dir <dir>] ...
```

The skill SHALL route direct provider-aligned native material through:

```text
houmao-mgr internals native-agent [--native-agent-root <dir>] ...
```

The skill SHALL NOT present top-level `credentials --project`, top-level `credentials --agent-def-dir`, or top-level `brains build` as maintained command paths.

#### Scenario: Skill uses project directory selector for project authoring
- **WHEN** a user asks the agent to create a specialist in project `/repo`
- **THEN** the skill guidance routes to `houmao-mgr project --project-dir /repo specialist create`
- **AND THEN** it does not choose a top-level command only to select that project

#### Scenario: Skill uses internals for direct native build
- **WHEN** a user explicitly asks the agent to build a brain from native-agent root `/tmp/native`
- **THEN** the skill guidance routes to `houmao-mgr internals native-agent brain build --native-agent-root /tmp/native`
- **AND THEN** it does not route to top-level `houmao-mgr brains build --agent-def-dir /tmp/native`

### Requirement: System skills use the revised project/native vocabulary consistently
Packaged system skills that mention Houmao agent authoring or launch preparation SHALL use:

- `specialist` for reusable project-level persona/tool/credential definitions,
- `profile` for reusable project launch defaults,
- `managed agent` or `agent instance` for runtime identities,
- `native agent` for internal provider-aligned launch material,
- `launch dossier` for internal recipe-backed native launch defaults.

#### Scenario: Loop skills ask for project profiles or launch dossiers explicitly
- **WHEN** a loop skill asks an agent to prepare launch facts
- **THEN** it distinguishes project profiles from native launch dossiers
- **AND THEN** it does not use raw profile or launch profile ambiguously

### Requirement: `houmao-agent-definition` resolves the `houmao-mgr` launcher in the required precedence order

The packaged `houmao-agent-definition` skill SHALL teach agents to resolve `houmao-mgr` for the current workspace. An explicit user choice SHALL take precedence over the default order of PATH lookup, the uv-managed fallback, and a development launcher.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-definition` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed definition-management action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-agent-definition` selects the correct current low-level command and asks before guessing

The packaged `houmao-agent-definition` skill SHALL tell the agent to recover omitted definition-management inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select commands by target and action:

- use `roles init` for creating one new minimal role root
- use `presets add` for creating one named preset
- use `roles list` for listing roles
- use `presets list` for listing named presets
- use `roles get` for inspecting one role, adding `--include-prompt` when the user explicitly asks to inspect prompt text or the full low-level definition
- use `presets get` for inspecting one named preset
- use `roles set` for changing the canonical role prompt
- use `presets set` for changing one named preset's role, tool, setup, auth reference, skill membership, or prompt mode
- use `roles remove` for removing one role
- use `presets remove` for removing one named preset

At minimum, the skill SHALL require the agent to obtain:

- for `roles list`: no role name
- for `presets list`: no preset name, plus any optional filters only when the user explicitly asked for them
- for `roles get`: the role name
- for `presets get`: the preset name
- for `roles init`: the role name, plus an optional initial prompt only when the user asked for it explicitly
- for `roles set`: the role name and at least one explicit prompt mutation
- for `presets add`: the preset name, role name, tool, and any optional preset fields the user explicitly wants to author
- for `presets set`: the preset name and at least one explicit preset mutation
- for removal: the concrete role or preset target to delete

When the user asks to change which credential bundle one preset or low-level definition uses, the skill SHALL treat that as a preset-auth-reference change on `presets set` rather than as direct auth-bundle mutation.

When the user asks to change env vars or auth files inside an auth bundle, the skill SHALL report that the request belongs to `houmao-credential-mgr` rather than inventing direct file edits or routing that request through definition-management commands.

#### Scenario: Full role inspection uses explicit prompt inclusion
- **WHEN** the user asks the agent to inspect one role's full low-level definition including its prompt text
- **THEN** the skill directs the agent to use `houmao-mgr internals native-agent roles get --include-prompt`
- **AND THEN** it does not require direct reads from `.houmao/agents/roles/<role>/system-prompt.md`

#### Scenario: Preset credential change stays within definition structure
- **WHEN** the user asks the agent to change which credential bundle one preset references
- **THEN** the skill directs the agent to use `houmao-mgr project agents presets set --auth ...` or `--clear-auth`
- **AND THEN** it treats that change as part of preset structure rather than as direct auth-bundle mutation

#### Scenario: Auth-bundle content mutation stays on the credential skill
- **WHEN** the user asks the agent to add, remove, or change env vars or auth files inside an auth bundle
- **THEN** the skill reports that the request belongs to the credential-management workflow
- **AND THEN** it does not claim that `houmao-agent-definition` covers that lower-level auth-bundle content mutation

#### Scenario: Missing target or mutation requires a user question
- **WHEN** the selected definition-management action still lacks a required target or explicit mutation after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing input before proceeding
- **AND THEN** it does not guess a role, preset name, tool, or field change

### Requirement: `houmao-agent-definition` is the canonical pre-launch agent-definition skill
The packaged `houmao-agent-definition` skill SHALL be the canonical Houmao-owned skill for persisted pre-launch agent definition workflows.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That unified skill SHALL expose these skill-level subcommands:

- `roles` for low-level prompt-only roles;
- `recipes` for low-level recipes, with `presets` as a compatibility alias;
- `launch-dossiers` for low-level native launch dossiers using the underlying `houmao-mgr internals native-agent launch-dossiers ...` CLI;
- `specialists` for project-specialist templates;
- `profiles` for specialist-backed project profiles;
- `create-agent-fast-forward` for creating or selecting a specialist, creating or updating an project profile, printing the launch command, and not launching a live agent;
- `launch-agent` for the limited easy launch entry point that hands off broader live lifecycle work to `houmao-agent-instance`;
- `stop-agent` for the limited easy stop entry point that hands off broader live lifecycle work to `houmao-agent-instance`.

The skill SHALL treat loosely stated `profile`, `agent profile`, `launch profile`, and `ready profile` wording as the `profiles` subcommand by default unless the user explicitly asks for `launch-dossiers`, launch dossier behavior, recipe-backed profile behavior, or the exact `internals native-agent launch-dossiers` CLI surface.

#### Scenario: Unified skill routes named subcommands
- **WHEN** an agent reads the packaged `houmao-agent-definition` skill
- **THEN** the top-level page lists the supported skill subcommands and their local subskill routes
- **AND THEN** the agent can route a user request that explicitly names `profiles`, `launch-dossiers`, or `create-agent-fast-forward` without asking which branch was intended

#### Scenario: Ambiguous launch profile means project profile
- **WHEN** a user asks to create or update an agent launch profile without saying raw, recipe-backed, or `internals native-agent launch-dossiers`
- **THEN** the skill routes the request to the `profiles` subcommand
- **AND THEN** it does not route the request to low-level native launch dossiers by default

### Requirement: `houmao-agent-definition` uses lane-specific subskills
The unified `houmao-agent-definition` skill SHALL keep its entry page concise and SHALL route detailed behavior into lane-specific local subskills or references.

At minimum, the skill SHALL distinguish `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`.

The skill SHALL include shared guidance for launcher resolution, missing-input handling, profile-lane terminology, and credential-routing boundaries.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The entry page SHALL either route existing generic `actions/*` pages through the new subcommand vocabulary or mark those pages as legacy low-level-only references so they do not conflict with the subcommand table.

#### Scenario: Entry page loads only the relevant lane
- **WHEN** the user asks to update one project profile
- **THEN** `houmao-agent-definition` routes to the `profiles` subcommand and project-profile subskill
- **AND THEN** it does not load or flatten unrelated low-level recipe, launch-dossier, or easy-instance launch instructions into the entry page

#### Scenario: Launch dossier route is explicit
- **WHEN** the user asks for `launch-dossiers` or for the exact `internals native-agent launch-dossiers` surface
- **THEN** `houmao-agent-definition` routes to the low-level recipe-backed profile subskill
- **AND THEN** the subskill names the underlying `houmao-mgr internals native-agent launch-dossiers ...` commands

### Requirement: Unified skill keeps neighboring platform concerns out of scope
The unified `houmao-agent-definition` skill SHALL NOT become the owner for credential bundle CRUD, mailbox root/account administration, workspace creation, broad live managed-agent lifecycle, or direct filesystem edits under `.houmao/`.

It SHALL route those concerns to `houmao-credential-mgr`, `houmao-mailbox-mgr`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, or other maintained Houmao skills as appropriate.

#### Scenario: Credential content mutation is routed away
- **WHEN** a user asks to mutate auth files or environment variables inside a credential bundle while using `houmao-agent-definition`
- **THEN** the skill routes the request to `houmao-credential-mgr`
- **AND THEN** it does not treat credential-bundle content mutation as specialist, recipe, or profile authoring

### Requirement: `houmao-agent-definition` uses config drafts for supported config authoring flows
The packaged `houmao-agent-definition` skill SHALL instruct agents to use `houmao-mgr internals config-drafts generate` before authoring supported project configuration documents for these skill subcommands:

- `specialists`
- `profiles`
- `launch-dossiers`
- profile preparation inside `create-agent-fast-forward`

For those supported config-authoring flows, the skill SHALL tell agents to generate drafts from explicit user inputs and recovered explicit context only.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL NOT own full default-bearing YAML examples or command skeletons in Markdown for config shapes covered by `internals config-drafts`.

The skill SHALL describe config drafts as minimal opinionated drafts and SHALL direct full customization beyond the draft's required holes back to maintained project subcommands.

The skill SHALL direct agents to the CLI-owned config draft as the authoritative source for the config kind, fixed lane/source values, required credential/auth reference, and draft YAML shape.

For executable command-oriented workflows that are not config documents, the skill SHALL document direct `houmao-mgr` command snippets in fenced `bash` blocks and SHALL NOT call `houmao-mgr internals command-templates`.

#### Scenario: Profile authoring generates a config draft
- **WHEN** a user asks `houmao-agent-definition profiles` to create project profile `reviewer-fast` for specialist `reviewer` and credential `reviewer-creds`
- **AND WHEN** the user does not request prompt-mode or headless posture persistence
- **THEN** the skill guidance directs the agent to generate `project.profile` with only `name`, `specialist`, and `credential`
- **AND THEN** the generated draft records project-profile lane and specialist source without adding prompt-mode or headless defaults

#### Scenario: Launch dossier authoring generates a raw launch-profile draft
- **WHEN** a user asks `houmao-agent-definition launch-dossiers` to prepare raw launch profile `alice` with recipe `reviewer-codex` and credential `reviewer-creds`
- **THEN** the skill guidance directs the agent to generate `internals.native-agent.launch-dossier`
- **AND THEN** the generated draft records only the fixed recipe-backed profile values and required credential/auth reference

#### Scenario: Specialist authoring generates a specialist draft
- **WHEN** a user asks `houmao-agent-definition specialists` to prepare a Codex specialist named `reviewer` with credential `reviewer-creds`
- **THEN** the skill guidance directs the agent to generate `project.specialist`
- **AND THEN** the guidance does not require loading a separate executable-command schema to see every possible credential, skill, mailbox, and launch option

#### Scenario: Recipe authoring uses direct commands
- **WHEN** a user asks `houmao-agent-definition recipes` to create recipe `reviewer-codex` from role `reviewer` and tool `codex`
- **AND WHEN** no recipe config-draft contract exists
- **THEN** the skill guidance shows the maintained direct `houmao-mgr internals native-agent recipes ...` command in a fenced `bash` block
- **AND THEN** the guidance does not invent a recipe YAML draft that Houmao does not provide

#### Scenario: Fast-forward uses drafts and direct launch command printing
- **WHEN** `create-agent-fast-forward` prepares a launchable project profile and prints the launch command
- **THEN** the skill guidance uses config drafts for specialist/profile preparation
- **AND THEN** it prints the maintained `houmao-mgr project agents launch ...` command directly

### Requirement: `houmao-agent-definition` uses direct command snippets for executable workflows
The packaged `houmao-agent-definition` skill SHALL document executable commands as fenced `bash` snippets.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or command-template blocker recovery.

The skill SHALL preserve required-input and conflict guardrails in prose before each direct command workflow.

#### Scenario: Low-level role command is shown directly
- **WHEN** a user asks the skill to initialize or edit a low-level role
- **THEN** the skill guidance shows a direct `houmao-mgr internals native-agent roles ...` command in a fenced `bash` block
- **AND THEN** it does not render a command-template id first

#### Scenario: Launch command is shown directly
- **WHEN** a user asks the skill to print or run a managed launch command
- **THEN** the skill guidance shows a direct `houmao-mgr project agents launch ...` command in a fenced `bash` block
- **AND THEN** omitted optional flags remain absent unless explicitly requested

### Requirement: Agent-definition skill excludes Gemini
The unified agent-definition skill SHALL contain no Gemini credential routing, specialist flags, profiles, recipes, or launch examples.

#### Scenario: Agent-definition provider routing excludes Gemini
- **WHEN** an agent uses the packaged definition skill to choose a provider lane
- **THEN** the guidance routes only to maintained Claude, Codex, or Kimi instructions

### Requirement: The existing Agent Definition routine owns authoring and deployment
`houmao-shared-routines->houmao-agent-definition` SHALL provide one command family for initialization, derivation, clarification, approval, materialization, validation, planning, apply, inspection, doctor, update, and removal.

#### Scenario: Human starts from requirements
- **WHEN** an admin invokes the routine with prose for a new reusable agent
- **THEN** it SHALL initialize or update `agent-def-overview.md` and SHALL stop at each requested review boundary

#### Scenario: Human starts from a materialized revision
- **WHEN** an admin asks to deploy an existing revision
- **THEN** the routine SHALL skip authoring and SHALL collect only the revision's declared deployment inputs

### Requirement: The routine delegates durable work to maintained commands
The routine SHALL use maintained `houmao-mgr` commands for validation, materialization, planning, apply, doctor, update, and removal.

#### Scenario: Deployment is confirmed
- **WHEN** the human approves a Deployment Plan
- **THEN** the routine SHALL invoke maintained apply and SHALL not reproduce filesystem or catalog mutation in skill instructions

### Requirement: The routine does not invent semantic edit authority
The routine SHALL bind only declared deployment inputs. It SHALL route undeclared content changes back to authoring and rematerialization.

#### Scenario: Task requires changing core behavior
- **WHEN** a request cannot fit declared bindings
- **THEN** the routine SHALL explain the conflict and SHALL not patch the revision during deployment

### Requirement: Definition administration remains admin-only and pre-launch
The routine SHALL reject managed-agent posture for authoring and deployment. Successful deployment SHALL report but SHALL not execute the launch command.

#### Scenario: Managed agent invokes definition deployment
- **WHEN** verified actor posture is managed agent
- **THEN** the routine SHALL reject the operation

### Requirement: Agent Definition routine supports bounded plural deployment
The existing Agent Definition routine SHALL collect count, shared inputs, member overrides, and explicit delegation before creating a Batch Request.

#### Scenario: Human delegates three selection categories
- **WHEN** the human asks for `N` deployments and explicitly delegates names, tools, and credential references
- **THEN** the routine SHALL propose bounded selections and SHALL preview every member before apply

### Requirement: The routine uses maintained batch commands
The routine SHALL delegate validation, planning, apply, recovery, and doctor to maintained `houmao-mgr` batch commands.

#### Scenario: Human confirms the batch plan
- **WHEN** every member is valid and the human confirms
- **THEN** the routine SHALL call one maintained batch apply command

### Requirement: The packaged authoring route maintains workspace orientation

The packaged `houmao-shared-routines->houmao-agent-definition` skill SHALL tell an admin authoring an Agent Definition to create and refresh `<authoring-dir>/README.md` according to the Agent Definition authoring README contract. The route SHALL keep README maintenance inside `definition-authoring` and SHALL preserve initialization, derivation, approval, preview, materialization, and validation as separate phases.

#### Scenario: Manual authoring stops before approval

- **WHEN** an admin explicitly asks the route to initialize and derive an authoring workspace but stop before approval
- **THEN** the route creates or refreshes the root README after derivation
- **AND THEN** it still stops before approval, preview, and immutable revision write

#### Scenario: Natural-language authoring activates the admin route

- **WHEN** a human operator naturally asks to turn an existing overview into a reusable Houmao Agent Definition
- **THEN** the admin entrypoint routes to `definition-authoring`
- **AND THEN** the authoring route refreshes the root README before returning derivation findings

#### Scenario: README does not replace maintained commands

- **WHEN** the authoring route generates or refreshes workspace orientation
- **THEN** it continues using maintained `houmao-mgr` commands for initialization, derivation, approval, materialization, and validation
- **AND THEN** it does not claim that README generation is a `houmao-mgr` subcommand

### Requirement: Definition guidance authors an explicit managed run mode

The packaged definition guidance SHALL use the mode resolver for specialist/profile and raw dossier authoring, fast-forward preparation, and project launch. It SHALL preserve explicit profile defaults and omit an unspecified mode. Unattended policy, gateway attachment, and mailbox defaults SHALL remain independent of mode.

#### Scenario: Profile preparation omits a mode

- **WHEN** the operator prepares an unattended Codex or Claude profile or raw launch dossier without specifying a mode
- **THEN** the instructions omit a mode override and describe the TUI project default

#### Scenario: Fast-forward prepares a DSH profile

- **WHEN** the operator asks for a launchable DSH profile with ordinary interactive defaults
- **THEN** the instructions report the native Web default and a usable launch command

#### Scenario: A specific mode is required

- **WHEN** a caller requests a qualified service or a headless-only lane
- **THEN** the workflow authors that explicit mode and explains an unavailable pair through the supported matrix

### Requirement: Definition guidance uses Kimi's supported project modes

Kimi specialist examples SHALL select `kimi` in project commands and config drafts. Profile and launch guidance SHALL preserve its ordinary TUI default and honor explicitly selected qualified modes. Credential references for supported tools SHALL resolve in the installed skill and route through the documented selection flow.

#### Scenario: A caller authors a Kimi specialist

- **WHEN** the packaged guidance shows a Kimi specialist or project draft
- **THEN** the selected tool is Kimi and the later launch takes the saved or requested mode

#### Scenario: An operator requests another Kimi mode

- **WHEN** a Kimi profile selects an implemented service or Web mode
- **THEN** the launch handoff preserves that mode and reports a limitation for an unsupported installed build

#### Scenario: A credential link is shown

- **WHEN** the installed guidance references Kimi or another maintained tool's credentials
- **THEN** the referenced packaged location exists and documents the supported credential flow

### Requirement: Definition guidance authors saved tmux server selectors
The definition skill SHALL teach saving tmux selectors with `project profile create|set` for specialist-backed profiles and `project agents launch-profiles add|set` for recipe-backed project profiles. It SHALL keep these flags within those project profile command families.

#### Scenario: An operator saves a tmux server choice for future launches
- **WHEN** the operator chooses a tmux server while authoring one of the two project profile types
- **THEN** the skill describes `user-default`, `houmao-default`, `new`, and `socket`
- **AND THEN** it explains that `socket` requires an absolute `--tmux-socket-path` in the execution owner's context and selects an existing server at launch
- **AND THEN** it shows that the profile's matching `get` command reports `defaults.posture.tmux`

#### Scenario: A profile patch preserves or clears the selected server
- **WHEN** an operator patches an existing profile
- **THEN** the skill explains that omitting tmux options preserves the saved selector, setting a mode replaces it, and `set --clear-tmux-server` restores launch-time fallback
- **AND THEN** it keeps those options distinct from native launch-dossier authoring and other launch posture options
### Requirement: Agent definition skill fixes Qualified Modes table and covers post-3.0.0 launch and DSH flags
`houmao-agent-definition` SHALL fix `references/common/profile-lanes.md` (`Claude: headless|tui`, `Codex: headless|service|tui`, `Kimi: headless|service|tui|web`, `DSH: headless|service|web`) and add `dsh`, `--tool-params`, `--clear-tool-params`, `tool_params.permissions`, `--headless-display-*`, `--reuse-home`, `--relaunch-chat-session-mode`, `--executor`, `--force`, `--agent-id-mode`, `--gateway-admin-seed`, `--system-skill-pack`/`--system-skills-mode`, and `managed_header` v2.

#### Scenario: Authoring and launch pages expose accurate run modes and DSH flags
- **WHEN** an admin creates a specialist, profile, launch dossier, deployment, or easy launch using `dsh`, `service`/`web` modes, or `tool_params`
- **THEN** `references/common/profile-lanes.md` lists exact per-tool qualified modes matching runtime validation
- **AND THEN** `specialists.md`, `profiles.md`, `recipe-profiles.md`, `launch-dossiers.md`, `deployment.md`, and `launch-instance.md` include `dsh` and current post-3.0.0 flags

### Requirement: Agent definition skill reconciles legacy command pages and deduplicates SKILL-MAIN.md
`houmao-agent-definition` SHALL resolve the five unindexed root pages (`create.md`, `get.md`, `list.md`, `remove.md`, `set.md`) and `low-level/raw-profiles.md` against `## Subcommands` and `manifest.toml`, remove inlined launcher and config-draft JSON examples already owned by `references/` and `commands/`, and remove obsolete `houmao-cli` guardrails.

#### Scenario: Entrypoint and command inventory have no duplicate or orphaned pages
- **WHEN** a reviewer inspects `houmao-agent-definition` against `imsight-agent-skill-handling`
- **THEN** `SKILL-MAIN.md` references `references/common/launcher.md` and `commands/` pages instead of inlining duplicate launcher steps and JSON payloads
- **AND THEN** every file under `commands/` maps cleanly to the `## Subcommands` table and `manifest.toml`

### Requirement: Agent definition skill preserves admin gate, alias, minimal drafts, and authoring invariants
`houmao-agent-definition` SHALL preserve admin-only `## Actor Frame Gate`, the `specialist-mgr` compatibility alias, minimal `internals config-drafts generate` payloads, the `definition-authoring` derive/approve/materialize/validate lifecycle, `definition-deployment` and atomic `definition-batch` (`1..32`), saved `--tmux-server`, and no same-root mailbox preregistration.

#### Scenario: Config draft generation and batch deployment preserve strict invariants
- **WHEN** an admin generates a minimal config draft or applies a batch deployment
- **THEN** `config-drafts generate` accepts only minimal `{"fields":{...}}` holes without memo seeds or launch overrides
- **AND THEN** `definition-batch` preserves `--count 1..32`, narrow delegation flags, and no premature per-agent mailbox preregistration
