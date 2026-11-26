# Execplan Finalize

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)

## Inputs

Require:
- `<loop-dir>`
- current generated lite execplan artifacts

## Actions

1. Update `execplan/README.md` and `execplan/manifest.md`.
2. Record generated artifact inventory, omissions, unresolved items, and validation notes in concise Markdown.
3. Ensure README files use only `Purpose` and `Contents` unless a file is itself the contract.
4. Ensure optional absent files are intentional, not silent omissions.

## Constraints

- Do not create `execplan/docs/`.
- Do not duplicate contract authority into final notes.
