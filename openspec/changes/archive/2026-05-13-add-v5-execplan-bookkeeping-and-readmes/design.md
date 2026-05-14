## Context

The skill already defines a generated execplan package with many artifact directories: `specs/`, `skills/`, `agents/`, `harness/`, `docs/`, optional `adrs/`, and nested purpose directories. The manifest indexes generated artifacts, but a human or agent browsing a directory still needs a local orientation point.

The desired README rule is intentionally small: each generated artifact directory gets a `README.md` containing only purpose and contents. These README files are not contract authority and should not duplicate generated specs, schemas, command registries, skill procedures, or agent bindings.

Generated loops also need a default bookkeeping model. In goal-oriented mail-driven loops, bookkeeping is the runtime control plane: it tells agents and operators what work exists, who owns it, what transitions happened, what evidence or mail justified those transitions, and what can happen next. It should not become another copy of the conversation.

Existing concrete loop plans show that sqlite works well when state tables and transitions are known up front. JSONL plus explicit schemas remains useful for append-only logs or simpler generated state, but it should not be the default when a normalized SQL schema is clear.

Those concrete plans also show the value of explainable generated contracts. Some TOML files carry structured comments that a harness can extract into `--explain` output. For the generic skill, comment extraction is too complex and fragile. Generated TOML contracts should instead use explicit `description` fields that normal TOML parsers preserve. Generated TOML should still include normal human-readable comments above sections for in-place readability.

## Goals / Non-Goals

**Goals:**

- Require short README files for generated artifact directories.
- Keep README content limited to purpose and contents.
- Teach each v5 generation stage to create or update README files for directories it owns.
- Extend scaffolds and validation so missing README files are caught consistently.
- Teach skill-invoked agents the generic bookkeeping principles for goal-oriented loops.
- Require generated state contracts to describe entities, allowed states, transitions, invariants, and state authority.
- Set sqlite as the default generated state/bookkeeping backend when SQL schemas are clearly defined.
- Preserve JSONL plus schema as an alternate generated state representation.
- Require harness integration for state initialization, validated record application, read-only query, and validation.
- Require generated TOML contract entries exposed by the harness to include `description` fields.
- Require harness `--explain` output to surface TOML `description` fields alongside schema explanations.
- Require generated TOML files to include human-readable comments above each generated section.

**Non-Goals:**

- Turn README files into authoritative contracts.
- Duplicate manifest entries, schemas, TOML contracts, harness command details, or generated skill bodies in README files.
- Require README files inside every trivial leaf directory when that directory is intentionally omitted.
- Change loop runtime behavior.
- Force sqlite for state that is naturally append-only, schema-light, or better represented as JSONL records.
- Store full mail bodies, detailed rationale, pseudocode, or rich narrative in bookkeeping state.
- Require every loop to use every generic table family; generated schemas should fit the loop.
- Require parsing structured TOML comments for explain output.
- Require `description` fields for purely mechanical private TOML files that are never surfaced by agents or harness commands.
- Treat section comments as structured authority or as the source for harness `--explain`.

## Decisions

### Use a minimal README template

Generated artifact directory README files should use this shape:

```markdown
# <Directory Name>

## Purpose

<One or two sentences explaining why this directory exists.>

## Contents

- `<file-or-dir>`: <what it is>
```

This keeps README files useful and cheap. The content should describe the directory, not restate the contracts inside it.

Alternative considered: include usage, authority, ownership, examples, and update policy sections. Rejected because the user wants a simple purpose-and-contents convention.

### Apply the rule to generated artifact directories

The rule applies to generated directories that exist in the execplan package or generated runtime artifact layouts, including top-level directories and nested generated artifact directories. If a directory is not emitted, no README is required for it.

Examples:

```text
execplan/README.md
execplan/specs/README.md
execplan/specs/comms/README.md
execplan/specs/comms/schemas/README.md
execplan/skills/README.md
execplan/agents/README.md
execplan/harness/README.md
execplan/docs/README.md
runs/README.md
```

Generated skill directories are a special case: if a skill directory contains only `SKILL.md` and optional `agents/openai.yaml`, `SKILL.md` can orient that specific skill. If the generated skill directory contains additional generated files, add a `README.md` for that directory too.

### Stage ownership

Each authoring stage should update README files for the directories it creates or materially populates:

- scaffold profiles create starter README files for known shell directories;
- process and contract stages update `specs/` and nested spec READMEs;
- harness stage updates `harness/` and nested harness READMEs;
- skills stage updates `skills/` and generated skill directory READMEs when needed;
- agent bindings stage updates `agents/` and nested agent READMEs;
- finalize stage fills missing README files and verifies consistency with emitted artifacts.

### Treat bookkeeping as control-plane state

Generated bookkeeping should answer control-plane questions:

- What is the run lifecycle state?
- What work items or objective branches exist?
- Which participant owns which active obligation?
- Which mail, record, evidence, or operator event caused a transition?
- Which decisions or scalar gates changed scheduling or completion?
- What can be scheduled next?
- Is the current state valid?

Generated bookkeeping should store compact facts:

- stable IDs and refs;
- statuses and allowed states;
- ownership and active handoffs;
- scalar gates, scores, pass/fail facts, rankings, approvals, and decisions;
- artifact paths, commit refs, command refs, and evidence refs;
- timestamps and compact transition audit.

Generated bookkeeping should not store:

- full mail bodies or rendered Markdown;
- rich request/reply prose;
- detailed reviewer or agent rationale;
- source-code analysis, pseudocode, or long summaries;
- duplicate docs or schema definitions.

Mail remains the communication authority. State records should link to mail by message ID, payload ID, thread ID, or other durable refs. Artifacts and docs remain the authority for rich evidence and narrative.

### Generate a state contract package

When a loop has runtime bookkeeping, generation should create `execplan/specs/state/` with the state contract artifacts that fit the chosen backend.

For sqlite-backed state:

```text
execplan/specs/state/
  README.md
  state-overview.md
  schema.sql
  seed.toml
  invariants.toml
```

For JSONL-backed state:

```text
execplan/specs/state/
  README.md
  state-overview.md
  records/
    <record-type>.schema.json
  invariants.toml
```

`state-overview.md` should explain state authority, boundaries, minimal entity families, allowed transitions, and what state must not store. `schema.sql` or JSON schemas are the field-level authority. `invariants.toml` names the validation rules the harness should check.

Common generated entity families include:

- `process_state`: run lifecycle, phase, revision, active/stopped status.
- `participants`: role instances when not fully static elsewhere.
- `work_items`: goal-directed units of work, branches, claims, tasks, or open ends.
- `handoffs`: mail-backed obligations, active ownership, expected replies, and routing refs.
- `mail_payloads`: structured source payload refs, validation/send status, mailbox message IDs.
- `attempts`: attempts to complete, improve, evaluate, or resolve a work item.
- `decisions`: normalized approvals, rejections, reviewer/operator judgments, or routing decisions.
- `evidence`: scalar facts and artifact refs used by gates.
- `artifacts`: produced files, commits, reports, patches, outputs, or external result refs.
- `operator_intent_events`: operator override, pause, prune, repair, stop, or recovery authority.
- `events`: compact audit records when a dedicated table would be unnecessary.

Generated schemas should include only the families the loop needs.

### Use TOML description fields for explainable contracts

Generated TOML files that define agent-facing or harness-facing contracts should include explicit `description` fields on explainable records. This includes policy sections, objective items, participant role entries, topology entries, template registry entries, state invariant entries, seed records, and other generated contract records that agents may need to inspect through the harness.

Generated TOML should also include plain human-readable comments above each generated section header or table-array header. These comments explain the purpose of the section for someone reading the file directly. They are not parsed by the harness and do not replace `description` fields.

Prefer this shape:

```toml
# Assignment policy records used by the scheduler and validator.
[[policies]]
id = "assignment_limit"
description = "Limits how many active work items one participant may own at a time."
value = 1
```

Nested or scalar fields may also use `description` when the field meaning is not obvious:

```toml
# Runtime state backend used by the generated harness.
[state_backend]
kind = "sqlite"
description = "Run-scoped sqlite database used as the live bookkeeping authority."
schema_path = "specs/state/schema.sql"
```

Avoid relying on structured TOML comments such as `## @doc` as the generated default. Comments should be plain prose for human readability; they should not be the harness explanation source.

Generated harness `--explain` output should read preserved `description` fields from TOML data and include them in the common JSON envelope for commands that expose contracts. JSON Schema `description` fields should continue to explain JSON schema-backed email and record payloads.

### Default generated state to sqlite when schemas are clear

Generated harness bookkeeping should default to sqlite when the execplan can define stable SQL tables for state such as participants, work items, handoffs, mail payloads, decisions, attempts, evidence, assignments, artifacts, run status, or audit records.

The generated package should include the SQL schema as an explicit artifact, for example under `execplan/specs/state/`, and the harness should treat that schema as the authoritative state contract. README files may list the schema file and database location, but should not restate table definitions.

JSONL plus schema is still supported as an alternate representation when the state is append-only, intentionally denormalized, or too small to justify sqlite. In that case, the generated execplan should include JSON schema files for each record type and make the choice explicit.

Default order:

1. Use sqlite when a clear SQL schema can be defined.
2. Use JSONL plus schema when records are append-only or sqlite would add unnecessary complexity.
3. Avoid unstructured ad hoc state files.

### Integrate state into the harness

The generated harness should be the normal state access path for agents.

Expected command groups:

- `state init`: create runtime state from generated contracts and seed data.
- `state validate`: check schema existence, referential integrity, allowed states, transition invariants, ownership invariants, and policy-derived gates.
- `state query`: expose read-only views such as summary, scheduler posture, active handoffs, work item state, evidence, decisions, and completion posture.
- `record validate`: validate a TOML or JSON record payload against the generated record schema.
- `record apply`: apply a schema-valid record to sqlite or JSONL while preserving transition rules.
- `state export`: optionally render compact human-readable views for recovery and operator inspection.

Participant agents should use generated harness commands for normal state mutation and query. They should not use raw SQL or ad hoc file edits. Direct state edits are operator repair actions only, performed while the loop is paused and followed by harness validation.

Harness commands should use the generated state contracts through relative paths inside the loop definition directory. If the harness needs local access to those contracts, it may use relative symlinks into the harness directory or direct relative paths when symlinks are unavailable.

Harness commands that expose generated contracts should support `--explain` when the command has structured explanation data. The default implementation should gather:

- TOML record or section `description` fields for TOML-backed contracts.
- JSON Schema `description` fields for JSON-schema-backed payloads.
- A stable path or key for each explanation entry so agents can map the text to the source contract.

The generated harness may require `--print-json` with `--explain` when the project uses a common JSON command envelope.

### Keep scheduling derivable

Generated bookkeeping should make scheduling and completion derivable from state. The harness should be able to answer:

- which participants are idle or busy;
- which work items are assignable;
- which active handoffs are awaiting replies;
- which items are blocked, completed, pruned, or waiting for evidence;
- whether completion conditions are satisfied;
- which operator override or recovery events affect scheduling.

## Risks / Trade-offs

- [README drift] -> Keep content limited to directory purpose and contents; validation should reject obvious contract duplication only when it conflicts with the simple rule.
- [Too many files] -> Require README files only for emitted generated artifact directories; omitted directories need no placeholder.
- [Stage overlap] -> Use stage ownership: the stage that creates or materially populates a directory owns its README update.
- [README treated as authority] -> Skill and validation guidance should state that README files are orientation only.
- [SQLite overuse] -> Keep JSONL plus schema available for append-only or schema-light state.
- [State contract drift] -> Treat SQL schema files or JSON schemas as authoritative, not README prose.
- [State overcaptures narrative] -> State guidance must clearly route rich prose to mail, docs, and artifacts.
- [Harness bypass] -> Participant-facing guidance should make raw state mutation non-normal and validation mandatory after repair.
- [Comment extraction complexity] -> Use explicit TOML `description` fields instead of structured comment parsing.
- [Description drift] -> Keep descriptions concise and explanatory; field-level authority remains TOML keys, SQL schemas, and JSON schemas.
- [Comment drift] -> Keep section comments short and non-authoritative; structured contracts remain authoritative.

## Migration Plan

1. Add scaffold README templates for known generated shell directories where practical.
2. Update authoring subskills so generated stages create or update purpose-and-contents README files for emitted artifact directories.
3. Update state-generation guidance with generic bookkeeping principles, expected state contract artifacts, and sqlite/JSONL backend rules.
4. Update generated TOML guidance so generated sections have human-readable comments and agent-facing or harness-facing contract records include `description` fields.
5. Update harness-generation guidance so generated harnesses initialize, validate, query, and apply state records from those contracts.
6. Update harness-generation guidance so `--explain` surfaces TOML `description` fields and JSON Schema descriptions.
7. Update validation to check README presence, simple README shape, generated state contract coherence, generated TOML section comments, and explainable TOML descriptions where required.
8. Update developer design docs and examples to show the README, bookkeeping, TOML-comment, TOML-description, state-backend, and harness-integration conventions.
9. Validate the skill package and run `git diff --check`.
