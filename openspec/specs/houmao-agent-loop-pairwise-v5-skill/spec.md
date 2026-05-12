# houmao-agent-loop-pairwise-v5-skill Specification

## Purpose
TBD - created by archiving change add-general-pairwise-v5-loop-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged manual `houmao-agent-loop-pairwise-v5` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v5` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v5` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-pairwise-v5` skill SHALL be manual-invocation-only. It SHALL only activate when the user explicitly requests `houmao-agent-loop-pairwise-v5` or an explicitly named v5 loop operation.

The packaged skill SHALL describe itself as a general loop authoring and execution skill.

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

### Requirement: V5 skill guidance is split into authoring and execution subskills
The top-level `houmao-agent-loop-pairwise-v5` skill SHALL act as an index and router for v5 subskills rather than carrying the whole workflow in one instruction file.

The packaged v5 skill SHALL include authoring subskills for creating intention material, refining intention material, generating execplans, validating execplans, and updating generated execplans.

The packaged v5 skill SHALL include execution subskills for preparing agents, starting a loop, checking status, pausing, resuming, recovering, and stopping.

Each subskill SHALL define its trigger, inputs, outputs, and boundaries.

#### Scenario: Top-level skill routes authoring work
- **WHEN** a user asks v5 to create, refine, generate, validate, or update generated loop material
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

### Requirement: V5 derives domain behavior from intention source
The packaged v5 skill SHALL NOT encode domain-specific objectives, toolchains, topology, scheduling policy, evidence gates, or generated role behavior as part of its general skill contract.

Domain-specific objectives, participants, policies, tools, evidence gates, or generated role behavior SHALL come from the user-provided intention source and generated per-loop execplan material.

Existing loop-plan directories MAY be referenced as examples or fixtures, but they SHALL NOT define mandatory behavior for all v5 loops.

#### Scenario: Intention defines domain behavior
- **WHEN** a user asks v5 to create a loop for a specific objective
- **THEN** the skill can create intention material and generate an execplan for that objective
- **AND THEN** domain-specific fields are required only when the intention source introduces them

#### Scenario: Reference example does not become global policy
- **WHEN** a generated execplan example includes domain-specific policies
- **THEN** those policies remain specific to that example loop
- **AND THEN** the packaged v5 skill does not copy them into unrelated v5 loops as required global policy

### Requirement: V5 generation provides a generic default execplan scaffold
The packaged skill SHALL treat a reusable generated execplan scaffold as the default target when generating `<loop-dir>/execplan/` from intention source.

The default scaffold SHALL include generated artifact metadata and a manifest-indexed package with the existing top-level areas `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`.

The default `specs/` area SHALL provide places for objective contracts, collaboration contracts, communication contracts, runtime state contracts, workspace contracts, and participant contracts when the loop needs those concerns.

The generator SHALL allow irrelevant default areas or files to be omitted and task-specific areas or files to be added when the intention source or clarification decisions justify that shape.

#### Scenario: Generated execplan has reusable package contracts
- **WHEN** the skill generates an execplan for a loop whose intention does not override the package shape
- **THEN** the generated execplan includes a manifest-indexed package with `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`
- **AND THEN** generated specs separate objective, collaboration, communication, state, workspace, and participant concerns when those concerns apply

#### Scenario: Simple loop can omit unnecessary default files
- **WHEN** the current intention source describes a loop that does not need durable runtime state or a generated workspace contract
- **THEN** the generated execplan may omit those specific default files
- **AND THEN** the manifest and generated docs make the omission explicit enough for validation and later extension

### Requirement: V5 defaults participant and agent bindings to separated identities
The packaged skill SHALL guide generated execplans to separate participant role templates, participant role instances, and concrete Houmao agent bindings.

Generated participant contracts SHALL define stable loop participant identities and responsibilities without requiring a fixed topology or fixed role names.

Generated agent bindings SHALL bind concrete Houmao agents to participant instances and identify prompt source, installed generated skills, maintained support skills, skill installation mode, memo seed policy, and workspace policy when those facts apply.

#### Scenario: Participant identity is not the concrete process
- **WHEN** the skill generates participant and agent material for a loop
- **THEN** participant specs define stable role instances for the loop
- **AND THEN** agent bindings separately map concrete Houmao agents to those participant instances

#### Scenario: Topology remains intention-derived
- **WHEN** the intention source defines a custom participant topology
- **THEN** the generated participant and agent bindings follow that topology
- **AND THEN** the packaged skill does not force a built-in coordinator, reviewer, or worker count

### Requirement: V5 defaults stateful loops to a minimal runtime bookkeeping kernel
When a generated loop needs durable runtime state, the packaged skill SHALL guide the execplan to include a minimal loop-local bookkeeping kernel or an explicitly equivalent generated contract.

The default bookkeeping kernel SHALL cover plan metadata, process state, handoffs or exchanges, structured communication payload lifecycle, operator intent events, and generic events.

Task-specific records, evidence models, scoring models, and domain tables SHALL be generated only from intention source or clarification decisions.

#### Scenario: Stateful loop gets generic bookkeeping
- **WHEN** the intention source implies durable handoffs, scheduling decisions, recovery, or audit
- **THEN** the generated execplan includes generic loop-local bookkeeping contracts for process state, exchanges, payload lifecycle, operator intent, and events
- **AND THEN** task-specific records are added only as generated extensions

#### Scenario: Stateless loop does not inherit domain tables
- **WHEN** the intention source describes a lightweight loop without domain records
- **THEN** the generated execplan does not import task-specific record tables from examples
- **AND THEN** validation accepts the absence of those task-specific tables

### Requirement: V5 defaults generated harnesses to narrow loop-local services
The packaged skill SHALL guide generated execplans to include a plan-local harness when the loop needs validation, dynamic lookup, rendering, record application, or state queries.

The generated harness SHALL be scoped to loop-local contracts such as objective rendering, policy explanation, communication payload schema inspection, payload validation, Markdown rendering, state query, invariant validation, completion checks, and controlled record application.

Generated harness command registries SHALL reference generated package artifacts by relative path when reading specs, schemas, renderers, agent bindings, or other files in the same loop-definition package.

Generated harness scripts MAY use relative symlinks under `execplan/harness/refs/` for stable local access to generated package artifacts. If symlinks are unavailable because of filesystem permissions or environment limits, generated harness scripts SHALL use direct relative paths to the authoritative artifacts instead.

Generated harnesses SHALL keep `harness/schemas/` limited to harness-owned schemas such as command envelopes. Communication, record, state, workspace, participant, and objective schemas SHALL remain authoritative under `specs/` and be referenced rather than copied into `harness/`.

The generated harness SHALL NOT own Houmao platform operations such as mailbox delivery, mailbox administration, managed-agent launch, gateway discovery, prompt transport, memory management, or workspace creation.

Harness command output intended for agent use SHALL default to a structured envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings.

#### Scenario: Agent asks harness for dynamic loop facts
- **WHEN** a generated role skill needs objective, policy, state, route, schema, or completion facts
- **THEN** it uses the generated harness or generated contract surface to retrieve those facts
- **AND THEN** it does not rely on static copied values embedded in role prose

#### Scenario: Harness boundary excludes platform mechanics
- **WHEN** generated execution needs mailbox transport, agent launch, gateway posture, memory updates, or workspace creation
- **THEN** the generated execution guidance routes that work to maintained Houmao skills or supported CLI surfaces
- **AND THEN** the generated harness remains responsible only for loop-local data mechanics

### Requirement: V5 defaults generated role skills to bounded event and tick handlers
The packaged skill SHALL guide generated execplans to create generated role skills that are scoped by role and by event, tick, or operator lifecycle action.

Generated on-event skills SHALL define their trigger, owning participant role, required context lookup, role-owned action, outgoing communication behavior, record effects, archive behavior when mail is involved, and stopping point.

Generated on-tick skills SHALL be used for scheduling, reconciliation, timeout, completion, or "what happens next" behavior that does not belong to one incoming event.

Generated tick skills SHALL inspect current dynamic state, perform one bounded applicable action or report no action, and stop.

#### Scenario: Mail event handler is bounded
- **WHEN** a generated participant receives a loop-defined mail family that has an on-event skill
- **THEN** the on-event skill handles that received message family for the owning role
- **AND THEN** it stops after the bounded event response instead of recursively driving unrelated loop phases

#### Scenario: Scheduler behavior uses a tick handler
- **WHEN** a loop requires scheduling or reconciliation after one or more events
- **THEN** the generated execplan represents that responsibility as an on-tick skill for the owning role
- **AND THEN** the tick handler performs at most one scheduling or reconciliation pass before stopping

### Requirement: V5 documents notifier-prompt-driven mail runtime
The packaged skill SHALL guide generated mail-driven loops to model Houmao agents as notifier-prompt-driven rather than as agents waiting inside a chat turn.

The skill SHALL explain that Houmao email/notifier support runs separately from target agents, detects open mail, and sends the target agent a prompt that guides mail processing.

Generated mail-driven execplans SHALL allow loop-specific notification prompt instructions, including instructions to invoke the matching mail-received on-event skill and to call an on-tick skill after mail processing when the loop requires follow-up scheduling, reconciliation, timeout, or completion work.

Generated on-tick skills SHALL be prompt-invoked bounded passes rather than periodic background workers.

Generated role skills SHALL finish the chat turn after mail processing and any requested tick work. They SHALL NOT instruct agents to sleep, poll, tail logs, or wait in-chat for future loop work.

#### Scenario: Notifier prompt drives mail event processing
- **WHEN** a mail-driven generated loop has open mail for a participant agent
- **THEN** Houmao notifier support is the expected wakeup mechanism that prompts the agent
- **AND THEN** the agent processes the mail through the generated message-family behavior and maintained Houmao mail support

#### Scenario: Tick after mail is prompt-directed
- **WHEN** the generated loop requires scheduling, reconciliation, timeout, or completion work after mail processing
- **THEN** the generated notification prompt guidance or equivalent agent binding material tells the agent to run the appropriate on-tick skill after processing mail
- **AND THEN** the tick performs one bounded pass and stops

#### Scenario: In-chat waiting is forbidden
- **WHEN** generated role behavior reaches the end of its current mail event and requested tick work
- **THEN** the role behavior tells the agent to finish the chat turn
- **AND THEN** it does not ask the agent to wait in-chat for future mail, future ticks, or periodic wakeups

### Requirement: V5 defaults workspace and run artifacts to auditable generated contracts
When a generated loop needs agent workspaces, the packaged skill SHALL guide the execplan to generate workspace contracts that can be consumed by `houmao-utils-workspace-mgr` or equivalent maintained workspace surfaces.

The default workspace contract SHALL identify launch cwd, per-agent work roots, per-agent note or knowledge paths, writable temporary artifact paths, shared resources, and read/write rules when those facts apply.

When a generated loop executes with durable artifacts, the packaged skill SHALL guide the runtime layout to preserve run-local payloads, rendered outputs, send or reply responses, record files, state files, logs, and evidence under a run directory such as `<loop-dir>/runs/<run-id>/` or an explicitly generated equivalent.

#### Scenario: Workspace defaults become manager input
- **WHEN** generated execution prepares workspaces for participants
- **THEN** the execplan provides workspace facts suitable for maintained workspace planning and verification
- **AND THEN** generated skills do not perform ad hoc workspace creation when a maintained workspace surface applies

#### Scenario: Run directory supports audit and recovery
- **WHEN** a generated loop records structured payloads, rendered messages, replies, records, state, or evidence during execution
- **THEN** those artifacts are preserved under the generated run artifact layout
- **AND THEN** status, validation, recovery, and human review can refer to those artifacts without depending only on live mailbox state

### Requirement: V5 exposes staged execplan generation subcommands
The packaged v5 skill SHALL expose these staged execplan generation subcommands:

- `execplan-specs-process`;
- `execplan-specs-contract`;
- `execplan-harness`;
- `execplan-skills`;
- `execplan-agent-bindings`;
- `execplan-finalize`.

The staged subcommands SHALL be authoring operations under the selected `<loop-dir>` and SHALL NOT perform Houmao platform launch, mailbox delivery, gateway, memory, lifecycle, or workspace creation side effects.

Each staged subcommand SHALL state its inputs, outputs, prerequisites, downstream invalidation effects, and boundaries.

#### Scenario: User asks for one staged generation step
- **WHEN** a user explicitly asks v5 to run `execplan-harness` for a selected loop directory
- **THEN** the skill routes to the staged harness-generation guidance
- **AND THEN** the staged operation works only on generated execplan material and does not start or mutate live agents

#### Scenario: Staged commands are discoverable
- **WHEN** a user asks which execplan generation stages are available
- **THEN** the skill lists the six staged subcommands in dependency order
- **AND THEN** it explains that `execplan-fast-forward` runs them as the non-interactive all-stage orchestration path

### Requirement: V5 generates execplan stages in process-first order
The staged execplan generation order SHALL be:

1. `execplan-specs-process`;
2. `execplan-specs-contract`;
3. `execplan-harness`;
4. `execplan-skills`;
5. `execplan-agent-bindings`;
6. `execplan-finalize`.

The `execplan-specs-process` stage SHALL generate or update the canonical loop process model before other execplan stages.

The canonical generated process model SHALL live at `<loop-dir>/execplan/specs/collab/collab-overview.md`.

The packaged skill SHALL NOT guide generated v5 execplans to use `<loop-dir>/execplan/specs/process.md` as the primary process model.

The process model SHALL describe the loop in generic process terms, including phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, or record families when those concepts apply.

The process model SHALL include a Python-style pseudocode view in fenced `python` code blocks, with inline comments that explain important conditions, actions, state effects, and stopping points.

The process model SHALL include a high-level Mermaid sequence graph in a fenced `mermaid` code block showing the main participant, event, handoff, and tick flow.

Downstream stages SHALL derive their generated artifacts from the process model and intention source rather than inventing independent process semantics.

Each staged artifact-generation page SHALL make its expected directory shape explicit for artifacts it emits. Optional layers MAY be omitted only when the omission or accepted equivalent is recorded in the manifest, generated docs, or validation notes.

Generated skill artifacts SHALL use a flat directory shape under `execplan/skills/<unique-skill-name>/SKILL.md`.

Generated skill names SHALL be unique across the execplan package and suitable for installation into one flat skill namespace. The packaged skill SHALL NOT rely on nested category directories such as `shared/`, `on-event/`, `on-tick/`, or `operator/` to disambiguate generated skills.

Generated concrete agent bindings SHALL include a plan-local binding registry at `execplan/agents/bindings.toml` and place profile material under `execplan/agents/profiles/<agent-id>/`.

Generated harnesses SHALL include an explicit command registry at `execplan/harness/commands.toml` unless the manifest records an accepted no-code or external harness surface.

#### Scenario: Process model precedes derived contracts
- **WHEN** `execplan-fast-forward` creates a fresh generated execplan
- **THEN** it treats `execplan-specs-process` as the first generation stage
- **AND THEN** it writes the canonical process overview to `execplan/specs/collab/collab-overview.md`
- **AND THEN** objective, participant, topology, communication, state, workspace, harness, skill, agent-binding, docs, and final manifest artifacts are derived after the process model exists

#### Scenario: Flat process path is rejected
- **WHEN** validation finds `execplan/specs/process.md` being used as the generated process overview
- **THEN** validation reports it as a misplaced generated artifact
- **AND THEN** the plan is not treated as conforming until the process overview is moved to `execplan/specs/collab/collab-overview.md`

#### Scenario: Process-first order applies without a fixed topology
- **WHEN** the intention source describes a custom loop topology
- **THEN** the process stage captures that topology in generic process terms
- **AND THEN** later stages derive contracts and generated role behavior from that process model without forcing a built-in participant shape

#### Scenario: Process model includes readable algorithm views
- **WHEN** `execplan-specs-process` emits process docs
- **THEN** those docs include Python-style pseudocode with inline comments for how the loop advances
- **AND THEN** those docs include a high-level Mermaid sequence graph for the participant/event/handoff flow

#### Scenario: Later stages use explicit package paths
- **WHEN** staged generation emits contracts, harness surfaces, generated skills, agent bindings, or final docs
- **THEN** each emitted artifact is placed under the canonical path family for that stage
- **AND THEN** any omitted default layer or accepted equivalent is recorded for validation and operator review

### Requirement: All-stage generation and update orchestration use staged execplan order
The `execplan-fast-forward` operation SHALL scaffold `execplan/` and orchestrate the staged execplan subcommands in dependency order without optional generation questions unless the user explicitly asks for one staged subcommand.

The `execplan-step-by-step` operation SHALL scaffold `execplan/`, then orchestrate the same staged execplan subcommands in dependency order while asking at most one unresolved generation-decision question at a time.

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
