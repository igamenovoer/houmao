# Plan Operation

Use `plan` when the user wants a dry run or when the requested operation is unclear.

`plan` may inspect local context and report intended changes. It must not mutate files unless the user explicitly provides a Markdown output path for the plan.

## Read First

- Selected flavor page:
  - [../in-repo-workspace.md](../in-repo-workspace.md)
  - [../out-of-repo-workspace.md](../out-of-repo-workspace.md)
- [../reference/local-state-links.md](../reference/local-state-links.md)
- [../reference/submodules.md](../reference/submodules.md)
- [../reference/workspace-contract.md](../reference/workspace-contract.md)

## Inputs

Recover or report:

- operation as `plan`
- workspace flavor
- workspace root
- source repo roots and target repo bindings
- launch profiles and stable agent names
- optional task name for `in-repo`
- optional validation commands for later `validate`
- optional plan output path

If a needed value cannot be inferred safely, make a conservative planned decision and label it as a decision or open question.

## Plan Sections

Produce a structured plan with:

1. Scope: operation, flavor, workspace root, source repo roots, launch profiles.
2. Directory layout: task root, per-agent paths, repo paths, knowledge paths, state paths, shared repo paths.
3. Git actions: worktrees, branches, local bare repos, ignored paths.
4. Local-state links: every candidate considered, selected decision, and reason.
5. Submodules: every tracked submodule considered, selected mode, and reason.
6. Workspace docs: `workspace.md`, workspace summary, ownership rules.
7. Launch-profile changes: cwd updates and optional memo seed file updates.
8. Validation plan: project signals, explicit commands, safe commands to run later, commands needing confirmation.
9. Integration rules: branch naming, submodule commit rules, merge/cherry-pick guidance.
10. Risks and unresolved questions.

## Output

- If the user supplied a plan output path, write the plan there as Markdown.
- Otherwise, print the plan in the response.
- Report that no workspace topology was created.
