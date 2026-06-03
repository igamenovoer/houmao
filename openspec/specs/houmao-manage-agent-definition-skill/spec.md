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

### Requirement: `houmao-agent-definition` prefers TUI-supported launch posture when unspecified
The packaged `houmao-agent-definition` skill SHALL instruct agents that omitted headless/TUI launch posture means "prefer TUI/local interactive when the selected tool or launch lane supports it."

This default SHALL apply to skill guidance for specialist-backed project profile authoring, raw recipe-backed launch-profile authoring, create-agent-fast-forward profile preparation, and the specialist-scoped easy launch entry point.

The skill SHALL NOT tell agents to add `--headless`, persist profile `--headless`, or report headless as a stored default unless the user explicitly asks for headless posture or the selected tool/lane is known to require headless.

The skill SHALL keep prompt mode separate from launch posture: `--prompt-mode unattended` SHALL NOT imply `--headless`, and an unspecified headless/TUI posture SHALL remain TUI-preferred when supported even if prompt mode defaults to unattended.

The skill SHALL identify Gemini easy launches as a known required-headless exception and SHALL preserve explicit stored headless posture when inspecting or launching from an existing profile.

#### Scenario: Project profile creation omits headless by default
- **WHEN** a user asks `houmao-agent-definition profiles` or `create-agent-fast-forward` to create a Codex or Claude project profile
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless` from `project profile create`
- **AND THEN** it treats the resulting profile as TUI/local-interactive preferred for later launch when supported

#### Scenario: Launch dossier authoring omits headless by default
- **WHEN** a user asks `houmao-agent-definition launch-dossiers` to add or update a recipe-backed launch profile
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it does not infer headless from unattended prompt mode, gateway defaults, mailbox defaults, or model defaults

#### Scenario: Fast-forward launch command stays TUI-preferred when supported
- **WHEN** `create-agent-fast-forward` prepares a launchable project profile for a TUI-capable tool
- **AND WHEN** the user does not request headless execution
- **THEN** the workflow reports a launch command without `--headless`
- **AND THEN** it reports that launch posture is TUI/local-interactive preferred when supported

#### Scenario: Required-headless exception remains explicit
- **WHEN** `houmao-agent-definition launch-agent` prepares a Gemini easy launch command
- **THEN** the skill guidance may require `--headless`
- **AND THEN** it describes that as a selected-tool requirement rather than the default for unspecified launch posture

### Requirement: `houmao-agent-definition` uses config drafts for supported config authoring flows
The packaged `houmao-agent-definition` skill SHALL instruct agents to use `houmao-mgr internals config-drafts generate` before authoring supported project configuration documents for these skill subcommands:

- `specialists`
- `profiles`
- `launch-dossiers`
- profile preparation inside `create-agent-fast-forward`

For those supported config-authoring flows, the skill SHALL tell agents to generate drafts from explicit user inputs and recovered explicit context only.

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

