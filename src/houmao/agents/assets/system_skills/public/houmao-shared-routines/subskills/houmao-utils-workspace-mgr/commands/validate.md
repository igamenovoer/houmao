# Validate Operation

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `validate` when the user wants to check that a planned or created workspace is ready for project work.

Validation does not create worktrees, rewrite launch profiles, repair links, or change workspace ownership rules. Project commands invoked by validation may create normal cache, build, or environment outputs.

## Read First

- Selected flavor page when flavor is known:
  - [in-repo-workspace.md](in-repo-workspace.md)
  - [out-of-repo-workspace.md](out-of-repo-workspace.md)
- [../references/validation-checks.md](../references/validation-checks.md)
- [../references/local-state-links.md](../references/local-state-links.md)
- [../references/submodules.md](../references/submodules.md)
- [../references/workspace-contract.md](../references/workspace-contract.md)

## Inputs

Recover or ask for:

- workspace root or task root
- agent worktree paths
- expected branches
- selected launch cwd values
- local-state link plan or `workspace.md`
- explicit validation commands, if any
- safe documented project commands, if any

Prefer explicit operator-provided commands and documented project commands. Do not invent heavy builds or destructive commands.

## Checks

Validate and report:

- workspace root and `workspace.md` exist
- each expected worktree exists and is a Git worktree
- each worktree is on the expected branch or reports its current branch clearly
- each launch cwd exists and reaches the expected visibility surface
- required local-state links or materialized paths exist and point to expected sources
- linked paths do not replace tracked content
- tracked submodules are present according to the selected materialization mode
- project-scope commands can run from the selected worktree or cwd when commands are supplied or safely documented

## Project-Scope Command Signals

Consider these signals, but run commands only when safe and explicit enough:

| Signal | Examples |
| --- | --- |
| Pixi | `pixi.toml`, explicit `pixi run ...` commands, documented project tasks. |
| Python env | `.venv/`, `venv/`, `pyproject.toml`, `requirements.txt`, explicit interpreter or test command. |
| C or C++ | `CMakeLists.txt`, `Makefile`, `compile_commands.json`, explicit configure/build/check command. |
| Package scripts | `package.json`, lockfiles, explicit script command. |
| In-project scripts | `scripts/`, documented helper commands, explicit operator-selected scripts. |

If a project exposes tooling but no safe command is supplied or documented, report the candidate tooling and ask for the validation command instead of inventing one.

## Output

Report:

- checks considered
- commands run
- commands skipped and why
- missing local-state links or materialized paths
- failed checks
- recommended follow-up actions, such as rerunning `create` with local-state overrides
