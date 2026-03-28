## 1. Reshape the project CLI tree

- [x] 1.1 Replace the `project credential` command group in `src/houmao/srv_ctrl/commands/project.py` with `project agent-tools`.
- [x] 1.2 Introduce supported tool families under `project agent-tools` and expose `auth list`, `auth add`, `auth get`, `auth set`, and `auth remove` for each supported tool.
- [x] 1.3 Update `houmao-mgr project --help` and related help text so `agent-tools` is the only documented project-local auth-management subtree.

## 2. Refine auth-bundle CRUD behavior

- [x] 2.1 Refactor auth-bundle helpers so `add` fails on duplicates and `set` fails on missing bundles while preserving the existing `.houmao/agents/tools/<tool>/auth/<name>/` storage model.
- [x] 2.2 Implement a structured `get` command that redacts secret values by default and reports file-backed auth material through metadata rather than raw contents.
- [x] 2.3 Implement `set` as a patch operation that only changes explicitly supplied fields and uses explicit clear-style options for field removal when needed.

## 3. Update tests

- [x] 3.1 Rewrite project CLI inventory/help tests to expect `project agent-tools` and the nested tool/auth subtree.
- [x] 3.2 Replace `project credential` command tests with `agent-tools <tool> auth` CRUD tests covering success and failure cases for `list`, `add`, `get`, `set`, and `remove`.
- [x] 3.3 Keep focused build/launch resolution tests green to confirm the CLI rename does not change project discovery or auth-bundle storage paths.

## 4. Update docs

- [x] 4.1 Replace `project credential` wording in `README.md`, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, `docs/reference/cli.md`, and `docs/reference/cli/houmao-mgr.md` with `project agent-tools <tool> auth ...`.
- [x] 4.2 Update system-files and related reference pages that mention project-local auth creation so they use the new command family and continue describing `.houmao/agents/tools/<tool>/auth/<name>/`.
- [x] 4.3 Sweep the repo for stale `project credential` references in active docs and tests and remove or revise them.

## 5. Verify the redesign

- [x] 5.1 Run focused Ruff and pytest coverage for `src/houmao/srv_ctrl/commands/project.py`, project CLI tests, and auth-bundle behavior.
- [x] 5.2 Run `pixi run docs-build` and spot-check `houmao-mgr project --help` plus one tool-specific `auth --help` surface for the new tree.
