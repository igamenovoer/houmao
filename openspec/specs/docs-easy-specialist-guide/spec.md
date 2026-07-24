# docs-easy-specialist-guide Specification

## Purpose
Define the documentation requirements for the easy-specialist conceptual guide in the getting-started section.
## Requirements
### Requirement: Easy-specialist conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/easy-specialists.md` documenting the easy lane as a three-step model: specialist, optional project profile, and easy instance. The page SHALL retain the existing filename so that incoming README and `docs/index.md` cross-links continue to resolve.

The page SHALL explain:

- What an easy-specialist is: a lightweight, project-local agent definition that bundles a role, tool, setup, auth, optional skills, and durable launch configuration into a single named source definition.
- What an project profile is: a reusable specialist-backed birth-time launch configuration object that targets exactly one specialist and stores defaults for managed-agent identity, working directory, auth override, mailbox configuration, launch posture, durable env records, prompt overlay, and optional memo seed. Project profiles are project-local catalog objects in the same shared launch-profile family that backs native launch dossiers.
- When to use specialist alone, when to use specialist plus project profile, and when to drop down to the explicit recipe + launch-profile lane: specialist alone is the recommended path for one-off setups; project profile is the natural step when the same specialist needs to be relaunched with the same managed-agent identity, workdir, mailbox, and memo seed each time; the explicit recipe + launch-profile lane is for operators who need fine-grained control over the underlying source recipe.
- The full lifecycle: `specialist create` defines the source template, optional `profile create` captures reusable birth-time defaults over that specialist, `instance launch` creates a running managed agent from either the specialist directly or from an project profile, and `instance stop` shuts it down.
- Relationship to managed agents: an easy instance IS a managed agent — it appears in `agents list`, can be targeted by `agents prompt`, `agents gateway`, `agents mail`, etc.
- CLI commands: `project specialist create|list|get|remove`, `project profile create|list|get|remove`, and `project agents launch|list|get|stop`, including `instance launch --profile <name>` and the `--profile`/`--specialist` mutual exclusion rule.
- Easy-instance inspection: `instance list` and `instance get` SHALL report the originating project-profile identity when runtime-backed state makes it resolvable, and SHALL continue to report the originating specialist when available.

The page SHALL document project-profile memo seed source options without documenting a memo seed policy option.

The page SHALL include a mermaid diagram showing the three-step easy lane (specialist → optional project profile → instance → managed agent). The page SHALL NOT use plain-text ASCII art for that diagram.

The comparison at the top of the page SHALL be a three-way comparison that distinguishes specialist alone, specialist plus project profile, and explicit recipe plus launch-profile, rather than the previous two-way "specialist vs full preset" comparison.

The page SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model and to `docs/reference/cli/houmao-mgr.md` for the canonical CLI reference.

The page SHALL be derived from `project/easy.py`, `project/launch_profiles.py`, and `srv_ctrl/commands/project.py` easy-lane command implementations.

#### Scenario: Reader understands the three easy-lane object roles

- **WHEN** a reader opens the easy-specialist guide
- **THEN** they find a clear distinction between specialist (the source definition), project profile (reusable birth-time configuration over one specialist), and easy instance (the runtime object)
- **AND THEN** they understand that project profiles and native launch dossiers share one underlying catalog-backed launch-profile object family

#### Scenario: Reader can create a specialist, an project profile, and launch from the profile

- **WHEN** a reader follows the easy-specialist guide
- **THEN** they find step-by-step commands: `project specialist create --name <name> --tool <tool> ...`, then `project profile create --name <profile> --specialist <name> ...`, then `project agents launch --profile <profile>`
- **AND THEN** they understand that `--profile` and `--specialist` cannot be combined on `instance launch`
- **AND THEN** they understand that when `--profile` is used, the launch derives the source specialist from the stored profile and applies project-profile defaults before direct CLI overrides

#### Scenario: Reader sees project-profile memo seed source controls

- **WHEN** a reader checks project-profile stored defaults
- **THEN** the guide documents `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`
- **AND THEN** the guide does not document `--memo-seed-policy`

#### Scenario: Reader sees easy-instance inspection report the project-profile origin

- **WHEN** a reader looks up `project agents get` in the guide
- **THEN** the page documents that the inspection output reports both the originating project-profile and the originating specialist when those identities are resolvable from runtime-backed state

#### Scenario: Reader uses a mermaid diagram for the lane shape

- **WHEN** a reader scans the guide for the easy-lane lifecycle picture
- **THEN** the lifecycle diagram is rendered as a mermaid fenced code block
- **AND THEN** the page does not use plain-text ASCII art for the lifecycle shape

#### Scenario: Reader sees a three-way comparison instead of the old two-way one

- **WHEN** a reader checks the comparison section near the top of the guide
- **THEN** the comparison covers specialist, specialist plus project profile, and explicit recipe plus launch-profile
- **AND THEN** the comparison does not present the choice as "specialist vs full preset" only

#### Scenario: Reader understands instance lifecycle

- **WHEN** a reader wants to manage easy instances
- **THEN** the page documents `instance list` for discovery, `instance get` for detailed state, and `instance stop` for shutdown
- **AND THEN** the page explains that instances are tracked in the shared registry like any other managed agent

### Requirement: Easy-specialist guide distinguishes Claude credentials from the optional state template
The easy-specialist guide at `docs/getting-started/easy-specialists.md` SHALL describe Claude credential-providing methods separately from the optional `--claude-state-template-file` input.

When the guide describes Claude specialist authoring, it SHALL make clear that `claude_state.template.json` is optional runtime bootstrap state and not itself a credential-providing method.

#### Scenario: Reader sees Claude state template documented as optional bootstrap input
- **WHEN** a reader follows the easy-specialist guide for a Claude specialist
- **THEN** the page distinguishes Claude credential inputs from `--claude-state-template-file`
- **AND THEN** it describes the state-template file as optional bootstrap state rather than as Claude credentials

### Requirement: Easy-specialist guide documents easy-lane managed-header controls
The easy-specialists guide SHALL document the managed-header controls that affect:

- `project profile create`
- `project agents launch`

The page SHALL explain:
- that project-profile creation can store managed-header policy,
- that easy-instance launch can force-enable or disable the managed header for one launch,
- that the one-shot easy-instance override does not rewrite the stored project profile.

#### Scenario: Reader finds managed-header controls on project profile create and easy instance launch
- **WHEN** a reader checks the easy-lane operator workflow
- **THEN** the page documents the managed-header create-time profile control and the one-shot easy-instance launch override
- **AND THEN** the page explains how those controls interact for profile-backed easy launch

### Requirement: Easy-specialist guide documents project-profile editing
The easy-specialist guide SHALL document how to edit an existing project profile with `houmao-mgr project profile set --name <profile> ...`.

The guide SHALL explain that project-profile `set` preserves unspecified stored defaults, while `project profile create --name <profile> --specialist <specialist> --yes` performs same-lane replacement and clears omitted optional defaults.

The guide SHALL state that project-profile replacement cannot replace an explicit launch profile that happens to use the same name.

#### Scenario: Reader can edit an project profile without removing it
- **WHEN** a reader opens the project-profile section of the easy-specialist guide
- **THEN** they find an example using `project profile set --name <profile>`
- **AND THEN** they learn that manual remove/recreate is not required for ordinary stored default changes

#### Scenario: Reader understands project-profile replacement semantics
- **WHEN** a reader opens the project-profile management guidance
- **THEN** the guide explains that `create --yes` replaces a same-lane project profile
- **AND THEN** the guide explains that omitted optional fields are cleared during replacement

### Requirement: Easy-specialist guide documents specialist editing
The easy-specialist guide SHALL document how to edit an existing specialist with `houmao-mgr project specialist set --name <specialist> ...`.

The guide SHALL explain that specialist `set` preserves unspecified stored source-definition fields, while `project specialist create --name <specialist> --tool <tool> ... --yes` performs same-name replacement with create semantics and may clear omitted optional fields.

The guide SHALL include at least one example that changes skill bindings without removing and recreating the specialist.

The guide SHALL state that specialist edits affect future launches or rebuilds from that specialist and do not mutate already-running managed agents in place.

#### Scenario: Reader can edit a specialist skill list without recreating it
- **WHEN** a reader opens the easy-specialist guide
- **THEN** they find an example using `project specialist set --name <specialist>` to add or remove a skill binding
- **AND THEN** they learn that manual remove/recreate is not required for ordinary specialist source-definition edits

#### Scenario: Reader understands specialist replacement semantics
- **WHEN** a reader opens the specialist management guidance
- **THEN** the guide explains that `create --yes` replaces the same-name specialist with create semantics
- **AND THEN** the guide distinguishes replacement from patching through `specialist set`

#### Scenario: Reader understands running-agent boundary
- **WHEN** a reader checks the specialist editing guidance
- **THEN** the guide states that editing the specialist source affects future launches or rebuilds
- **AND THEN** it does not imply that already-running managed agents are updated in place

### Requirement: Easy-specialist guide documents project skill registration and name-based binding
The easy-specialist guide SHALL explain that project-local custom skills are registered first and then bound to specialists by name.

At minimum, the guide SHALL document:

- `houmao-mgr project skills add --name <name> --source <dir> --mode copy|symlink`
- `houmao-mgr project specialist create --skill <name>`
- `houmao-mgr project specialist set --add-skill <name>`

If the guide documents `--with-skill <dir>`, it SHALL describe that flag as a convenience path that registers or updates the canonical project skill entry before binding the resulting registered skill to the specialist.

The guide SHALL explain that canonical project skill storage lives under `.houmao/content/skills/`, while `.houmao/agents/skills/` is derived projection only.

The guide SHALL direct existing users with older easy-specialist project metadata to `houmao-mgr project migrate` instead of implying that `project` commands silently upgrade those specialist definitions in place.

#### Scenario: Reader learns to register a skill before binding it to a specialist
- **WHEN** a reader follows the easy-specialist authoring guide
- **THEN** the guide shows `project skills add` before `project specialist create --skill <name>` or `set --add-skill <name>`
- **AND THEN** the guide does not present `.houmao/agents/skills/` as the canonical skill authoring root

#### Scenario: Reader sees explicit migration guidance for older easy-specialist state
- **WHEN** a reader already has one older project overlay with legacy easy-specialist metadata
- **THEN** the guide directs them to `houmao-mgr project migrate`
- **AND THEN** the guide does not imply that ordinary `project` commands will silently upgrade that metadata

### Requirement: Easy-specialist guide documents current Codex and Kimi reasoning ladders
The easy-specialist guide SHALL document the maintained GPT-5.6 Sol, Terra, and Luna reasoning-level mappings, including `ultra` only for models whose Codex catalog advertises it. The guide SHALL explain that Kimi reasoning levels follow the selected alias's declared ordered efforts and fail clearly when no maintained effort ladder is available.

#### Scenario: Reader can select GPT-5.6 ultra intentionally
- **WHEN** a reader wants a GPT-5.6 Sol or Terra specialist at `ultra`
- **THEN** the guide identifies reasoning level `6`
- **AND THEN** it does not claim Luna supports `ultra`

#### Scenario: Reader understands Kimi effort discovery
- **WHEN** a reader configures a Kimi specialist with a reasoning level
- **THEN** the guide explains that the selected model alias must declare an ordered effort ladder
- **AND THEN** it does not present a universal Kimi effort table
