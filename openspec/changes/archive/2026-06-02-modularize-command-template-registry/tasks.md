## 1. Package Skeleton And Compatibility

- [x] 1.1 Create `src/houmao/srv_ctrl/command_templates/` with `models.py`, `builders.py`, `registry.py`, `rendering.py`, `export.py`, and `families/`.
- [x] 1.2 Move `TemplateField`, `FieldConflict`, `CommandTemplate`, value-type literals, and shared choices into the new package with frozen typed models preserved.
- [x] 1.3 Move builder helpers such as field, flag, choice, clear, conflict, and template construction into `builders.py`.
- [x] 1.4 Keep `src/houmao/srv_ctrl/commands/command_templates.py` as a thin compatibility wrapper or update imports so existing callers continue to work.

## 2. Family Module Migration

- [x] 2.1 Move project easy templates into `families/project_easy.py` without changing template ids or render output.
- [x] 2.2 Move low-level project agent definition templates into `families/project_agents.py` without changing template ids or render output.
- [x] 2.3 Move credential template generation into `families/credentials.py`, preserving project/plain lanes, Claude/Codex/Gemini fields, verbs, and conflicts.
- [x] 2.4 Move agent lifecycle templates into `families/agents_lifecycle.py`, preserving launch, launch-profile launch, join, relaunch, and cleanup templates.
- [x] 2.5 Move gateway templates into `families/agents_gateway.py`, preserving lifecycle, prompt, interrupt, send-keys, TUI, mail-notifier, and reminder templates.
- [x] 2.6 Move mailbox and managed-agent mailbox binding templates into `families/mailbox.py`.
- [x] 2.7 Move managed-agent mail fallback templates into `families/managed_agent_mail.py`.
- [x] 2.8 Implement registry assembly that imports all family modules, returns a stable template-id map, and fails clearly on duplicate ids.

## 3. Rendering And Existing CLI Behavior

- [x] 3.1 Move intent loading, field validation, blocker detection, warning generation, omitted-field reporting, and argv rendering into `rendering.py`.
- [x] 3.2 Preserve `list_command_templates`, `get_command_template`, `show_command_template`, and `render_command_template` public functions.
- [x] 3.3 Verify `houmao-mgr internals command-templates list|show|render` keep their existing JSON payload shape and plain output behavior.

## 4. YAML Export

- [x] 4.1 Add deterministic YAML export helpers for a single template and the complete registry in `export.py`.
- [x] 4.2 Add file-writing helpers for exporting one template to a YAML file and all templates to an output directory with stable file names.
- [x] 4.3 Add `houmao-mgr internals command-templates export --id <template-id>` for stdout and optional file output.
- [x] 4.4 Add `houmao-mgr internals command-templates export --all` for stdout and optional output-directory export.
- [x] 4.5 Make export fail clearly for missing selection, `--id` plus `--all`, or incompatible output options.

## 5. Tests And Validation

- [x] 5.1 Add registry tests for duplicate-id detection and family-module inventory coverage.
- [x] 5.2 Update existing command-template tests to import the new package directly where appropriate while preserving CLI coverage.
- [x] 5.3 Add YAML export tests proving single-template YAML parses to the same payload as `show` and is deterministic across repeated exports.
- [x] 5.4 Add YAML export tests for all-template stdout and output-directory modes.
- [x] 5.5 Run `pixi run ruff format` on changed Python files.
- [x] 5.6 Run `pixi run lint`, `pixi run typecheck`, focused command-template tests, and the relevant broader unit test command.
- [x] 5.7 Run `openspec validate modularize-command-template-registry --strict`.
