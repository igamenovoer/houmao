# houmao-agent-loop-pairwise-v5-skill Specification

## Purpose
TBD - created by archiving change add-general-pairwise-v5-loop-skill. Update Purpose after archive.
## Requirements
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

### Requirement: V5 skill guidance is split into authoring and execution subskills
The top-level `houmao-agent-loop-pairwise-v5` skill SHALL act as an index and router for v5 subskills rather than carrying the whole workflow in one instruction file.

The packaged v5 skill SHALL include authoring subskills for creating intention material, refining intention material, generating execplans, validating execplans, and updating generated execplans.

The packaged v5 skill SHALL include execution subskills for preparing agents, preparing workspaces or accepting equivalent manual workspace readiness evidence, validating loop readiness, launching agents, starting a loop, checking status, pausing, resuming, recovering, and stopping.

Each subskill SHALL define its trigger, inputs, outputs, and boundaries.

#### Scenario: Top-level skill routes authoring work
- **WHEN** a user asks v5 to create, refine, generate, validate, or update generated loop material
- **THEN** the top-level skill routes to an authoring subskill
- **AND THEN** the authoring subskill handles the requested authoring operation within the selected `<loop-dir>`

#### Scenario: Top-level skill routes execution work
- **WHEN** a user asks v5 to prepare agents, prepare workspaces, validate loop readiness, launch agents, start, inspect status, pause, resume, recover, or stop a loop
- **THEN** the top-level skill routes to an execution subskill
- **AND THEN** the execution subskill works from the generated `<loop-dir>/execplan/` and maintained Houmao operation surfaces

### Requirement: V5 execution uses generated execplan material and maintained Houmao operation surfaces
The v5 execution workflow SHALL operate from the generated `<loop-dir>/execplan/` package.

When execution needs platform operations such as managed-agent launch, prompt delivery, mailbox work, gateway work, memory work, lifecycle control, or inspection, the v5 execution subskills SHALL route through maintained Houmao operation skills or CLI surfaces rather than duplicating those contracts locally.

When execution needs loop-local state or generated role behavior, the v5 execution subskills SHALL use the generated execplan contracts, generated skills, generated agent bindings, generated docs, or generated harness surfaces.

Agent preparation SHALL create or update the concrete launchable agent/profile posture required by generated agent bindings.

Agent launch SHALL be owned by `launch-agents`, which uses maintained Houmao launch surfaces and does not send loop-start work.

Loop begin SHALL be owned by `start`, which uses generated start contracts and maintained communication surfaces to deliver the first loop trigger after required agents are live.

#### Scenario: Agent preparation composes existing Houmao surfaces
- **WHEN** a v5 execution subskill prepares agents for a generated execplan
- **THEN** it uses maintained Houmao specialist, mailbox, gateway, memory, or project-skill surfaces as appropriate
- **AND THEN** it does not hand-edit Houmao runtime internals or launch agents as the normal preparation path

#### Scenario: Launch composes existing Houmao surfaces
- **WHEN** a v5 execution subskill launches prepared agents for a generated execplan
- **THEN** it uses maintained Houmao instance or supported easy-instance launch surfaces
- **AND THEN** it does not duplicate managed-agent launch mechanics locally

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

### Requirement: V5 generated harnesses use Houmao-installed Python dependencies with import-failure guidance
The packaged v5 skill SHALL teach generated harnesses to use `click`, `jinja2`, and `jsonschema` as normal Python dependencies when generated harness features need modular command routing, Markdown template rendering, or JSON Schema validation.

The Houmao project SHALL declare `jinja2` and `jsonschema` as runtime dependencies so the uv-installed Houmao environment provides them. The existing `click` runtime dependency SHALL continue to satisfy modular CLI command-routing support.

Generated harnesses SHALL import only the non-stdlib libraries required by the features they implement.

When a generated harness entrypoint cannot import a required non-stdlib dependency, it SHALL fail with actionable guidance that names the missing dependency and tells the caller to either install the dependency into the Python environment used to run the harness or run the harness with the Python environment associated with the installed Houmao uv tool.

Generated harness import-failure guidance SHALL avoid hardcoding a uv tool environment path. It SHALL suggest inspection or refresh commands such as `uv tool list --show-paths --show-python` or reinstalling/updating the Houmao uv tool environment when appropriate.

The v5 harness authoring guidance SHALL tell agents to test generated harnesses after writing them. If a harness test fails because required harness libraries are missing, the active interpreter appears different from the intended runtime, or dependency posture is ambiguous, the agent SHALL retry the same harness test through the Houmao uv-installed environment before treating the failure as a harness implementation bug.

Generated harnesses MAY provide `execplan/harness/requirements.txt` and optional local `pip --target execplan/harness/vendor` instructions for standalone/custom execution, but the packaged v5 skill SHALL NOT require or ship a bundled wheelhouse for these dependencies.

The packaged v5 skill SHALL NOT include source-bundled `.whl` files for `click`, `jinja2`, `jsonschema`, or their transitive dependencies.

Validation guidance SHALL report generated v5 execplans as stale or non-conforming when they claim a skill-bundled wheelhouse fallback for these harness libraries.

#### Scenario: Houmao install provides common harness libraries
- **WHEN** Houmao is installed as a uv-managed tool from the project package
- **THEN** the installed environment includes `click`, `jinja2`, and `jsonschema`
- **AND THEN** generated harnesses can instruct users to use that Houmao environment when another Python interpreter lacks those libraries

#### Scenario: Harness import failure gives actionable recovery paths
- **WHEN** a generated harness imports a required non-stdlib library and that import fails
- **THEN** the harness reports the missing library by name
- **AND THEN** the message tells the caller to install the library into the active harness Python environment or use the Python environment associated with the installed Houmao uv tool

#### Scenario: Harness author retries failed tests through Houmao uv environment
- **WHEN** an agent tests a generated harness and the test fails because a required harness library is missing or the active interpreter appears to be the wrong runtime
- **THEN** the v5 skill guidance tells the agent to retry the same test through the Houmao uv-installed environment
- **AND THEN** the agent does not rewrite harness logic until distinguishing dependency environment failure from implementation failure

#### Scenario: Harness dependencies are feature-scoped
- **WHEN** a generated harness does not render `.md.j2` templates
- **THEN** it does not need to declare or import `jinja2`
- **AND WHEN** a generated harness does not validate JSON Schema payloads
- **THEN** it does not need to declare or import `jsonschema`

#### Scenario: Skill does not ship wheelhouse fallback
- **WHEN** the packaged v5 skill assets are inspected
- **THEN** they do not contain a bundled harness wheelhouse of `.whl` files for `click`, `jinja2`, `jsonschema`, or transitive dependencies
- **AND THEN** v5 harness guidance does not claim a skill-bundled wheelhouse fallback exists

#### Scenario: Optional standalone local target remains possible
- **WHEN** a generated loop intentionally supports running its harness outside the Houmao-installed environment
- **THEN** it may include `execplan/harness/requirements.txt` and a local `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt` instruction
- **AND THEN** this local target path is documented as caller-managed standalone support, not as a skill-bundled offline fallback

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

### Requirement: V5 generated artifact directories include concise README files
The packaged v5 skill SHALL guide generated execplans to include a `README.md` in every emitted generated artifact directory.

Generated artifact directory README files SHALL contain only a concise description of the directory purpose and its contents.

Generated artifact directory README files SHALL use this minimal section shape:

- `Purpose`;
- `Contents`.

The `Purpose` section SHALL explain why the directory exists.

The `Contents` section SHALL list the generated files or child directories in that directory and briefly state what each one is.

Generated README files SHALL NOT duplicate contract details from specs, schemas, command registries, skill bodies, agent bindings, or manifests.

Generated README files SHALL NOT be treated as source authority. They are human and agent orientation aids only.

Each v5 artifact-generation stage SHALL create or update README files for the generated artifact directories it creates or materially populates.

The `execplan-finalize` stage SHALL fill missing README files for emitted generated artifact directories and verify that the README files use the simple purpose-and-contents shape.

Validation guidance SHALL report missing generated artifact directory README files, except when the directory is intentionally omitted or the generated directory is a simple generated skill directory whose `SKILL.md` already orients the skill and no additional generated files exist.

#### Scenario: Generated specs directory has orientation README
- **WHEN** a generated execplan emits `execplan/specs/comms/`
- **THEN** it includes `execplan/specs/comms/README.md`
- **AND THEN** that README states the directory purpose and lists contents such as `templates.toml`, `schemas/`, and `renderers/`

#### Scenario: README stays non-authoritative
- **WHEN** a generated artifact directory README describes files under that directory
- **THEN** it does not duplicate schema fields, command semantics, role procedures, or binding contracts
- **AND THEN** authoritative details remain in generated specs, schemas, harness registries, generated skills, agent bindings, manifests, or other generated contract files

#### Scenario: Finalization fills README gaps
- **WHEN** `execplan-finalize` runs after earlier generation stages
- **THEN** it checks emitted generated artifact directories for README files
- **AND THEN** it creates or updates missing README files with only `Purpose` and `Contents`

#### Scenario: Simple generated skill directory can rely on SKILL.md
- **WHEN** a generated skill directory contains only `SKILL.md` and optional `agents/openai.yaml`
- **THEN** validation may accept the absence of that skill directory's `README.md`
- **AND THEN** `execplan/skills/README.md` still describes the generated skill directory collection

### Requirement: V5 generated bookkeeping state defaults to sqlite when SQL schemas are clear
The packaged v5 skill SHALL guide generated execplans to use sqlite as the default bookkeeping state backend when the loop state has a clearly defined SQL schema.

Generated sqlite-backed state SHALL include an explicit SQL schema artifact in the loop definition, such as under `execplan/specs/state/`.

Generated harness code SHALL treat the SQL schema artifact as the authoritative state contract for sqlite-backed bookkeeping.

Generated execplans MAY use JSONL plus explicit schemas as an alternate bookkeeping representation when state records are append-only, intentionally denormalized, schema-light, or too small to justify sqlite.

Generated execplans SHALL NOT use unstructured ad hoc state files for loop bookkeeping when either sqlite or JSONL plus schema is feasible.

Generated artifact directory README files MAY list state schema files, database files, or JSONL record files, but SHALL NOT duplicate SQL table definitions or JSON schema fields.

#### Scenario: Clear relational bookkeeping uses sqlite
- **WHEN** an execplan defines stable bookkeeping entities such as agents, pairwise edges, rounds, mail events, decisions, assignments, artifacts, or run status
- **THEN** the generated harness defaults to sqlite for that state
- **AND THEN** the execplan includes an explicit SQL schema artifact for the generated sqlite database

#### Scenario: Append-only bookkeeping can use JSONL plus schema
- **WHEN** generated bookkeeping is intentionally append-only or schema-light
- **THEN** the execplan may choose JSONL records instead of sqlite
- **AND THEN** each JSONL record type has an explicit schema artifact

### Requirement: V5 generated bookkeeping follows control-plane state principles
The packaged v5 skill SHALL teach skill-invoked agents that generated bookkeeping is runtime control-plane state for goal-oriented loops.

Generated bookkeeping state SHALL store compact facts and references needed for scheduling, ownership, validation, recovery, transition audit, and completion checks.

Generated bookkeeping state SHALL NOT duplicate full mail bodies, rendered Markdown, rich request/reply prose, long rationale, pseudocode, detailed analysis, or documentation content.

Generated bookkeeping state SHALL reference mail, artifacts, docs, commits, evidence files, or external results by durable IDs or paths when those sources hold the detailed content.

Generated bookkeeping guidance SHALL state that mail remains the communication authority and generated state remains the transition/scheduling authority.

Generated bookkeeping guidance SHALL require every important transition to be reconstructable from structured records that identify the changed entity, new state or decision, actor or source, related mail/evidence/artifact refs, and timestamp.

Generated bookkeeping guidance SHALL require active ownership to be explicit enough for recovery and scheduling queries.

Generated bookkeeping guidance SHALL require generated state to define a finite valid state space through allowed states, statuses, transitions, and invariants.

Generated bookkeeping guidance SHALL require operator override, pause, prune, stop, repair, and recovery authority to be recorded as explicit operator intent events when such controls exist.

#### Scenario: State stores facts and refs, not mail prose
- **WHEN** a generated loop records a handoff from one participant to another
- **THEN** state stores compact routing, status, ownership, related work item, and mail reference facts
- **AND THEN** the detailed request body remains in the persisted mail record

#### Scenario: Scheduling can be derived from state
- **WHEN** an agent or operator asks what work can run next
- **THEN** the generated harness can derive busy participants, idle participants, active handoffs, assignable work items, blockers, and completion posture from bookkeeping state

### Requirement: V5 generated state contracts define schema, invariants, and boundaries
The packaged v5 skill SHALL guide generated execplans with runtime bookkeeping to emit a state contract package under `execplan/specs/state/`.

Generated `execplan/specs/state/` packages SHALL include a concise `README.md` and a `state-overview.md`.

Generated `state-overview.md` files SHALL describe state authority, state boundaries, minimal entity families, allowed transitions, invariants, scheduling queries, and content that state must not store.

Sqlite-backed generated state SHALL include `schema.sql` under `execplan/specs/state/`.

Sqlite-backed generated state SHOULD include seed data and invariant declarations when the loop needs deterministic initialization or validation beyond schema shape.

JSONL-backed generated state SHALL include explicit record schemas for each generated JSONL record type.

Generated state contracts SHOULD consider these generic entity families and include the subset needed by the loop:

- `process_state`;
- `participants`;
- `work_items`;
- `handoffs`;
- `mail_payloads`;
- `attempts`;
- `decisions`;
- `evidence`;
- `artifacts`;
- `operator_intent_events`;
- `events`.

Generated state contracts SHALL treat SQL schema files or JSON schemas as field-level authority.

Generated README files and overview prose SHALL NOT duplicate table definitions or record schema fields.

#### Scenario: Sqlite state contract package is generated
- **WHEN** a generated loop uses sqlite bookkeeping
- **THEN** it emits `execplan/specs/state/README.md`, `state-overview.md`, and `schema.sql`
- **AND THEN** it emits seed or invariant artifacts when initialization or validation needs them

#### Scenario: JSONL state contract package is generated
- **WHEN** a generated loop uses JSONL bookkeeping
- **THEN** it emits `execplan/specs/state/README.md`, `state-overview.md`, and explicit record schemas
- **AND THEN** the harness validates each JSONL record against the corresponding schema before treating it as loop state

### Requirement: V5 generated harness integrates state through validated commands
The packaged v5 skill SHALL guide generated harnesses to be the normal access path for participant state mutation and query.

Generated harness guidance SHALL tell participant agents to avoid raw SQL or ad hoc state-file edits during normal loop execution.

Generated harnesses for stateful loops SHALL provide commands or command groups for state initialization, state validation, read-only state query, record validation, and record application.

Generated harness state initialization SHALL create runtime state from generated state contracts and seed data.

Generated harness state validation SHALL check schema availability, referential integrity, allowed states, transition invariants, active ownership invariants, mail/artifact references, and policy-derived gates when those concepts exist in the loop.

Generated harness read-only queries SHALL expose loop-summary and scheduler-posture views sufficient for agents to decide next work without inspecting raw state.

Generated harness record application SHALL validate structured record payloads against generated schemas before mutating sqlite or appending JSONL records.

Generated harness guidance SHALL reserve direct state edits for operator repair, require the loop to be paused for such repair, and require harness validation after repair.

Generated harness code MAY access generated state contracts through direct relative paths from the harness directory or through relative symlinks into the harness directory.

#### Scenario: Agent applies state through harness
- **WHEN** a participant needs to record a decision, handoff, attempt, evidence fact, or completion transition
- **THEN** it uses the generated harness record validation/application path
- **AND THEN** the harness rejects schema-invalid or invariant-breaking records

#### Scenario: Operator repair bypass is constrained
- **WHEN** an operator directly edits runtime sqlite or JSONL state for repair
- **THEN** the loop is paused first
- **AND THEN** the operator runs generated harness validation before normal participant execution resumes

### Requirement: V5 generated TOML contracts expose descriptions through harness explain output
The packaged v5 skill SHALL guide generated TOML contract files to include explicit `description` fields for records or sections that are exposed to agents or operators through generated harness commands.

Generated TOML descriptions SHALL be concise human-readable explanations of what the record, section, or non-obvious field means.

Generated TOML descriptions SHALL be normal TOML data fields, not structured comments.

Generated TOML files SHALL include plain human-readable comments above each generated section header or table-array header.

Generated TOML section comments SHALL explain the purpose of the section for direct human readers.

Generated TOML section comments SHALL NOT be treated as structured authority.

Generated TOML files MAY include additional comments for human readability, but generated harness `--explain` behavior SHALL NOT depend on parsing TOML comments.

Generated harness commands that expose TOML-backed contracts SHALL provide a `--explain` option when structured descriptions are available.

Generated harness `--explain` output SHALL include TOML `description` values with stable source keys or paths that identify the contract entry being explained.

Generated harness `--explain` output for JSON-schema-backed contracts SHALL use JSON Schema `description` fields where available.

Generated validation guidance SHALL report missing `description` fields for generated TOML records or sections that are intended to be explainable through harness commands.

Generated validation guidance SHALL report missing human-readable comments above generated TOML sections when those sections are emitted by the execplan generator.

Generated validation guidance SHALL NOT require `description` fields for private mechanical TOML files that are not exposed to agents, operators, or harness explain output.

#### Scenario: TOML policy entry explains itself
- **WHEN** a generated TOML policy entry is exposed through a harness policy or objective command
- **THEN** the entry includes a `description` field
- **AND THEN** the generated harness `--explain` output prints that description with a stable source key

#### Scenario: Harness does not parse TOML comments for explain
- **WHEN** a generated TOML contract contains comments
- **THEN** those comments may help human readers
- **AND THEN** the harness explanation source remains the structured `description` fields

#### Scenario: TOML section is readable in-place
- **WHEN** a generated TOML file emits a section such as `[state_backend]` or `[[policies]]`
- **THEN** a plain human-readable comment appears immediately above that section
- **AND THEN** the comment explains the section purpose without replacing structured `description` fields

### Requirement: V5 top-level skill entrypoint uses progressive-disclosure reference pages
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL keep its top-level `SKILL.md` focused on activation, required loop root, source/generated-output invariants, supported operations, routing, and global constraints.

The top-level `SKILL.md` SHALL NOT carry the full detailed generated-contract defaults, bookkeeping model, TOML conventions, mail runtime model, scaffold profile details, generation-stage dependency model, or maintained-platform boundary guidance when that guidance can live in routed runtime reference pages.

The packaged skill SHALL include runtime-readable reference pages under the skill package for shared detailed guidance used by multiple routed subskills.

Runtime reference pages SHALL be outside `dev/design/`, because they are part of normal skill execution rather than maintainer-only design intent.

Runtime reference pages SHALL be organized by durable operational concern rather than by one-off implementation history.

Routed subskills that depend on shared detailed guidance SHALL include an explicit `Read first` section that lists the runtime reference pages they must read before acting.

Routed subskills SHALL avoid duplicating the detailed guidance owned by runtime reference pages unless a local operation-specific exception is needed.

The split SHALL preserve existing operation names, generated-loop behavior, scaffold profile semantics, runtime mail model, and maintained Houmao platform-boundary rules.

#### Scenario: Entry point routes without loading detailed defaults
- **WHEN** an invoking agent opens the top-level `houmao-agent-loop-pairwise-v5/SKILL.md`
- **THEN** it can determine whether the skill applies, which `<loop-dir>` invariant applies, and which routed page to read
- **AND THEN** it does not need to read full generated-contract, bookkeeping, TOML, mail-runtime, or platform-boundary defaults from the entrypoint itself

#### Scenario: Operation page declares shared references
- **WHEN** a routed authoring or execution page requires shared detailed guidance
- **THEN** the page includes a `Read first` section naming the required runtime reference pages
- **AND THEN** those links resolve within the packaged skill directory

#### Scenario: Runtime references are not maintainer-only docs
- **WHEN** shared guidance is needed during normal skill execution
- **THEN** it lives in runtime reference pages under the skill package
- **AND THEN** it is not available only through `dev/design/`

#### Scenario: Split preserves current behavior
- **WHEN** the top-level entrypoint is shortened and detailed guidance is moved into reference pages
- **THEN** existing v5 operations remain routed by the same operation names
- **AND THEN** generated artifact structure, scaffold profile meanings, mail-driven runtime semantics, and maintained Houmao platform boundaries remain unchanged

### Requirement: V5 provides distinct intent and execplan clarification subcommands
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose canonical authoring operations named `clarify-intent` and `clarify-execplan`.

The `clarify-intent` operation SHALL focus on user-editable loop intention source.

The `clarify-execplan` operation SHALL focus on generated execplan implementation choices.

The top-level skill routing SHALL distinguish these two operations and route each one to its own authoring page.

The top-level skill MAY treat the natural phrase `clarify intent` as an unambiguous alias for `clarify-intent`, but canonical operation listings and routed pages SHALL use `clarify-intent`.

#### Scenario: Intent clarification routes to intent page
- **WHEN** a user asks v5 to run `clarify-intent`
- **THEN** the top-level skill routes to the intent clarification page
- **AND THEN** that page works from `<loop-dir>/intention/` as source authority

#### Scenario: Execplan clarification routes to execplan page
- **WHEN** a user asks v5 to run `clarify-execplan`
- **THEN** the top-level skill routes to the execplan clarification page
- **AND THEN** that page works from `<loop-dir>/execplan/` as generated implementation authority

### Requirement: V5 clarification uses a shared structured clarification protocol
The packaged v5 skill SHALL include a runtime-readable clarification protocol reference page under `subskills/reference/`.

Clarification operation pages SHALL read the shared clarification protocol before asking clarification questions.

Clarification operation pages SHALL read `runtime-mail-model.md` before clarifying any mail-driven loop behavior.

The shared clarification protocol SHALL require the invoking agent to read relevant source artifacts before asking questions.

The shared clarification protocol SHALL require an internal coverage scan before asking questions.

The shared clarification protocol SHALL require candidate questions to be prioritized by impact and uncertainty.

The shared clarification protocol SHALL allow at most five accepted clarification questions per session.

The shared clarification protocol SHALL require exactly one question at a time.

The shared clarification protocol SHALL require each question to be answerable by either a short multiple-choice selection or a constrained short answer.

The shared clarification protocol SHALL require a recommended or suggested answer with concise reasoning when the available context supports one.

The shared clarification protocol SHALL require accepted answers to be recorded immediately and reflected in the appropriate source artifacts.

The shared clarification protocol SHALL require validation after each accepted answer so obsolete contradictions are removed and the clarified ambiguity is not left unresolved.

The shared clarification protocol SHALL require a final coverage summary with clear, resolved, deferred, and outstanding categories.

#### Scenario: Clarification scans before asking
- **WHEN** a clarification operation starts
- **THEN** it reads the required source artifacts and reference pages
- **AND THEN** it builds an internal coverage map before asking the first question

#### Scenario: Clarification asks one high-impact question
- **WHEN** the internal scan finds multiple ambiguity candidates
- **THEN** the operation chooses the highest-impact unresolved candidate
- **AND THEN** it asks only one question before waiting for the user's answer

#### Scenario: Accepted answer is integrated immediately
- **WHEN** the user accepts, edits, or supplies a valid answer
- **THEN** the operation records the accepted answer
- **AND THEN** it updates the affected source artifacts before asking another question

### Requirement: V5 intent clarification scans loop intent coverage before questioning
The `clarify-intent` operation SHALL read current intention source, project context when present, and existing intent ADRs when present before asking questions.

The `clarify-intent` operation SHALL scan intent coverage categories for at least:

- objective, non-goals, and completion signals;
- participant roles, authorities, and handoff rights;
- collaboration topology and work-item lifecycle;
- mail/message families at intent level;
- on-event and on-tick responsibilities;
- state/bookkeeping needs;
- operator controls and recovery posture;
- workspace, artifact, and evidence expectations;
- project integration context;
- terminology and explicit omissions.

The `clarify-intent` operation SHALL prioritize questions that materially affect generated process, contracts, runtime safety, scheduling, recovery, validation, or acceptance.

The `clarify-intent` operation SHALL avoid asking low-impact local wording or formatting questions when higher-impact loop logic remains unclear.

Accepted `clarify-intent` answers SHALL be recorded under the loop's intent ADR area and reflected in `intention/` Markdown.

The `clarify-intent` operation SHALL NOT directly edit generated `execplan/` artifacts.

#### Scenario: Intent clarification finds core loop ambiguity
- **WHEN** intention source states participants but not completion authority
- **THEN** `clarify-intent` treats completion authority as a high-impact ambiguity
- **AND THEN** it asks a targeted question before asking local wording or file-organization questions

#### Scenario: Intent clarification updates intention source only
- **WHEN** the user accepts an intent clarification answer
- **THEN** the answer is recorded in an intent ADR
- **AND THEN** the relevant intention Markdown is updated
- **AND THEN** generated `execplan/` files are not directly edited by `clarify-intent`

### Requirement: V5 execplan clarification scans generated implementation coverage before questioning
The `clarify-execplan` operation SHALL require an existing generated `<loop-dir>/execplan/` package.

The `clarify-execplan` operation SHALL read relevant generated execplan artifacts before asking questions, including process specs, derived contracts, harness surfaces, generated skills, agent bindings, manifest, docs, and prior execplan ADRs when present.

The `clarify-execplan` operation SHALL scan generated implementation coverage categories for at least:

- process phases, events, handoffs, ticks, terminal posture, and recovery posture;
- mail schemas, renderers, reply links, ack/result/error families, and payload lifecycle;
- state schema, transitions, invariants, ownership, backend choice, and repair posture;
- harness commands for initialization, query, validation, record apply, rendering, and explain output;
- generated skill triggers, bounded procedures, stop points, and tick placement;
- agent bindings, notifier prompts, support skills, workspace policy, and memo posture;
- run artifacts, evidence refs, validation coverage, manifest coherence, and generated docs;
- platform boundary compliance and no in-chat waiting.

The `clarify-execplan` operation SHALL ask only about implementation decisions that are unclear, unjustified by intention or defaults, contradictory, or likely to affect runtime correctness.

Accepted `clarify-execplan` answers SHALL be recorded under `<loop-dir>/execplan/adrs/` and reflected in the affected generated execplan artifacts.

When an accepted answer affects an upstream generation stage, `clarify-execplan` SHALL update or flag all downstream affected artifacts according to the generation pipeline.

The `clarify-execplan` operation SHALL NOT rewrite editable intention source unless it discovers that the generated ambiguity comes from missing or contradictory intention source; in that case it SHALL report the issue and direct the user to `clarify-intent` or an intention edit.

#### Scenario: Execplan clarification finds missing reply handling
- **WHEN** generated mail contracts define a result request but no reply expectation, timeout, or reconciliation tick
- **THEN** `clarify-execplan` treats the missing handling as a high-impact implementation ambiguity
- **AND THEN** it asks a targeted question before asking about local file wording

#### Scenario: Execplan clarification records generated implementation decision
- **WHEN** the user accepts an execplan clarification answer
- **THEN** the answer is recorded under `<loop-dir>/execplan/adrs/`
- **AND THEN** the affected generated specs, harness, skills, agents, docs, manifest, or validation notes are updated or flagged according to the generation pipeline

#### Scenario: Execplan clarification detects intent source gap
- **WHEN** an implementation ambiguity cannot be resolved without changing the loop's intended behavior
- **THEN** `clarify-execplan` reports that the issue belongs in intention source
- **AND THEN** it does not silently invent intention policy inside generated artifacts

### Requirement: V5 exposes an independent prepare-workspace execution stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `prepare-workspace` as an execution subcommand for preparing or verifying multi-agent workspaces from generated execplan workspace contracts and prepared concrete agent/profile facts.

The `prepare-workspace` stage SHALL be separate from `prepare-agents`.

The skill SHALL document the normal ordered execution sequence as `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, then `start`.

The `prepare-agents` stage SHALL run before `prepare-workspace` when managed workspace setup needs concrete agent or launch-profile names.

The `prepare-agents` stage SHALL NOT call, route to, create, repair, execute `prepare-workspace`, or launch live agents as the normal preparation path.

The `prepare-workspace` stage SHALL NOT call, route to, or perform `prepare-agents`.

#### Scenario: Agent preparation precedes managed workspace preparation
- **WHEN** a generated loop requires managed workspaces with concrete agent or launch-profile names
- **THEN** the normal execution order prepares agent/profile identities before workspace setup
- **AND THEN** workspace preparation uses those prepared facts as workspace-manager inputs

#### Scenario: Workspace stage is routed independently
- **WHEN** a user asks the loop skill to run `prepare-workspace` for a selected loop directory
- **THEN** the skill routes to a dedicated workspace-preparation execution subskill
- **AND THEN** that subskill does not install generated agent skills, create specialists, launch agents, or perform other `prepare-agents` responsibilities

#### Scenario: Manual workspace setup can supply equivalent readiness evidence
- **WHEN** a generated loop requires workspace readiness and the user chooses not to run `prepare-workspace`
- **THEN** later readiness validation may accept explicit manual workspace facts that satisfy the generated workspace contract
- **AND THEN** the skill does not require the `prepare-workspace` command itself when equivalent evidence exists

#### Scenario: Preparation stages do not call each other
- **WHEN** a user asks the loop skill to run either `prepare-agents` or `prepare-workspace`
- **THEN** the selected stage performs only its own preparation responsibility
- **AND THEN** it does not call or route to the other preparation stage

### Requirement: V5 generated workspace contracts provide workspace-manager inputs
When a generated loop needs managed agent workspaces, the packaged skill SHALL guide execplan generation to emit workspace contracts that provide enough structured information for `houmao-utils-workspace-mgr` planning and execution.

Generated workspace contracts SHALL identify the workspace flavor, task name, workspace root or repo root policy, concrete agent workspace names, launch profile names, launch cwd policy, required per-agent work roots, required per-agent note or knowledge paths, shared resources, loop-requested bookkeeping directories, ignored transient paths, and memo-seed posture when those facts apply.

Generated agent bindings SHALL keep concrete participant-to-agent/profile mapping under the agent binding area and SHALL reference the applicable workspace policy instead of replacing the workspace contract.

#### Scenario: Workspace contract can drive workspace planning
- **WHEN** a generated execplan requires standard managed workspaces
- **THEN** `execplan/specs/workspace/workspace.toml` contains structured workspace-manager inputs for flavor, task name, agent workspace names, launch profile names, cwd policy, and bookkeeping directories
- **AND THEN** `execplan/agents/bindings.toml` maps participant instances to concrete agents and references the relevant workspace policy

#### Scenario: Workspace facts are not hidden in agent bindings only
- **WHEN** generated agent bindings identify concrete agents and launch profiles
- **THEN** workspace requirements remain authoritative in the generated workspace contract
- **AND THEN** the bindings refer to that workspace policy rather than becoming the only source of workspace behavior

### Requirement: V5 prepare-workspace delegates supported workspace setup to the workspace manager
The `prepare-workspace` execution subskill SHALL route supported Houmao workspace planning and execution through `houmao-utils-workspace-mgr`.

The `prepare-workspace` execution subskill SHALL adapt generated workspace contracts, generated agent bindings, and prepared concrete agent/profile facts into workspace-manager inputs.

The `prepare-workspace` execution subskill SHALL default to workspace-manager `plan` mode unless the user explicitly requests execution or has approved a current workspace plan.

The `prepare-workspace` execution subskill SHALL NOT implement ad hoc worktree, branch, shared repo, `.gitignore`, memo-seed, launch-profile cwd, local-state symlink, or submodule materialization mechanics when `houmao-utils-workspace-mgr` can represent the requested layout.

#### Scenario: Prepare-workspace uses prepared agent facts
- **WHEN** workspace-manager inputs require concrete agent or launch-profile names
- **THEN** `prepare-workspace` reads the prepared agent/profile facts produced by `prepare-agents`
- **AND THEN** it does not invent placeholder agent names independently of agent preparation

#### Scenario: Prepare-workspace plans before side effects by default
- **WHEN** a user asks `prepare-workspace` without explicitly asking to execute an approved plan
- **THEN** the skill uses workspace-manager plan mode
- **AND THEN** it reports the planned workspace organization without creating worktrees or changing launch profiles

#### Scenario: Prepare-workspace executes through workspace manager
- **WHEN** a user asks `prepare-workspace` to execute a supported workspace layout from an approved generated execplan and prepared agent facts
- **THEN** the skill uses `houmao-utils-workspace-mgr` execution guidance for the selected workspace flavor
- **AND THEN** it does not create the workspace by duplicating workspace-manager mechanics inside the loop skill

### Requirement: V5 prepare-workspace verifies workspace postconditions
After workspace planning or execution, the `prepare-workspace` execution subskill SHALL report workspace readiness facts and blockers relative to the generated execplan and prepared concrete agent/profile facts.

For executed standard workspace layouts, the subskill SHALL verify expected workspace contract docs, per-agent worktree paths, per-agent knowledge paths, shared knowledge paths, loop-requested bookkeeping directories, ignored transient paths, launch cwd posture, memo-seed files, and uniqueness of mutable per-agent workspace targets when those facts apply.

The `prepare-workspace` report SHALL distinguish ready facts, planned-but-not-executed facts, missing facts, and inconsistencies.

Equivalent manual workspace evidence SHALL distinguish the same ready, missing, and inconsistent facts when the generated execplan requires workspace readiness but the user did not run `prepare-workspace`.

#### Scenario: Executed workspace is checked against prepared agents
- **WHEN** workspace-manager execution completes for a generated loop
- **THEN** `prepare-workspace` checks that the resulting workspace facts match the generated workspace contract, generated agent bindings, and prepared concrete agent/profile facts
- **AND THEN** it reports any missing worktrees, missing knowledge paths, missing bookkeeping directories, launch cwd mismatches, or conflicting mutable paths as blockers

#### Scenario: Plan-only run is not treated as ready execution
- **WHEN** `prepare-workspace` only produced a workspace-manager plan
- **THEN** the subskill reports the planned workspace facts as not yet executed
- **AND THEN** `validate-loop` treats workspace readiness as incomplete until the required facts exist or the execplan explicitly accepts plan-only/custom readiness

#### Scenario: Manual workspace facts are validated as evidence
- **WHEN** the user provides manual workspace readiness facts instead of a `prepare-workspace` report
- **THEN** `validate-loop` checks those facts against generated workspace contracts and prepared agent/profile facts
- **AND THEN** missing or inconsistent facts block `launch-agents`

### Requirement: V5 validation checks workspace stage separation
The `validate-execplan` guidance SHALL check that generated workspace contracts route supported workspace setup through `houmao-utils-workspace-mgr` or an explicit operator-owned custom workspace contract.

The `validate-execplan` guidance SHALL check that generated lifecycle docs or generated operator guidance represent `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, and `start` as separate ordered stages.

The `validate-execplan` guidance SHALL check that `prepare-agents` and `prepare-workspace` remain separate execution stages and do not call each other.

The `validate-execplan` guidance SHALL check that `launch-agents` and `start` remain separate execution stages, where `launch-agents` launches live agents and `start` sends the first loop trigger.

The `validate-execplan` guidance SHALL NOT require live agent/profile/workspace/mailbox/gateway readiness; those execution-readiness checks belong to `validate-loop` and `launch-agents`.

#### Scenario: Validation catches missing launch stage
- **WHEN** authoring validation finds generated lifecycle guidance that sends first loop work from a stage that also launches agents
- **THEN** validation reports the generated execution stages as non-conforming
- **AND THEN** the plan is not considered conforming until launch and start are represented as separate stages

#### Scenario: Validation catches reversed generated stage order
- **WHEN** authoring validation finds generated lifecycle guidance that puts managed workspace preparation before concrete agent/profile preparation
- **THEN** validation reports the generated execution order as non-conforming
- **AND THEN** the plan is not considered conforming until the generated order is `prepare-agents`, workspace readiness, `validate-loop`, `launch-agents`, then `start`

#### Scenario: Validation catches cross-stage coupling
- **WHEN** validation finds `prepare-agents` guidance that instructs the agent to create worktrees, run workspace-manager execution, launch live agents, or route to `prepare-workspace`
- **THEN** validation reports the execplan or skill guidance as non-conforming
- **AND THEN** the plan is not considered ready until workspace setup and live launch are represented by their independent stages

#### Scenario: Execution readiness is checked by validate-loop and launch-agents
- **WHEN** concrete agent/profile/workspace/mailbox/gateway readiness is missing
- **THEN** `validate-execplan` does not treat that local runtime state as an authoring-time package-shape failure
- **AND THEN** `validate-loop` or `launch-agents` reports the runtime readiness blocker before `start`

#### Scenario: Validation accepts no-workspace loops
- **WHEN** a generated execplan explicitly does not require managed agent workspaces
- **THEN** validation does not require workspace-manager inputs for that loop
- **AND THEN** validation still accepts `prepare-workspace` as a no-op or verification-only stage when the omission is recorded in the manifest, docs, or validation notes

### Requirement: V5 exposes validate-loop as the execution readiness gate
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `validate-loop` as an execution subcommand for checking whether a generated loop is ready to start.

`validate-loop` SHALL be distinct from `validate-execplan`.

`validate-loop` SHALL check concrete runtime preparation state, including prepared agent/profile identities, generated and maintained skill binding posture, prepared workspace facts, launch cwd and memo posture, mailbox/gateway/notifier readiness for mail-driven loops, harness availability, run artifact readiness, state initialization readiness, and no in-chat waiting posture when those facts apply.

`validate-loop` SHALL report blockers and warnings without mutating agent profiles, workspaces, mailboxes, gateways, harness state, or run artifacts as its normal behavior.

`start` SHALL require a current `validate-loop` pass or perform only a final lightweight readiness check before sending the first trigger.

#### Scenario: Validate-loop checks runtime readiness
- **WHEN** a user asks the loop skill to run `validate-loop` for a selected loop directory
- **THEN** the skill checks prepared agent/profile facts, workspace facts, mail/gateway/notifier posture, harness posture, and run artifact posture as applicable
- **AND THEN** it reports blockers without starting loop work

#### Scenario: Validate-loop is distinct from execplan validation
- **WHEN** generated execplan artifacts are structurally valid but concrete agents or workspaces are not prepared
- **THEN** `validate-execplan` can still pass
- **AND THEN** `validate-loop` reports runtime readiness blockers before `start`

#### Scenario: Start depends on loop readiness
- **WHEN** a user asks to start a generated loop
- **THEN** the start guidance requires a current `validate-loop` pass or repeats only essential final readiness checks
- **AND THEN** it does not silently repair missing agent, workspace, mailbox, gateway, harness, or run artifact preparation

### Requirement: V5 exposes launch-agents as the live launch stage
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL expose `launch-agents` as an execution subcommand for launching prepared loop participants before loop start.

The normal execution sequence SHALL be `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence when required, `validate-loop`, `launch-agents`, then `start`.

The `launch-agents` subcommand SHALL read generated agent bindings, prepared agent/profile facts, workspace readiness facts or accepted manual equivalents, launch cwd posture, memo posture, notifier prompt posture, and generated run contracts when those facts apply.

The `launch-agents` subcommand SHALL launch missing live agents only through maintained Houmao launch surfaces such as `houmao-agent-instance` or supported easy-instance launch workflows.

The `launch-agents` subcommand SHALL verify and report live-agent or session facts for every required participant after launch.

The `launch-agents` subcommand SHALL NOT create or repair profiles, install generated skills, prepare workspaces, repair mailbox/gateway posture, mutate harness state, send loop-start work, or deliver the first loop trigger as its normal behavior.

#### Scenario: Launch-agents launches prepared participants
- **WHEN** a user asks v5 to run `launch-agents` for a generated loop with prepared profiles and validated pre-launch readiness
- **THEN** the skill launches required missing agents through maintained Houmao launch surfaces
- **AND THEN** it reports the live-agent/session facts needed by `start`

#### Scenario: Launch-agents does not begin loop work
- **WHEN** `launch-agents` starts managed agents successfully
- **THEN** it does not send the generated first work prompt or mail trigger
- **AND THEN** the loop remains unstarted until the user runs `start`

#### Scenario: Launch-agents blocks missing preparation
- **WHEN** required prepared profile facts, workspace readiness facts, launch cwd posture, or notifier prompt posture are missing
- **THEN** `launch-agents` reports the missing preparation
- **AND THEN** it does not repair those facts or start partially prepared agents as the normal path

### Requirement: V5 start begins loop work only after agents are live
The packaged `houmao-agent-loop-pairwise-v5` `start` execution subcommand SHALL treat live agents as a precondition for delivering the first loop trigger.

The `start` subcommand SHALL require a current `launch-agents` report or equivalent live-agent/session facts before sending loop-start work.

The `start` subcommand SHALL perform only a final lightweight liveness and start-trigger readiness check before initializing start-time runtime state and delivering the first generated trigger.

The `start` subcommand SHALL NOT launch agents, create or repair profiles, install skills, prepare workspaces, or perform full readiness validation as its normal behavior.

#### Scenario: Start sends first trigger after launch
- **WHEN** `launch-agents` has launched all required participants and reported live-agent facts
- **THEN** `start` can perform a final lightweight check
- **AND THEN** it sends the generated first loop trigger through the generated start contract and maintained communication surfaces

#### Scenario: Start blocks without live agents
- **WHEN** a user asks `start` but required participants are not live and no equivalent live-agent facts are available
- **THEN** `start` reports that `launch-agents` is required
- **AND THEN** it does not launch agents or send loop-start work

### Requirement: V5 generated execplans provide a loop-local operator control skill
The packaged v5 skill SHALL guide generated execplans with lifecycle control needs to emit a generated skill named `<loop-slug>-operator-control`.

The generated operator control skill SHALL live directly under `<loop-dir>/execplan/skills/<loop-slug>-operator-control/`.

The generated operator control skill SHALL identify the concrete loop slug, loop directory, manifest path, harness path, agent binding path, and supported run lifecycle operations for that generated loop.

The generated operator control skill SHALL provide loop-local guidance for lifecycle operations such as status, start, pause, resume, stop, recover, mode switching, and manual stepping when those operations apply.

The generated operator control skill MAY use local subskill or reference pages for lifecycle procedures, but those files SHALL remain inside the `<loop-slug>-operator-control` skill directory rather than under category directories such as `execplan/skills/operator/`.

The generated operator control skill SHALL route platform mechanics through maintained Houmao skills or CLI surfaces instead of duplicating launch, messaging, mailbox, gateway, workspace, memory, or inspection contracts.

#### Scenario: Execplan emits operator control
- **WHEN** the packaged skill generates `execplan/skills/` for a loop that supports operator lifecycle control
- **THEN** the generated execplan includes `<loop-dir>/execplan/skills/<loop-slug>-operator-control/SKILL.md`
- **AND THEN** that skill identifies the concrete generated loop and its lifecycle control surfaces

#### Scenario: Operator control uses flat skill namespace
- **WHEN** the generated operator control skill needs supporting lifecycle pages
- **THEN** those pages live inside `<loop-dir>/execplan/skills/<loop-slug>-operator-control/`
- **AND THEN** the generated execplan does not create `execplan/skills/operator/` or other category directories

#### Scenario: Operator control routes maintained platform operations
- **WHEN** the generated operator control procedure needs to inspect agents, send prompts, read or send mail, change notifier posture, or stop managed agents
- **THEN** it directs the operator to the maintained Houmao support skill or supported CLI surface that owns that platform operation
- **AND THEN** it keeps loop-local decisions, state queries, and record application in generated execplan or harness surfaces

### Requirement: V5 generated control contracts separate run state from execution mode
The packaged v5 skill SHALL guide generated execplans with lifecycle control needs to define loop-local control state that distinguishes run lifecycle state from execution mode.

Generated control state SHALL model run lifecycle state with values such as `not_started`, `running`, `paused`, `recovering`, `stopped`, and `completed`, or an explicitly documented equivalent state set.

Generated control state SHALL model execution mode with at least `auto` and `manual`, unless the generated execplan explicitly records that one of those modes is not applicable.

Generated control state SHALL default the initial execution mode to `auto` unless intention source, an accepted clarification decision, or an explicit operator-control action selects a different initial mode.

Generated control state SHALL define `auto` mode as notifier-driven execution where mail notification prompts are the normal wakeup path for mail-driven participants.

Generated control state SHALL define `manual` mode as operator-directed execution where mail notifier wakeups for the generated loop are suspended or disabled and the operator prompts bounded participant work directly.

Generated control state SHALL NOT treat `manual` mode as equivalent to `paused`; pausing blocks normal participant progress, while manual mode changes the wakeup authority.

Generated state or record contracts SHALL record operator intent events for mode switches, pauses, resumes, stops, overrides, and recovery actions when those controls exist.

#### Scenario: Running loop switches to manual mode
- **WHEN** an operator switches a running mail-driven loop from `auto` mode to `manual` mode
- **THEN** generated control state records the run lifecycle state separately from execution mode
- **AND THEN** the run can remain `running` while its execution mode becomes `manual`

#### Scenario: Unspecified initial mode defaults to auto
- **WHEN** a generated controllable loop has no explicit initial execution mode in intention source, accepted clarification decisions, or operator-control state
- **THEN** generated control state treats the initial execution mode as `auto`
- **AND THEN** generated status or mode lookup reports that default rather than leaving the mode ambiguous

#### Scenario: Pause remains distinct from manual mode
- **WHEN** an operator pauses a loop that is currently in manual mode
- **THEN** generated control state records a paused lifecycle posture
- **AND THEN** it does not rely on `manual` mode alone to mean participant progress is blocked

#### Scenario: Operator intent is auditable
- **WHEN** the operator changes mode, pauses, resumes, stops, overrides, or starts recovery
- **THEN** the generated execplan records an operator intent event or equivalent structured record
- **AND THEN** status and recovery can report the operator action, source, timestamp, affected run, and related evidence refs

### Requirement: V5 generated harnesses expose control and mode lookup commands
The packaged v5 skill SHALL guide generated harnesses for controllable loops to expose loop-local control commands or equivalent command groups.

Generated harness control commands SHALL support read-only status and execution-mode lookup for generated skills and operators.

Generated harness control commands SHALL support controlled mode changes when the generated loop supports `auto` and `manual` mode.

Generated harness control commands SHALL expose participant-specific manual context when manual operation is supported.

Generated participant context output SHALL include enough structured information for generated skills to decide one bounded pass, including run identity, run state, execution mode, participant identity, relevant pending mail refs or active handoff refs, allowed actions, and whether the participant must stop after one pass.

Generated harness control commands SHALL record requested control changes in loop-local state or records but SHALL NOT directly own gateway notifier implementation, mailbox delivery, managed-agent prompting, or managed-agent lifecycle mechanics.

#### Scenario: Agent queries execution mode
- **WHEN** a generated participant skill begins tick work
- **THEN** it can query the generated harness for current run state, execution mode, and participant control context
- **AND THEN** it does not infer execution mode from static skill prose or intention Markdown

#### Scenario: Operator changes mode through generated control surface
- **WHEN** the generated operator control skill changes a loop from `auto` to `manual`
- **THEN** it uses the generated harness to record the requested mode change and resulting loop-local control state
- **AND THEN** it routes notifier posture changes through the maintained Houmao gateway surface

#### Scenario: Manual context is actionable
- **WHEN** an operator prompts a participant for one manual-mode step
- **THEN** the generated participant skill can obtain manual context from the harness
- **AND THEN** that context identifies the bounded actions the participant may take before ending the turn

### Requirement: V5 generated on-tick skills are execution-mode aware
The packaged v5 skill SHALL guide generated on-tick skills for controllable loops to query generated harness control context before deciding tick behavior.

Generated on-tick skills SHALL branch between `auto` mode and `manual` mode behavior when both modes are supported.

In `auto` mode, generated on-tick skills SHALL perform the bounded post-mail, scheduling, reconciliation, timeout, completion, or "what now" work defined by notifier-prompt-driven loop semantics.

In `manual` mode, generated on-tick skills SHALL perform one operator-prompted bounded pass that may include checking relevant mail, processing one relevant mail or bounded mail batch, querying current state, acting from current context when no mail is pending, applying generated records through the harness, sending downstream mail, replying upstream mail, or reporting no actionable work.

Generated on-tick skills SHALL finish the chat turn after their bounded pass in both modes.

Generated on-tick skills SHALL NOT sleep, poll, tail logs, wait in-chat for mail, or rely on a periodic external tick driver.

#### Scenario: Auto-mode tick remains notifier-driven
- **WHEN** a mail notifier prompt asks an agent to process mail and run a follow-up tick in `auto` mode
- **THEN** the generated on-tick skill queries control context and performs the bounded auto-mode tick behavior
- **AND THEN** the agent finishes the chat turn after the tick

#### Scenario: Manual-mode tick can work without notifier prompt context
- **WHEN** an operator prompts an agent to perform one manual-mode step
- **THEN** the generated on-tick skill queries manual context and checks the current mail or state posture needed for one bounded action
- **AND THEN** the agent sends any required downstream mail, upstream reply, state record, or no-action report before ending the turn

#### Scenario: Tick does not block future prompts
- **WHEN** a generated on-tick skill finds no actionable work in either execution mode
- **THEN** it reports the no-action posture
- **AND THEN** it does not keep the chat turn open waiting for future mail or status changes

### Requirement: V5 generated agent bindings and validation cover operator control mode semantics
The packaged v5 skill SHALL guide generated agent bindings for mail-driven controllable loops to document auto-mode notifier behavior and manual-mode operator-prompted behavior.

Generated notifier prompt material SHALL describe auto-mode behavior: the notifier wakes the agent for mail processing, the agent uses generated on-event skills for matching message families, and the agent runs any required follow-up tick before ending the turn.

Generated operator control material SHALL describe manual-mode behavior: notifier wakeups are suspended or disabled for the generated loop, and the operator prompts one bounded participant step at a time.

Generated validation guidance SHALL check that controllable generated execplans include the operator control skill, harness control/mode lookup surfaces, mode-aware on-tick guidance, mode-switch operator intent records, notifier posture boundaries, and no in-chat waiting posture.

Generated validation guidance SHALL report missing or inconsistent mode control as a generated execplan issue when the loop claims to support auto/manual operation.

#### Scenario: Agent binding documents both wakeup modes
- **WHEN** a generated mail-driven loop supports manual operation
- **THEN** generated agent binding or notifier prompt material documents auto-mode notifier-driven behavior
- **AND THEN** generated operator control material documents manual-mode operator-prompted behavior

#### Scenario: Validation catches missing mode lookup
- **WHEN** a generated execplan claims to support manual mode but the generated harness lacks a mode lookup or manual context surface
- **THEN** `validate-execplan` guidance reports the execplan as incomplete
- **AND THEN** it points to the harness and generated skill stages that must be regenerated or repaired

#### Scenario: Validation catches notifier/manual mismatch
- **WHEN** generated operator control says manual mode disables notifier wakeups but generated agent bindings still require notifier prompts for manual work
- **THEN** validation guidance reports the mismatch
- **AND THEN** the generated execplan must align manual operation around operator-prompted bounded turns

### Requirement: V5 pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe tree-loop behavior as the canonical local-close tree or forest topology when it explains generated loop topology to users.

The skill SHALL present `pairwise loop` as a legacy alias only where useful for compatibility with the package name or older user language.

The skill body SHALL not introduce extra "v5" branding outside the skill name or package identity.

#### Scenario: V5 remains explicitly invokable
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise-v5`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** the user-facing workflow describes tree-loop behavior instead of making pairwise loop the primary concept name

#### Scenario: V5 avoids extra version branding
- **WHEN** v5 guidance is revised for terminology
- **THEN** added prose avoids unnecessary `v5` wording in the skill body
- **AND THEN** the package name and explicit invocation handle remain unchanged

### Requirement: Pairwise loop system-input questions distinguish required and optional runtime inputs
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL use required/optional input labels when asking users for Houmao loop system-operation values.

Those labeled questions SHALL apply to loop directory selection, project context roots, generated artifact locations, workspace preparation targets, agent-definition preparation inputs, validation targets, launch targets, operator-control targets, mail-notifier posture, lifecycle mode, and other Houmao runtime mechanics.

The skill SHALL NOT mention version lineage outside the skill name while implementing this guidance.

The skill SHALL NOT impose required/optional labels on user-task intent questions about objectives, acceptance criteria, domain constraints, participant reasoning, or business semantics unless the specific question asks for Houmao runtime behavior.

#### Scenario: Init asks for loop directory as required input
- **WHEN** `houmao-agent-loop-pairwise-v5 init` needs the user to choose an output loop directory
- **THEN** the skill asks with a required section that names the loop directory
- **AND THEN** it includes an optional section for project root, project context hints, naming preferences, or states that no optional input is needed

#### Scenario: Execplan generation asks for system blockers with optional defaults
- **WHEN** execplan generation or validation lacks a Houmao system input needed to proceed
- **THEN** the skill asks with required inputs separated from optional modifiers
- **AND THEN** the optional section identifies defaults, skip behavior, or manual alternatives when they exist

#### Scenario: Intent clarification remains domain-focused
- **WHEN** `clarify-intent` asks about objective ambiguity, acceptance semantics, participant responsibilities, or task-specific loop behavior
- **THEN** the question is not required to use required/optional system-input labels
- **AND THEN** the clarification flow still uses required/optional labels if it asks for a Houmao runtime setting such as workspace sharing, mail-notifier mode, or lifecycle control behavior

### Requirement: Pairwise-v5 skill is retired in favor of pro
The system SHALL NOT package `houmao-agent-loop-pairwise-v5` as a current installable Houmao-owned system skill.

The current generated-execplan loop workflow SHALL live under `houmao-agent-loop-pro`.

#### Scenario: Pairwise-v5 name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise-v5` is not present as a current installable skill
- **AND THEN** generated-execplan loop workflow guidance points to `houmao-agent-loop-pro`
