## 1. Entrypoint Refactor

- [x] 1.1 Rewrite `houmao-utils-workspace-mgr/SKILL.md` as a concise router with activation, help, operations, routing, references, and constraints.
- [x] 1.2 Replace long inline policy sections in `SKILL.md` with operation and reference links.
- [x] 1.3 Add an operation table or compact list for `help`, `plan`, `create`, `validate`, and `summarize`.
- [x] 1.4 Document `execute` only as a compatibility alias for `create` if retained.
- [x] 1.5 Remove loop-specific wording from the workspace-manager entrypoint.

## 2. Routed Operation And Reference Pages

- [x] 2.1 Add operation pages for `plan`, `create`, `validate`, and `summarize`.
- [x] 2.2 Move plan behavior from the entrypoint into `subskills/operations/plan.md`.
- [x] 2.3 Move create behavior from the entrypoint into `subskills/operations/create.md`.
- [x] 2.4 Add `subskills/operations/validate.md` for workspace readiness checks.
- [x] 2.5 Add `subskills/operations/summarize.md` for consumer-neutral workspace summaries.
- [x] 2.6 Move shared local-state link policy into a reference page.
- [x] 2.7 Move shared submodule materialization policy into a reference page.
- [x] 2.8 Move memo seed and workspace contract documentation policy into reference pages.

## 3. Workspace Validation Semantics

- [x] 3.1 Define validation inputs for explicit operator commands, discovered project tool signals, and workspace plan references.
- [x] 3.2 Document validation checks for worktree existence, branch posture, required local-state links, submodule materialization, and launch cwd expectations.
- [x] 3.3 Document project-scope command validation for Pixi, Python virtual environments, C or C++ build systems, package scripts, and in-project scripts.
- [x] 3.4 Ensure validation avoids inventing heavy or destructive commands when no safe project command is supplied or documented.
- [x] 3.5 Ensure validation reports considered, run, skipped, failed, and missing-readiness checks.

## 4. Tests And Documentation

- [x] 4.1 Update packaged asset tests to assert the concise router shape and new operation names.
- [x] 4.2 Update tests to assert validation routing and consumer-neutral summary wording.
- [x] 4.3 Update README and system-skill docs that describe workspace-manager operation names.
- [x] 4.4 Run focused system-skill asset and docs tests.
- [x] 4.5 Run `openspec validate refactor-workspace-mgr-subcommands --strict`.
