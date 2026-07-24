# Summarize Operation

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `summarize` when the user wants compact facts about a planned or prepared workspace.

The summary is consumer-neutral. It may be used by humans, scripts, or upstream planners, but this skill does not make any caller type part of its own contract.

## Read First

- Selected flavor page when flavor is known:
  - [in-repo-workspace.md](in-repo-workspace.md)
  - [out-of-repo-workspace.md](out-of-repo-workspace.md)
- [../references/workspace-contract.md](../references/workspace-contract.md)

## Summary Fields

For each prepared workspace, identify:

- selected workspace flavor
- workspace root and task root when applicable
- selected `task-name` for `in-repo`
- launch cwd or shared visibility surface
- private source-mutation surface
- shared writable surfaces
- default read-only shared surfaces
- local-state link posture
- validation posture when validation has run
- ad hoc worktree posture
- branch names
- relevant `workspace.md` path

For in-repo mode, include `<repo-root>/houmao-ws` as the untracked workspace collection, `<task-root>/shared-kb/` as cross-run shared task knowledge, `<task-root>/owner-states/<subdir>/...` as per-run task-owner bookkeeping when selected, and each agent's private `repo/` worktree.

## Output

Prefer a concise Markdown table plus short notes for risks or missing validation.
