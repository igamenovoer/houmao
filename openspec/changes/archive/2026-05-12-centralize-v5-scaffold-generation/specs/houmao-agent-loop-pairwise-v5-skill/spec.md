## ADDED Requirements

### Requirement: V5 packages a shared scaffold generator and template assets
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL include a Python scaffold generator inside the v5 skill package.

The packaged `houmao-agent-loop-pairwise-v5` skill SHALL include bundled scaffold template assets for Markdown and TOML starter files owned by the scaffold generator.

The scaffold generator SHALL use the bundled template assets as the authoritative source for starter scaffold content instead of requiring routed pages to synthesize those file bodies independently.

The scaffold generator SHALL use Python stdlib only unless a later change explicitly approves an additional dependency.

#### Scenario: Packaged skill includes generator resources
- **WHEN** the v5 skill is inspected in the repository
- **THEN** it includes a Python scaffold generator under the skill package
- **AND THEN** it includes bundled template assets for starter scaffold files used by that generator

#### Scenario: Starter content comes from packaged templates
- **WHEN** a v5 route needs to create starter Markdown or TOML scaffold files
- **THEN** the route uses the packaged scaffold generator and its bundled templates
- **AND THEN** the route does not rely on separately authored inline starter-file bodies in multiple pages

### Requirement: V5 scaffold-producing routes use shared generator profiles
The scaffold-producing routes in `houmao-agent-loop-pairwise-v5` SHALL use the shared scaffold generator rather than describing separate ad hoc file creation flows.

The `init` and `create-intention` routes SHALL use a shared profile for `intention/` scaffold creation.

The `execplan-fast-forward` route SHALL use a shared profile for non-interactive `execplan/` shell creation.

The `execplan-step-by-step` route SHALL use the same execplan shell scaffold surface, with an explicit option or profile that includes `execplan/adrs/`.

The `execplan-finalize` route SHALL use a shared scaffold surface for starter support docs or README material that belongs to the centralized scaffold layer.

#### Scenario: Init and create-intention share one scaffold path
- **WHEN** a user asks v5 to initialize loop intention material
- **THEN** the routed authoring page uses the shared intention scaffold profile
- **AND THEN** `intention/README.md` and `intention/loop-overview.md` come from the centralized scaffold surface

#### Scenario: Fast-forward and step-by-step share execplan shell scaffolding
- **WHEN** a user asks v5 to run `execplan-fast-forward` or `execplan-step-by-step`
- **THEN** both routes scaffold the `execplan/` package through the shared execplan scaffold surface
- **AND THEN** `execplan-step-by-step` includes `execplan/adrs/` only through the explicit stepwise scaffold option or profile

## MODIFIED Requirements

### Requirement: V5 authoring creates an editable intention source area
The v5 authoring workflow SHALL create or maintain `<loop-dir>/intention/` as the editable source area for user intention Markdown.

The intention source area SHALL be created through the packaged shared scaffold generator and bundled template assets rather than by repeated page-local starter-file prose.

The intention source area SHALL include `<loop-dir>/intention/README.md` describing the purpose and conventions of the area.

The intention source area SHALL include `<loop-dir>/intention/loop-overview.md` as the human entrypoint for the loop intention.

The intention source area SHALL allow additional Markdown files to be mostly freeform. User edits to intention Markdown SHALL be treated as expected source edits rather than generated-output drift.

#### Scenario: Authoring initializes intention files
- **WHEN** a user provides an intention and a `<loop-dir>` for a new v5 loop
- **THEN** the skill creates `<loop-dir>/intention/README.md`
- **AND THEN** the skill creates `<loop-dir>/intention/loop-overview.md`
- **AND THEN** the overview records the user intention as editable source material

#### Scenario: User edits remain valid source
- **WHEN** a user manually edits Markdown under `<loop-dir>/intention/`
- **THEN** the skill treats those edits as current source input for later refinement or execplan generation
- **AND THEN** the skill does not require the freeform intention files to match a strict generated-template schema

#### Scenario: Intention starter files come from centralized scaffold assets
- **WHEN** the v5 authoring workflow initializes `intention/`
- **THEN** it uses the packaged shared scaffold generator and bundled templates
- **AND THEN** it does not require separate routed pages to define independent starter-file bodies for `README.md` and `loop-overview.md`

### Requirement: V5 generates an execplan package from intention source
The v5 authoring workflow SHALL generate `<loop-dir>/execplan/` as the generated execution package derived from the current intention source.

The v5 scaffold-producing execplan routes SHALL create the initial `execplan/` shell through the packaged shared scaffold generator and bundled template assets.

The generated execplan package SHALL include `manifest.toml` at its root.

The generated execplan package SHALL use the top-level generated layout:

- `specs/`,
- `skills/`,
- `agents/`,
- `harness/`,
- `docs/`.

The skill SHALL label or describe execplan content as generated material and SHALL treat intention Markdown as the editable source of truth for later execplan updates.

#### Scenario: Execplan uses the generated package layout
- **WHEN** the skill generates an execplan for a v5 loop
- **THEN** `<loop-dir>/execplan/manifest.toml` exists
- **AND THEN** `<loop-dir>/execplan/specs/` exists
- **AND THEN** `<loop-dir>/execplan/skills/` exists
- **AND THEN** `<loop-dir>/execplan/agents/` exists
- **AND THEN** `<loop-dir>/execplan/harness/` exists
- **AND THEN** `<loop-dir>/execplan/docs/` exists

#### Scenario: Intention is the execplan update source
- **WHEN** a user changes the loop source after an execplan was generated
- **THEN** the v5 `update-execplan` workflow reads from `<loop-dir>/intention/`
- **AND THEN** it updates `<loop-dir>/execplan/` as generated output

#### Scenario: Execplan shell comes from centralized scaffold assets
- **WHEN** a v5 route needs to create the initial `execplan/` shell, starter manifest, or starter support docs
- **THEN** it uses the packaged shared scaffold generator and bundled templates
- **AND THEN** it does not define those starter artifacts independently in multiple routed pages

### Requirement: All-stage generation and update orchestration use staged execplan order
The `execplan-fast-forward` operation SHALL scaffold `execplan/` and orchestrate the staged execplan subcommands in dependency order without optional generation questions unless the user explicitly asks for one staged subcommand.

The `execplan-fast-forward` scaffold step SHALL use the packaged shared scaffold generator and bundled execplan shell templates.

The `execplan-step-by-step` operation SHALL scaffold `execplan/`, then orchestrate the same staged execplan subcommands in dependency order while asking at most one unresolved generation-decision question at a time.

The `execplan-step-by-step` scaffold step SHALL use the same packaged shared scaffold generator, with explicit support for `execplan/adrs/`.

The `execplan-step-by-step` operation SHALL record accepted artifact-generation decisions under `<loop-dir>/execplan/adrs/` and SHALL revise affected execplan artifacts after each accepted decision.

The packaged skill SHALL NOT expose `generate-execplan` as a separate operation name; all non-interactive full execplan generation SHALL route through `execplan-fast-forward`.

The `update-execplan` operation SHALL determine the earliest affected stage from the changed intention source or explicit user request, then rerun that stage and downstream stages as needed.

The `execplan-finalize` stage SHALL produce final support docs, package README updates, final manifest entries, generated metadata, explicit omission notes, and consistency notes after authoritative generated artifacts exist.

The manifest MAY be seeded before finalization, but final manifest content SHALL be produced or checked during `execplan-finalize`.

#### Scenario: Execplan-fast-forward runs all stages
- **WHEN** a user asks v5 to `execplan-fast-forward`
- **THEN** the operation runs `execplan-specs-process`, `execplan-specs-contract`, `execplan-harness`, `execplan-skills`, `execplan-agent-bindings`, and `execplan-finalize` in order
- **AND THEN** it runs or requests `validate-execplan` before reporting the execplan ready

#### Scenario: Execplan-step-by-step records accepted generation decisions
- **WHEN** a user asks v5 to `execplan-step-by-step`
- **THEN** the operation scaffolds `execplan/` including `execplan/adrs/`
- **AND THEN** it asks one generation-decision question at a time only when a material artifact choice is not derivable from source or defaults
- **AND THEN** each accepted decision is recorded under `execplan/adrs/` and reflected in affected generated artifacts before continuing downstream

#### Scenario: Update-execplan reruns affected downstream stages
- **WHEN** intention changes affect participant process flow or handoff semantics
- **THEN** `update-execplan` starts from `execplan-specs-process`
- **AND THEN** it reruns downstream stages whose generated artifacts depend on the changed process model

#### Scenario: Finalization is last
- **WHEN** a staged generation run reaches `execplan-finalize`
- **THEN** generated docs, package README, final manifest content, generated metadata, and explicit omission notes reflect the artifacts actually emitted by earlier stages
- **AND THEN** finalization does not introduce new authoritative process, contract, harness, skill, or agent-binding semantics that bypass earlier stages

#### Scenario: Both all-stage routes use the shared scaffold generator
- **WHEN** `execplan-fast-forward` or `execplan-step-by-step` begins scaffold creation
- **THEN** the route uses the packaged shared scaffold generator and bundled templates for the execplan shell it owns
- **AND THEN** the route does not rely on independently maintained page-local scaffold definitions
