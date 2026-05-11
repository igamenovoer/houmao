## ADDED Requirements

### Requirement: Houmao provides a packaged manual `houmao-agent-loop-pairwise-v5` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v5` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v5` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-pairwise-v5` skill SHALL be manual-invocation-only. It SHALL only activate when the user explicitly requests `houmao-agent-loop-pairwise-v5` or an explicitly named v5 loop operation.

The packaged skill SHALL describe itself as a general v5 loop authoring and execution skill rather than as a CUDA, Hopper, or domain-specific optimization skill.

#### Scenario: User explicitly invokes v5
- **WHEN** a user explicitly asks to use `houmao-agent-loop-pairwise-v5`
- **THEN** the packaged v5 skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents a general loop authoring and execution workflow

#### Scenario: Generic loop request does not auto-route to v5
- **WHEN** a user asks generically to plan or run an agent loop without naming `houmao-agent-loop-pairwise-v5`
- **THEN** the v5 skill does not claim the request by default
- **AND THEN** the user must explicitly select v5 before v5-specific files or operations are created

### Requirement: V5 skill creation invokes skill-creator guidance
When creating or substantially updating the packaged `houmao-agent-loop-pairwise-v5` skill assets, the implementation agent SHALL invoke `$skill-creator` before authoring the skill files.

The implementation SHALL apply skill-creator guidance for skill anatomy, concise instructions, progressive disclosure, bundled resource placement, `agents/openai.yaml` metadata, and validation.

If a generic skill initialization helper is unsuitable for the packaged system-skill asset location, the implementation SHALL still follow the skill-creator workflow principles and report why the helper was not used.

#### Scenario: Implementer invokes skill-creator before creating v5 assets
- **WHEN** implementation begins creating `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`
- **THEN** the implementer invokes `$skill-creator`
- **AND THEN** the resulting skill asset structure follows skill-creator anatomy and progressive-disclosure guidance

#### Scenario: Packaged location can justify not using a generic initializer
- **WHEN** the generic skill initialization helper does not fit the repository-packaged system-skill location
- **THEN** the implementer records that reason in the implementation summary
- **AND THEN** the implementer still creates valid `SKILL.md` frontmatter, `agents/openai.yaml`, and only necessary bundled resources

### Requirement: V5 requires a user-selected loop directory before authoring or generation
The `houmao-agent-loop-pairwise-v5` skill SHALL require a user-provided `<loop-dir>` before creating intention files, generating an execplan, or operating a v5 loop.

The skill SHALL treat `<loop-dir>` as the root for v5 loop source and generated execution material.

The skill SHALL NOT invent a default loop directory when the user has not provided one.

The skill SHALL keep v5-owned authoring and generated artifacts under the selected `<loop-dir>` unless the user explicitly asks for inspection of external references.

#### Scenario: Missing loop directory blocks file creation
- **WHEN** a user asks v5 to author a new loop but does not provide `<loop-dir>`
- **THEN** the skill asks for the required loop directory
- **AND THEN** it does not create intention or execplan files before that directory is known

#### Scenario: Provided loop directory becomes the v5 root
- **WHEN** a user provides `<loop-dir>` for a v5 loop
- **THEN** the skill creates or uses v5-owned files under that directory
- **AND THEN** the skill does not scatter generated loop files into unrelated paths

### Requirement: V5 authoring creates an editable intention source area
The v5 authoring workflow SHALL create or maintain `<loop-dir>/intention/` as the editable source area for user intention Markdown.

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

### Requirement: V5 generates an execplan package from intention source
The v5 authoring workflow SHALL generate `<loop-dir>/execplan/` as the generated execution package derived from the current intention source.

The generated execplan package SHALL include `manifest.toml` at its root.

The generated execplan package SHALL use the top-level generated layout:

- `specs/`,
- `skills/`,
- `agents/`,
- `harness/`,
- `docs/`.

The skill SHALL label or describe execplan content as generated material and SHALL treat intention Markdown as the editable source of truth for regeneration.

#### Scenario: Execplan uses the generated package layout
- **WHEN** the skill generates an execplan for a v5 loop
- **THEN** `<loop-dir>/execplan/manifest.toml` exists
- **AND THEN** `<loop-dir>/execplan/specs/` exists
- **AND THEN** `<loop-dir>/execplan/skills/` exists
- **AND THEN** `<loop-dir>/execplan/agents/` exists
- **AND THEN** `<loop-dir>/execplan/harness/` exists
- **AND THEN** `<loop-dir>/execplan/docs/` exists

#### Scenario: Intention is the regeneration source
- **WHEN** a user changes the loop source after an execplan was generated
- **THEN** the v5 regeneration workflow reads from `<loop-dir>/intention/`
- **AND THEN** it updates `<loop-dir>/execplan/` as generated output

### Requirement: V5 skill guidance is split into authoring and execution subskills
The top-level `houmao-agent-loop-pairwise-v5` skill SHALL act as an index and router for v5 subskills rather than carrying the whole workflow in one instruction file.

The packaged v5 skill SHALL include authoring subskills for creating intention material, refining intention material, generating execplans, validating execplans, and regenerating execplans.

The packaged v5 skill SHALL include execution subskills for preparing agents, starting a loop, checking status, pausing, resuming, recovering, and stopping.

Each subskill SHALL define its trigger, inputs, outputs, and boundaries.

#### Scenario: Top-level skill routes authoring work
- **WHEN** a user asks v5 to create, refine, generate, validate, or regenerate loop material
- **THEN** the top-level skill routes to an authoring subskill
- **AND THEN** the authoring subskill handles the requested authoring operation within the selected `<loop-dir>`

#### Scenario: Top-level skill routes execution work
- **WHEN** a user asks v5 to prepare, start, inspect status, pause, resume, recover, or stop a loop
- **THEN** the top-level skill routes to an execution subskill
- **AND THEN** the execution subskill works from the generated `<loop-dir>/execplan/` and maintained Houmao operation surfaces

### Requirement: V5 execution uses generated execplan material and maintained Houmao operation surfaces
The v5 execution workflow SHALL operate from the generated `<loop-dir>/execplan/` package.

When execution needs platform operations such as managed-agent launch, prompt delivery, mailbox work, gateway work, memory work, lifecycle control, or inspection, the v5 execution subskills SHALL route through maintained Houmao operation skills or CLI surfaces rather than duplicating those contracts locally.

When execution needs loop-local state or generated role behavior, the v5 execution subskills SHALL use the generated execplan contracts, generated skills, generated agent bindings, generated docs, or generated harness surfaces.

#### Scenario: Agent preparation composes existing Houmao surfaces
- **WHEN** a v5 execution subskill prepares agents for a generated execplan
- **THEN** it uses maintained Houmao specialist, instance, mailbox, gateway, memory, or project-skill surfaces as appropriate
- **AND THEN** it does not hand-edit Houmao runtime internals as the normal preparation path

#### Scenario: Loop-local execution consults execplan
- **WHEN** a v5 execution subskill needs loop role instructions or loop-local runtime behavior
- **THEN** it reads or invokes the relevant generated material under `<loop-dir>/execplan/`
- **AND THEN** it does not treat freeform intention Markdown as the direct runtime contract

### Requirement: Initial v5 authoring does not require ADR input
The initial v5 authoring workflow SHALL NOT require an `adrs/` directory.

The initial v5 authoring workflow SHALL NOT scan ADR files as a required source input for execplan generation.

The initial v5 validation workflow SHALL NOT fail a loop only because `<loop-dir>/adrs/` is absent.

ADR support MAY be added by a later change, but it SHALL remain outside the initial v5 contract.

#### Scenario: Loop without ADRs can generate an execplan
- **WHEN** a v5 loop has `<loop-dir>/intention/README.md` and `<loop-dir>/intention/loop-overview.md`
- **AND WHEN** `<loop-dir>/adrs/` does not exist
- **THEN** the v5 authoring workflow can still generate or validate `<loop-dir>/execplan/`

### Requirement: V5 remains domain-neutral
The packaged v5 skill SHALL NOT encode CUDA optimization, Hopper, SM90a, kernel-variant, or other domain-specific requirements as part of its general skill contract.

Domain-specific objectives, participants, policies, tools, evidence gates, or generated role behavior SHALL come from the user-provided intention source and generated per-loop execplan material.

Domain-specific existing loop-plan directories MAY be referenced as examples or fixtures, but they SHALL NOT define mandatory behavior for all v5 loops.

#### Scenario: Non-CUDA loop can use v5
- **WHEN** a user asks v5 to create a loop for a non-CUDA objective
- **THEN** the skill can create intention material and generate an execplan for that objective
- **AND THEN** the skill does not require Hopper, CUDA, kernel variants, or timing policy fields

#### Scenario: CUDA reference does not become global policy
- **WHEN** a generated execplan example includes CUDA-specific policies
- **THEN** those policies remain specific to that example loop
- **AND THEN** the packaged v5 skill does not copy them into unrelated v5 loops as required global policy
