# Execplan Finalize

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`

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
