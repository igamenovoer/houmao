# Generated Contract Defaults

## Purpose

Use this page when generating, validating, finalizing, or operating against generated `execplan/` contracts.

Use these defaults unless intention source or accepted clarification decisions choose an equivalent or narrower shape. Any equivalent or omission must be indexed or explained in `manifest.toml`, generated docs, or validation notes.

## Execplan Scaffold

- `manifest.toml` indexes generated artifacts, generated-source posture, and plan revision.
- Every emitted generated artifact directory has a concise `README.md` with only:
  - `Purpose`: why the directory exists;
  - `Contents`: files or child directories in that directory.
- `adrs/` records accepted execplan-generation decisions when `execplan-step-by-step` is used.
- `specs/collab/collab-overview.md` is the required process-first authority.
- `specs/` separates objective, collaboration, communication, state, workspace, run-artifact, and participant contracts when those concerns apply.
- `skills/` contains one flat directory of generated skills: `skills/<unique-skill-name>/SKILL.md`.
- Generated skill names must be unique after installation; encode purpose in the skill name or metadata, not in nested category directories.
- `agents/` binds concrete Houmao agents to participant instances, prompt sources, installed skills, notifier prompt text, and workspace policy.
- `harness/` exposes loop-local validation, dynamic lookup, rendering, query, and controlled record application through an explicit command registry.
- `docs/` explains generated contracts for humans but is not source authority; final docs live under named files, not loose unindexed notes.

## Participants

- Separate participant role templates, stable participant instances, and concrete agent bindings.
- Do not force a fixed participant topology or role count.
- Generate task-specific records only from intention source or clarification decisions.

## Bookkeeping State

Treat bookkeeping as runtime control-plane state, not working memory.

State stores compact facts:
- ids and refs;
- statuses and ownership;
- decisions and scalar gates;
- evidence links;
- transition audit;
- completion posture.

Mail, docs, and artifacts store rich material:
- prose;
- rationale;
- rendered Markdown;
- pseudocode;
- analysis;
- detailed evidence.

Important transitions must be reconstructable from:
- changed entity;
- source actor or event;
- new state or decision;
- mail, evidence, or artifact refs;
- timestamp.

Active ownership must be queryable enough for scheduling and recovery.

## State Contracts

When durable bookkeeping is needed, generate state contracts under `execplan/specs/state/`:

- `state-overview.md` for authority, boundaries, entity families, transitions, invariants, scheduling queries, and non-state content;
- `schema.sql` when sqlite is selected;
- `seed.toml` when deterministic initialization is needed;
- `invariants.toml` when validation needs named checks;
- JSON schemas for JSONL records when JSONL is selected.

Default state backend order:
- use sqlite when stable entities and transitions can be expressed as a clear SQL schema;
- use JSONL plus explicit schemas only for append-only, schema-light, or intentionally denormalized state;
- avoid unstructured ad hoc state files when sqlite or JSONL plus schema is feasible.

Consider generic families such as:
- plan metadata;
- process state;
- participants;
- work items;
- handoffs or exchanges;
- communication payload lifecycle;
- attempts;
- decisions;
- evidence;
- artifacts;
- operator intent events;
- generic events.

## Generated TOML

- Generated TOML sections have plain human-readable comments above each section or table-array header.
- Agent-facing or harness-facing TOML records include concise `description` fields.
- `description` fields, not comments, are the source for harness `--explain`.
- Private mechanical TOML files that are never exposed through harness commands do not need record-level descriptions.

## Skill And Harness Defaults

- Generated on-event skills handle one concrete incoming event or message family, perform one bounded role-owned action, then stop.
- Generated on-tick skills handle scheduling, reconciliation, timeout, completion, or "what now" decisions by doing at most one pass, then stop.
- Generated skills query specs, state, or harness output for dynamic policy and runtime facts instead of copying constants into static prose.
- Generated harnesses may use `click` for modular commands, `jinja2` for `.md.j2` rendering, and `jsonschema` for validation when needed.
- Generated import failures should guide callers to install missing libraries into the active harness Python environment or use the Houmao uv-installed environment.
- Stateful generated harnesses expose normal participant access through commands for state initialization, validation, read-only query, record validation, and record application.
- Generated harness commands that expose TOML-backed contracts support `--explain` when structured descriptions exist, with stable source keys in machine-readable output.

## Workspace And Runs

- Generated workspace contracts identify launch cwd, agent work roots, notes or knowledge paths, writable temp/artifact paths, shared resources, and read/write rules when applicable.
- Generated execution preserves durable payloads, rendered outputs, send or reply responses, records, state files, logs, and evidence under a run artifact layout such as `<loop-dir>/runs/<run-id>/`.
- Omit unused default layers only when the manifest and generated docs make the omission explicit.
