# Generate Execplan

## Preconditions

- User wants generated execution material.
- Current intention source exists.
- `execplan/` should be derived from `intention/`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read:
- relevant files under `<loop-dir>/intention/`

Rules:
- Do not require `adrs/`.

## Generated Shape

Use this scaffold profile unless the intention source clearly needs a smaller equivalent shape. Create or replace generated material under:

```text
<loop-dir>/execplan/
  manifest.toml
  specs/
    objective/
    collab/
    comms/
    state/
    workspace/
    participants/
  skills/
  agents/
  harness/
  docs/
```

Minimum responsibilities:
- `manifest.toml` indexes generated artifacts, generated-source posture, and plan revision.
- `specs/` contains machine-readable loop contracts. Use subdirectories only when the loop needs them:
  - `specs/objective/` for goals, constraints, success posture, and references to policy sections.
  - `specs/collab/` for topology, scheduling policy, handoff rules, and structured collaboration record schemas.
  - `specs/comms/` for mail or message schemas, template registries, and renderers.
  - `specs/state/` for runtime state schemas, seed data, and invariants when the loop needs bookkeeping state.
  - `specs/workspace/` for workdir, command, artifact, environment, path contracts, and workspace-manager inputs.
  - `specs/participants/` for abstract participant roles and stable role instances.
- `skills/` contains generated on-event skills, on-tick skills, lifecycle skills, or shared utility skills. Keep each skill bounded to one trigger or role responsibility.
- `agents/` contains concrete agent bindings and prompt sources that map live Houmao agents to participant roles, installed skills, and workspace policy.
- `harness/` contains the plan-local command surface for data-model validation, dynamic lookup, query, rendering, controlled record application, and other deterministic loop-local mechanics.
- `docs/` contains generated human support views that explain generated contracts without becoming source authority.
- When a default layer or file is intentionally unnecessary, record the omission in the manifest, generated docs, or validation notes.

## Participant And State Defaults

Participant model:
- separate participant role templates, stable participant role instances, and concrete Houmao agent bindings;
- avoid assuming a fixed topology, fixed role names, or fixed role count;
- put concrete prompt sources, installed skills, maintained support skills, skill-install mode, memo seed policy, and workspace policy in `execplan/agents/` when those facts apply.

Runtime bookkeeping:
- generate state contracts only when the loop needs durable handoffs, scheduling decisions, recovery, audit, or other compact runtime facts;
- default durable state to compact records for:
  - plan metadata;
  - process state;
  - handoffs or exchanges;
  - communication payload lifecycle;
  - operator intent events;
  - generic events;
- add task-specific records, evidence models, scoring models, and domain tables only from intention source or accepted clarification decisions.

## Workspace Rules

- Default generated workspace policy to Houmao `in-repo` style unless intention source explicitly asks for another flavor or a custom operator-owned workspace.
- Represent setup inputs for `houmao-utils-workspace-mgr`: `task-name`, agent names, workspace flavor, launch profile names, optional memo-seed posture, and requested loop bookkeeping directories.
- Use the standard in-repo layout as the base: `<repo-root>/houmao-ws/<task-name>/workspace.md`, per-agent `kb/`, per-agent `repo/` worktrees, and task `shared-kb/`.
- Add loop bookkeeping directories only when useful, such as task-level `runs/` and `artifacts/`, per-agent `artifacts/`, and ignored per-agent `tmp/`.
- Generate an operator-facing workspace-management skill only as a thin router that reads the execplan workspace contract and calls `houmao-utils-workspace-mgr`; do not embed Git worktree creation mechanics in generated skills.

## Run Artifact Defaults

- When execution produces durable artifacts, define a run artifact layout such as `<loop-dir>/runs/<run-id>/` or an explicit equivalent.
- Preserve source payloads, rendered outputs, send or reply responses, record files, state files, logs, evidence, and operator notes when those artifacts exist.
- Treat the run artifact layout as the audit and recovery surface; do not depend only on live mailbox state for later status or recovery.

## Communication Generation Defaults

Mail-driven path:

```text
TOML payload -> schema validation -> Markdown rendering -> maintained Houmao mail send
```

Rules:
- Treat ordinary cross-agent participant handoffs as mail-driven unless the intention source explicitly chooses a non-mail mechanism.
- Use the same structured-payload, schema-validation, and renderer pattern for any artifact that must be both machine-recorded and human-readable.
- Generated execplans own loop-specific communication semantics:
  - sender and recipient routes;
  - message families;
  - payload schemas;
  - Markdown renderers;
  - reply expectations;
  - state or record effects caused by mail.

Platform boundary:
- generated specs, skills, agent bindings, and harness commands define loop semantics;
- `houmao-mailbox-mgr` owns mailbox setup, inspection, repair, cleanup, export, registration, and late mailbox binding;
- `houmao-agent-email-comms` owns ordinary mail status, list, read, send, post, reply, mark, move, and archive operations;
- `houmao-process-emails-via-gateway` owns notifier-driven open-mail rounds when the current round provides the gateway base URL;
- `houmao-agent-messaging` owns managed-agent prompt, interrupt, mailbox handoff, and gateway-backed communication routing;
- `houmao-agent-gateway` owns gateway lifecycle and gateway posture;
- generated harness commands may validate, render, query, and apply loop-local records, but they do not deliver, read, reply to, or archive mailbox messages.

Default package:
- generate this package for mail-driven loops unless intention source chooses an equivalent shape;
- keep the package under `<loop-dir>/execplan/specs/comms/`.

```text
<loop-dir>/execplan/specs/comms/
  comms-overview.md
  templates.toml
  schemas/
    freeform-notice.schema.json
    ack.schema.json
    <message-family>.schema.json
  renderers/
    freeform-notice.md.j2
    ack.md.j2
    <message-family>.md.j2
```

Registry rules:
- `specs/comms/templates.toml` is the registry for generated message families.
- Each ordinary generated family should be discoverable by:
  - short template name;
  - full schema id.
- Each registry entry should identify:
  - schema id;
  - schema path;
  - renderer path;
  - payload format, normally `toml`;
  - sender and recipient role constraints when the family is route-limited;
  - expected reply schema id or reply family when the message expects a reply.

Payload envelope:
- use this common envelope unless intention source selects another convention;
- include:
  - `schema_id`;
  - `schema_version`;
  - `payload_id`;
  - `kind`;
  - `run_id`;
  - `plan_revision`;
  - `handoff_id` or another generated exchange id;
  - `context`;
  - `requested_reply_schema_id` when the message expects a structured reply.

Rendered Markdown:
- include:
  - a fenced `houmao-email-metadata` block with schema id, schema version, kind, run id, plan revision, exchange or handoff id, and important routing or result references;
  - a `Context` section explaining why the mail was sent;
  - template-specific human-readable sections;
  - an explicit reply request section when the sender expects a reply.

Generic families:
- include `freeform-notice` and `ack` by default unless intention source forbids them or defines equivalent families;
- `freeform-notice` covers participant-facing or operator-origin information that does not fit a task-specific request/reply template but still needs:
  - validated context;
  - requested action;
  - reply expectation fields;
- `ack` covers receipt-only acknowledgement;
- `ack` does not imply a substantive state transition unless another generated contract says so.

Lifecycle records:
- when runtime state exists, generate communication payload lifecycle records for templated mail;
- the default lifecycle record includes payload id, schema id, kind, exchange or handoff id, source payload, status, optional platform message id, optional failure reason, and timestamps.

Harness email commands:
- expose `email schema|validate|render|apply|query` when the loop needs command-line access to communication contracts;
- `email schema` explains a template or schema id;
- `email validate` validates a TOML payload without delivery;
- `email render` produces Markdown without delivery;
- `email apply` records loop-local payload lifecycle or mail-caused record effects after validation;
- `email query` reads loop-local payload lifecycle or communication state.

Mail-received event skills:
- generate one on-event skill for each concrete received message family that needs role behavior;
- each such skill should:
  - name its owning participant role;
  - trigger on the received schema id or message family;
  - read only the needed context;
  - validate payload or record inputs when applicable;
  - perform one bounded role-owned action;
  - send required replies through maintained Houmao mail support;
  - archive the processed message only after required work and required replies succeed;
  - stop.
- Put aggregation, scheduling, timeout handling, reconciliation, and completion checks in on-tick skills when those responsibilities do not belong to one received-mail event.

## Actions

1. Confirm `<loop-dir>` and intention files exist.
2. Derive the execplan from intention source only.
3. Identify which generated contract layers are needed: objective, collaboration, communication, state, workspace, participants, skills, agents, harness, and docs.
4. Generate domain-specific objectives, roles, policies, evidence gates, and tools only when intention source states them.
5. Generate participant contracts separately from concrete Houmao agent bindings.
6. Put dynamic values that agents need during work into generated specs, runtime state, or harness lookup surfaces rather than baking them into static skill prose.
7. Generate on-event skills for concrete incoming events such as received schema-specific mail, and on-tick skills for scheduler-like responsibilities that do not belong to one incoming event.
8. When workspace setup is needed, generate workspace contracts that route creation to `houmao-utils-workspace-mgr` and keep the default as in-repo plus explicitly listed bookkeeping directories.
9. When durable runtime artifacts are expected, define the run artifact layout and what it preserves.
10. Mark generated Markdown with a clear generated-source note or metadata block.
11. Keep generated skill files concise and progressively disclosed.
12. Preserve unresolved assumptions as explicit `UNRESOLVED - <reason>` entries.
13. Run the `validate-execplan` operation before reporting completion.

## Constraints

- Do not treat generated `execplan/` as editable source.
- Do not require ADR discovery.
- Do not copy policies from examples or reference plans into unrelated loops.
- Do not make one reference topology, state backend, scheduler, communication schema set, or harness command set mandatory for all loops.
- Do not implement workspace creation mechanics in generated skills when `houmao-utils-workspace-mgr` can represent the layout.
- Do not create platform launch side effects from this page.
