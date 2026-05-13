# Execplan Specs Process

## Read First

- `../reference/generation-pipeline.md`
- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
- MUST READ: `../reference/runtime-mail-model.md`

## Preconditions

- Current intention source exists.
- User wants the first staged execplan generation step or `execplan-fast-forward` / `execplan-step-by-step` is orchestrating all stages.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read:
- relevant intention Markdown;
- accepted ADRs when present;
- existing process specs only as generated material to replace or update.

## Outputs

Generate or update the canonical process overview at:

```text
<loop-dir>/execplan/specs/collab/collab-overview.md
```

Create or update generated artifact directory README files for emitted process-spec directories:

```text
<loop-dir>/execplan/specs/README.md
<loop-dir>/execplan/specs/collab/README.md
```

Use additional files under `<loop-dir>/execplan/specs/collab/` only when the process model needs them, such as `loop-policy.toml`, `topology/graph.md`, or `records/*.schema.json`.

If additional `collab/` child directories are emitted, add `README.md` files for those directories too.

Do not write the primary process overview as a flat file such as `<loop-dir>/execplan/specs/process.md`.

The canonical process overview contains collaboration process material such as:
- phases;
- selected topology mode or `UNRESOLVED - topology mode`;
- cycle posture, including pairwise normalization or generic cycle-control needs;
- events;
- handoffs or exchanges;
- local-close result routing for `pairwise-tree`, or explicit reply/forward routing for `generic-graph`;
- predecessor-context posture for generic routes, including selected carried context or explicit omission;
- schema-typed mail family outline when mail drives events;
- runtime trigger model, especially notifier-prompt-driven mail events when the loop is mail-driven;
- execution mode model when the loop supports both auto and manual operation;
- tick responsibilities;
- participant ownership;
- terminal and recovery posture;
- Python-style process pseudocode with fenced `python` code blocks and inline comments;
- a high-level Mermaid sequence graph using fenced `mermaid` code blocks;
- provisional participant, message, state, and record families;
- unresolved process decisions.

## Actions

1. Derive the loop process model from intention source.
2. Create or replace `<loop-dir>/execplan/specs/collab/collab-overview.md` as the first process-stage authority.
3. Create or update README files for emitted `specs/` directories using only `Purpose` and `Contents`.
4. Express the model in generic process terms before generating derived contracts.
5. Select or mark unresolved exactly one topology mode:
  - `pairwise-tree`: document local-close handoffs, immediate-upstream result return, and any accepted cycle normalization through an existing participant;
  - `generic-graph`: document directed routes, cycle control, dedupe or repeat-visit posture, termination, and task-specific predecessor-context needs.
6. Record result-routing semantics:
  - pairwise results return to immediate upstream unless an explicit terminal or operator exception exists;
  - generic results, replies, and forwards follow explicit route or message-family policy.
7. For mail-driven loops, record that Houmao notifier prompts wake agents for mail processing and optional follow-up ticks; do not model in-chat waits or periodic tick workers.
8. Outline schema-typed mail families that will become concrete contracts later, including provisional `schema_id` names when known.
9. When manual operation is supported, model `auto` and `manual` as execution modes separate from run lifecycle state:
  - `auto`: the default initial mode; notifier prompts drive mail and follow-up tick turns;
  - `manual`: notifier wakeups are suspended or disabled, and the operator prompts one bounded participant turn at a time.
10. Include a Python-style pseudocode section that explains how the loop advances:
  - use a fenced `python` code block;
  - name generic roles, events, state queries, handoff decisions, tick passes, terminal branches, and recovery branches;
  - show mode checks before tick work when both modes apply;
  - show topology-mode branch behavior when pairwise-tree and generic-graph choices materially differ;
  - add inline `#` comments for conditions, actions, state effects, and stopping points;
  - keep it domain-derived but not implementation-bound Python.
11. Include a high-level Mermaid sequence section:
  - use a fenced `mermaid` code block;
  - show the main participants or role families;
  - show the normal event/handoff path;
  - show local-close replies or generic forwards as selected by topology;
  - show mail/notifier/tick behavior when the loop is mail-driven;
  - show the operator-prompted manual path when manual operation is part of the process;
  - omit low-level transport or storage details that belong to later contract or harness stages.
12. Identify which later stages are required or intentionally omitted.
13. Preserve unresolved process choices as `UNRESOLVED - <reason>`.
14. Do not finalize objective, participant, communication, state, workspace, harness, skill, agent, docs, or manifest details in this stage; leave them for downstream stages.

## Downstream Effects

- Changes here invalidate every later staged output unless the changed process facts are explicitly local and documented.
- Downstream stages must derive process semantics from this stage.

## Constraints

- Do not force a built-in participant topology.
- Do not import process policy from examples as global behavior.
- Do not create flat process files directly under `execplan/specs/`.
- Do not perform platform setup or runtime execution.
