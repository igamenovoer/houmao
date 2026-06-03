# houmao-agent-loop-lite-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-lite. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged manual `houmao-agent-loop-lite` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-lite` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-lite` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The packaged `houmao-agent-loop-lite` skill SHALL be manual-invocation-only. It SHALL activate only when the user explicitly requests `houmao-agent-loop-lite` or an explicitly named lite loop operation.

The packaged skill SHALL describe itself as the lightweight Markdown/direct-SQL loop authoring and generated-loop execution path.

#### Scenario: User explicitly invokes lite
- **WHEN** a user explicitly asks to use `houmao-agent-loop-lite`
- **THEN** the packaged lite skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents a Markdown-first loop authoring and execution workflow

#### Scenario: Generic loop request does not auto-route to lite
- **WHEN** a user asks generically to plan or run an agent loop without naming `houmao-agent-loop-lite`
- **THEN** the lite skill does not claim the request by default
- **AND THEN** the user must explicitly select lite before lite-specific files or operations are created

### Requirement: Lite preserves the pro loop-directory spine while removing heavy layers
The `houmao-agent-loop-lite` skill SHALL preserve the split between editable intention material and generated operational material.

The skill SHALL keep `<loop-dir>/intention/` as editable source material.

The skill SHALL keep `<loop-dir>/execplan/` as generated operational material.

The skill SHALL keep `<loop-dir>/runs/` as the durable runtime artifact root.

Lite generated execplans SHALL use `execplan/specs/`, `execplan/skills/`, and `execplan/agents/` when those concern areas are required.

Lite generated execplans SHALL NOT generate `execplan/harness/` or `execplan/docs/`.

#### Scenario: Lite initializes a loop directory
- **WHEN** a user invokes lite initialization with a selected `<loop-dir>`
- **THEN** the skill creates editable intention material under `<loop-dir>/intention/`
- **AND THEN** it keeps generated operational material under `<loop-dir>/execplan/`
- **AND THEN** it does not create `execplan/harness/` or `execplan/docs/`

### Requirement: Lite defaults to the smallest complete generated package
The lite skill SHALL emit only files and directories needed by the selected loop.

The default lite generated package SHALL include required Markdown files for manifest, objective, organization, process, communication, generated skill index, agent binding index, and state usage.

The default lite generated package SHALL include required communication templates and a required SQLite schema.

Optional material such as workspace rules, run-artifact rules, seed SQL, query recipes, notifier prompts, concrete profile definitions, tick skills, and operator-control skills SHALL NOT appear unless the selected loop process needs them.

A missing optional lite file SHALL mean that concern is not part of the generated lite loop rather than an incomplete placeholder.

#### Scenario: Optional workspace material is absent by default
- **WHEN** a lite loop does not require explicit workspace rules
- **THEN** the generated lite package does not include a workspace contract file
- **AND THEN** lite validation does not fail solely because workspace material is absent

#### Scenario: Optional seed SQL is absent by default
- **WHEN** a lite loop can initialize runtime state from `schema.sql` alone
- **THEN** the generated lite package does not include `state/seed.sql`
- **AND THEN** agents are not instructed to run seed SQL for that loop

### Requirement: Lite communication templates are required and typed in the body
Every lite generated execplan SHALL include at least one communication template under `execplan/specs/templates/`.

Each lite communication template SHALL be plain Markdown.

Each lite communication template SHALL begin with a body-local prologue that includes `Loop-Template-Type` and `Loop-Template-Version`.

The prologue SHALL end at the first blank line.

The template body SHALL use literal `<placeholder ...>` placeholders when generated content must be filled.

Lite templates SHALL NOT use JSON Schema, Jinja2, conditionals, loops, filters, or expression language.

Lite templates SHALL NOT duplicate Houmao mail envelope fields such as sender, receiver, subject, message id, thread id, timestamps, reply refs, or system headers.

#### Scenario: Template declares its loop-local type
- **WHEN** a lite communication template is generated
- **THEN** the first body paragraph declares `Loop-Template-Type`
- **AND THEN** generated receiver skills can dispatch on that type after reading the Houmao mail body

#### Scenario: Template does not duplicate mail envelope data
- **WHEN** a lite communication template is generated for Houmao mail delivery
- **THEN** it does not contain placeholder fields for sender, receiver, subject, message id, thread id, or timestamp
- **AND THEN** generated skills read those facts from Houmao mailbox metadata instead

### Requirement: Lite generated skills are mandatory
A lite execplan SHALL include generated skills under `execplan/skills/`.

A lite execplan SHALL include a generated shared guidance skill that states common lite rules for read order, placeholder replacement, direct SQLite usage, Houmao envelope metadata, and bounded-turn behavior.

For every required `Loop-Template-Type`, the lite execplan SHALL include at least one generated receiver skill whose trigger names that exact template type.

Generated receiver skills SHALL direct agents to read Houmao mail metadata from the mailbox response and to read loop-local type metadata from the body prologue.

Generated sender skills, when emitted, SHALL require unresolved `<placeholder` tokens to be removed before sending mail.

#### Scenario: Receiver skill exists for template type
- **WHEN** a lite execplan includes a `task-request` communication template
- **THEN** `execplan/skills/` contains a generated receiver skill whose trigger names `Loop-Template-Type: task-request`
- **AND THEN** the generated skill describes the bounded action for that message type

#### Scenario: Unresolved placeholders block send guidance
- **WHEN** a generated lite sender skill prepares an outbound template body
- **THEN** the skill requires the agent to check that no `<placeholder` token remains
- **AND THEN** the skill does not send the message until required placeholders are filled or the action is aborted

### Requirement: Lite state is direct SQLite with a Markdown usage contract
Lite generated execplans SHALL use `execplan/specs/state/schema.sql` as the SQLite schema authority when durable runtime state is needed.

Lite generated execplans SHALL include `execplan/specs/state/README.md` describing how agents initialize, query, update, and validate the per-run SQLite database directly.

Lite runs SHALL store runtime SQLite databases under `runs/<run-id>/` unless the generated lite manifest records an explicit equivalent location.

Generated lite skills SHALL manipulate SQLite directly according to the state README and SHALL NOT route state access through a generated harness.

Lite state SHALL store compact facts and references rather than full mail bodies, rendered Markdown, long rationale, or detailed analysis.

#### Scenario: Run initializes SQLite directly
- **WHEN** a lite loop starts a new run
- **THEN** the run creates a SQLite database from `execplan/specs/state/schema.sql`
- **AND THEN** generated skills operate on that database directly according to `execplan/specs/state/README.md`

#### Scenario: State stores refs rather than full mail bodies
- **WHEN** a generated lite skill records a received mail event
- **THEN** it stores compact refs such as message ref, thread ref, participant id, work item id, status, and timestamp
- **AND THEN** it does not copy the full mail body into SQLite unless the generated loop explicitly defines a compact extraction field

### Requirement: Lite operations remain bounded and delegate platform mechanics
Lite generated skills SHALL model on-event and tick work as prompt-triggered bounded turns.

Lite generated skills SHALL NOT instruct agents to sleep, poll, tail logs, or wait in-chat for future work.

Lite generated skills SHALL route ordinary mailbox operations through maintained Houmao mailbox skills or supported CLI surfaces.

Lite generated skills SHALL route gateway, notifier, launch, messaging, inspection, workspace, and agent-definition operations through their owning maintained Houmao skills or supported CLI surfaces.

When explicit workspace setup is needed, lite guidance SHALL route standard Houmao workspace planning, creation, validation, and summaries through `houmao-utils-workspace-mgr`.

Lite guidance SHALL NOT describe workspace-manager `execute` as the standard workspace setup operation.

#### Scenario: Mail-driven lite event stops after one action
- **WHEN** a lite generated receiver skill handles one recognized template type
- **THEN** it performs one bounded role-owned action
- **AND THEN** it ends the turn after required mail, state, or artifact updates complete

#### Scenario: Lite does not duplicate maintained platform contracts
- **WHEN** a lite generated operator skill needs to enable notifier behavior for a participant
- **THEN** it routes that operation through `houmao-agent-gateway`
- **AND THEN** it does not restate the low-level gateway notifier contract inline

#### Scenario: Lite routes workspace readiness through workspace manager
- **WHEN** a lite generated process needs explicit standard workspace setup or readiness evidence
- **THEN** lite guidance routes planning, creation, validation, or summaries through `houmao-utils-workspace-mgr`
- **AND THEN** it does not use `execute` as the standard workspace-manager operation name

### Requirement: Lite exposes a small authoring and execution operation surface
The packaged lite skill SHALL support operations for initialization, intent clarification, generated-skill generation, validation, agent preparation, launch, start, status, pause, resume, stop, and recovery when those operations apply to the selected lite loop.

The lite validation operation SHALL validate required Markdown shape, required communication template type declarations, generated receiver-skill coverage for template types, absence of unresolved placeholders in generated templates where applicable, absence of forbidden harness/docs directories, and SQLite schema parseability.

Lite validation SHALL NOT require JSON schemas, TOML contracts, Jinja renderers, or generated harness command registries.

#### Scenario: Lite validation checks generated-skill coverage
- **WHEN** a lite execplan contains a communication template type without a generated receiver skill
- **THEN** lite validation reports the execplan as incomplete
- **AND THEN** it identifies the missing template-to-skill coverage

#### Scenario: Lite validation does not require pro harness files
- **WHEN** a lite execplan omits `execplan/harness/`
- **THEN** lite validation treats that omission as valid
- **AND THEN** it does not require harness command registries or harness scripts

### Requirement: Lite skill uses routed pro-shaped operation pages
The packaged `houmao-agent-loop-lite` skill SHALL use `SKILL.md` as an entrypoint and router rather than as the full operation manual.

The lite `SKILL.md` SHALL include activation rules, help text, required root vocabulary, operation names, routing guidance, and global constraints.

The lite package SHALL include operation-specific authoring pages under `subskills/authoring/`.

At minimum, the lite authoring pages SHALL cover:

- `init`
- `create-intention`
- `clarify-intent`
- `clarify-execplan`
- `execplan-fast-forward`
- `execplan-specs-process`
- `execplan-specs-contract`
- `execplan-skills`
- `execplan-agent-bindings`
- `execplan-finalize`
- `validate-execplan`
- `update-execplan`

The lite package SHALL include operation-specific execution pages under `subskills/execution/`.

At minimum, the lite execution pages SHALL cover:

- `prepare-agents`
- `prepare-workspace`
- `validate-loop`
- `launch-agents`
- `start`
- `status`
- `pause`
- `resume`
- `recover`
- `stop`

The lite package SHALL include shared reference pages under `subskills/reference/` for reusable Markdown contract defaults, Markdown template events, direct SQLite state, runtime mail model, platform boundaries, scaffold ownership, and required/optional system input question shape.

The lite package SHALL include scaffold support under `assets/scaffolds/` and `scripts/scaffold.py` for starter intention and Markdown/direct-SQL execplan shells.

Detailed workflow guidance SHALL live in routed pages or reference pages rather than in long sections inside `SKILL.md`.

#### Scenario: Installed lite skill exposes routed pages
- **WHEN** `houmao-agent-loop-lite` is installed into a supported skill home
- **THEN** the installed skill contains `SKILL.md`
- **AND THEN** it contains `subskills/authoring/init.md`
- **AND THEN** it contains `subskills/authoring/execplan-fast-forward.md`
- **AND THEN** it contains `subskills/execution/prepare-agents.md`
- **AND THEN** it contains `subskills/execution/validate-loop.md`
- **AND THEN** it contains `subskills/reference/direct-sqlite-state.md`

#### Scenario: Lite router points to one operation page
- **WHEN** an agent reads `houmao-agent-loop-lite/SKILL.md` for a concrete operation such as `prepare-agents`
- **THEN** the router tells the agent which `subskills/execution/prepare-agents.md` page to read
- **AND THEN** the detailed `prepare-agents` checklist is not duplicated as a long standalone section in `SKILL.md`

### Requirement: Lite generation pipeline mirrors pro without harness or schema-renderer stages
The lite generated execplan workflow SHALL remain stage-based like `houmao-agent-loop-pro`.

The lite `execplan-fast-forward` operation SHALL generate or refresh lite execplan artifacts in this dependency order:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-skills
          -> execplan-agent-bindings
              -> execplan-finalize
```

The lite workflow SHALL NOT include an `execplan-harness` stage.

The lite process and contract stages SHALL use Markdown files as generated authorities for objective, organization, process, communication, state, workspace, run, participant, and agent-binding concerns when those concerns apply.

The lite communication contract SHALL use typed Markdown templates under `execplan/specs/templates/` instead of JSON schemas or Jinja2 renderers.

The lite state contract SHALL use `execplan/specs/state/schema.sql` plus Markdown direct-use guidance for SQLite initialization, reads, writes, validation, and recovery when durable state is needed.

Lite generated skills SHALL operate against Markdown contracts, typed Markdown templates, and SQLite directly, and SHALL NOT require generated harness commands.

Lite validation SHALL verify the routed lite package shape and the generated Markdown/direct-SQL execplan shape without requiring pro-only JSON schemas, Jinja2 renderers, generated harness commands, or generated docs.

#### Scenario: Lite fast-forward skips harness generation
- **WHEN** a user runs lite `execplan-fast-forward` for a loop with valid intention material
- **THEN** the generated stages include process specs, contract specs, skills, agent bindings, and final metadata
- **AND THEN** the generated stages do not include `execplan-harness`
- **AND THEN** the execplan does not create `execplan/harness/`

#### Scenario: Lite skills use direct SQLite state
- **WHEN** a generated lite skill needs durable state for a run
- **THEN** it follows `execplan/specs/state/README.md` and `execplan/specs/state/schema.sql`
- **AND THEN** it reads or writes the run SQLite database directly
- **AND THEN** it does not call a generated harness command for state access

#### Scenario: Lite validation checks Markdown templates instead of schemas
- **WHEN** lite validation checks generated communication contracts
- **THEN** it verifies the required typed Markdown template prologue and generated receiver-skill coverage
- **AND THEN** it does not require JSON Schema files or Jinja2 renderer files

