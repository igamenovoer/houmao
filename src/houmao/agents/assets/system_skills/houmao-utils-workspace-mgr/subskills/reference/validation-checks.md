# Validation Checks

Validation checks prepared workspace readiness without creating or repairing workspace topology.

Validation may run project tools that create normal cache, build, or environment outputs.

## Inputs

Use:

- explicit operator-provided validation commands
- documented project commands
- discovered project tool signals
- workspace plan or `workspace.md`
- prepared worktree paths
- expected branch names
- expected launch cwd values
- required local-state link decisions
- submodule materialization decisions

Prefer explicit operator-provided commands and documented project commands over discovered guesses.

## Workspace Checks

Report:

- workspace root and `workspace.md` existence
- worktree existence and Git worktree posture
- expected branch versus current branch
- launch cwd existence and visibility surface
- required local-state links or materialized paths
- whether linked paths point to expected sources
- whether linked paths replace tracked content
- tracked submodule presence and selected materialization mode

## Project-Scope Commands

Consider these signals, but run commands only when safe and explicit enough:

| Signal | Examples |
| --- | --- |
| Pixi | `pixi.toml`, explicit `pixi run ...` commands, documented project tasks. |
| Python env | `.venv/`, `venv/`, `pyproject.toml`, `requirements.txt`, explicit interpreter or test command. |
| C or C++ | `CMakeLists.txt`, `Makefile`, `compile_commands.json`, explicit configure/build/check command. |
| Package scripts | `package.json`, lockfiles, explicit script command. |
| In-project scripts | `scripts/`, documented helper commands, explicit operator-selected scripts. |

If a project exposes tooling but no safe command is supplied or documented, report the candidate tooling and ask for the validation command instead of inventing one.

Use the selected worktree or project cwd from the workspace plan. If the command must run somewhere else, report that cwd explicitly before running it.

## Report Shape

Include:

- checks considered
- commands run
- commands skipped and why
- missing local-state links or materialized paths
- failed checks
- recommended follow-up actions, such as rerunning `create` with local-state overrides
