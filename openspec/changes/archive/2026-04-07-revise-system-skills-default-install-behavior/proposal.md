## Why

`houmao-mgr system-skills` currently makes operators spell out both the target home and the selection mode even when the natural target is already implied by the current project or by a tool-native home redirection env var. That makes common installs verbose, pushes users toward redundant `--default` usage, and leaves the CLI less aligned with Houmao's other project-aware default-resolution patterns.

## What Changes

- Make `houmao-mgr system-skills install` and `houmao-mgr system-skills status` resolve an effective target home when `--home` is omitted.
- Resolve the effective home with this precedence: explicit `--home`, tool-native home env var, project-scoped default.
- Use these project-scoped defaults when no explicit or env-redirected home is active:
  - Claude: `<cwd>/.claude`
  - Codex: `<cwd>/.codex`
  - Gemini: `<cwd>`
- Make `houmao-mgr system-skills install` use the packaged CLI-default set list when neither `--set` nor `--skill` is provided.
- Keep explicit selection in key-value style only through repeatable `--set <name>` and `--skill <name>`.
- Remove the `--default` flag from `houmao-mgr system-skills install`. **BREAKING**
- Update operator-facing help, tests, and CLI reference docs to match the new default-resolution contract.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `houmao-mgr-system-skills-cli`: change `install` and `status` from explicit-home-only behavior to effective-home resolution, make omitted selection mean CLI-default sets, and remove the public `--default` flag.
- `docs-cli-reference`: update the `system-skills` reference to document the new home-resolution precedence, Gemini's project-root default home, and the removal of `--default`.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/system_skills.py` and any helper introduced for tool-home resolution.
- Affected tests: `tests/unit/srv_ctrl/test_system_skills_commands.py` plus any related CLI-reference coverage.
- Affected docs: `docs/reference/cli/system-skills.md`, `docs/reference/cli/houmao-mgr.md`, and any README/reference examples that still show `--default`.
- Operator-facing breaking change: callers must stop using `system-skills install --default`; omission of `--set` and `--skill` becomes the new default-selection path.
