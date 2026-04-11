## 1. Baseline and Caller Analysis

- [x] 1.1 Run a baseline focused project-command test slice and record the command used for final comparison.
- [x] 1.2 Inspect `src/houmao/srv_ctrl/commands/project.py` helper callers with `rg` before moving or deleting private helpers.
- [x] 1.3 Confirm whether the project-local credential helper cluster superseded by `commands/credentials.py` has runtime callers.
- [x] 1.4 Delete confirmed-dead project-local credential helper code, or explicitly leave it for relocation if caller analysis is inconclusive.

## 2. Shared Project Command Helpers

- [x] 2.1 Create `src/houmao/srv_ctrl/commands/project_common.py` for cross-family project command helpers.
- [x] 2.2 Move overlay resolution helpers such as `_ensure_project_roots`, `_ensure_project_overlay`, `_resolve_existing_project_roots`, and project status wording helpers that are used across command families.
- [x] 2.3 Move narrow shared utility helpers such as non-empty name validation, yaml mapping helpers, model config helpers, and prompt text helpers only when more than one extracted family needs them.
- [x] 2.4 Update imports in `project.py` and any extracted modules to use `project_common.py` without creating circular imports.

## 3. Command Family Extraction

- [x] 3.1 Extract project mailbox commands into `src/houmao/srv_ctrl/commands/project_mailbox.py` and register the resulting group from `project.py`.
- [x] 3.2 Extract explicit launch-profile commands and launch-profile storage/payload helpers into `src/houmao/srv_ctrl/commands/project_launch_profiles.py`.
- [x] 3.3 Extract easy profile, easy specialist, and easy instance commands into `src/houmao/srv_ctrl/commands/project_easy.py`, importing shared launch-profile helpers from `project_launch_profiles.py`.
- [x] 3.4 Extract project agent tool setup commands into `src/houmao/srv_ctrl/commands/project_tools.py`.
- [x] 3.5 Extract project roles, presets, and recipes commands into `src/houmao/srv_ctrl/commands/project_definitions.py`.
- [x] 3.6 Keep `src/houmao/srv_ctrl/commands/project.py` as the public `project_group` entrypoint that registers extracted groups plus `project_credentials_group`.

## 4. Test and Import Path Updates

- [x] 4.1 Update project command tests that monkeypatch moved private helpers to patch the new owning module path.
- [x] 4.2 Add or update CLI shape coverage for `houmao-mgr project --help` and the extracted subgroups: `agents`, `agents launch-profiles`, `easy`, and `mailbox`.
- [x] 4.3 Add a lightweight architectural test or assertion that `project.py` remains the public entrypoint and does not contain all project command families after extraction.
- [x] 4.4 Verify `commands/main.py` still imports `project_group` from `houmao.srv_ctrl.commands.project`.

## 5. Behavior Verification

- [x] 5.1 Run the same focused project-command test slice captured in task 1.1.
- [x] 5.2 Run the CLI shape contract tests that cover project command help output.
- [x] 5.3 Run Ruff on edited command modules and project command tests.
- [x] 5.4 Run mypy or the narrowest applicable typecheck if cross-module helper moves affect typed helper signatures.
- [x] 5.5 Run `openspec validate split-project-command-module --strict`.

## 6. Cleanup and Review

- [x] 6.1 Inspect `src/houmao/srv_ctrl/commands/project.py` after extraction to ensure it is primarily root entrypoint and registration logic.
- [x] 6.2 Inspect extracted module imports for circular dependency smells or broad helper imports from unrelated command families.
- [x] 6.3 Confirm no command family has been dropped from `houmao-mgr project --help`.
- [x] 6.4 Update this task list as implementation completes so OpenSpec progress reflects the refactor state.
