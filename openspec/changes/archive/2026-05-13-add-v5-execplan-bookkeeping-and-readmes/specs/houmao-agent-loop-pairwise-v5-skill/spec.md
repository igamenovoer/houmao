## ADDED Requirements

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
