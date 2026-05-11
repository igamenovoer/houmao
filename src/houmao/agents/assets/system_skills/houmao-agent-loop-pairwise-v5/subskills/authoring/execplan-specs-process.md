# Execplan Specs Process

## Preconditions

- Current intention source exists.
- User wants the first staged execplan generation step or `generate-execplan` is orchestrating all stages.

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

Generate or update process-first specs under `execplan/specs/` using paths that fit the loop shape, normally collaboration process material such as:
- phases;
- events;
- handoffs or exchanges;
- tick responsibilities;
- participant ownership;
- terminal and recovery posture;
- provisional participant, message, state, and record families;
- unresolved process decisions.

## Actions

1. Derive the loop process model from intention source.
2. Express the model in generic process terms before generating derived contracts.
3. Identify which later stages are required or intentionally omitted.
4. Preserve unresolved process choices as `UNRESOLVED - <reason>`.
5. Do not finalize objective, participant, communication, state, workspace, harness, skill, agent, docs, or manifest details in this stage; leave them for downstream stages.

## Downstream Effects

- Changes here invalidate every later staged output unless the changed process facts are explicitly local and documented.
- Downstream stages must derive process semantics from this stage.

## Constraints

- Do not force a built-in participant topology.
- Do not import process policy from examples as global behavior.
- Do not perform platform setup or runtime execution.
