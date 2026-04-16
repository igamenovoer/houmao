## Why

Installing Houmao system skills across several agent tools currently requires repeating the same `system-skills install` command once per tool. The current `--set` option is also terse for an operator-facing command where "set" means a named system-skill bundle. A comma-separated tool list plus an explicit `--skill-set` flag makes the common project bootstrap path shorter while keeping selection and home targeting unambiguous.

## What Changes

- Allow `houmao-mgr system-skills install --tool` to accept a comma-separated list of supported tools such as `claude,codex,copilot,gemini`.
- **BREAKING**: Rename the repeatable named-set selection flag from `--set` to `--skill-set`; `--set` is no longer part of the supported public install surface.
- Resolve each selected tool home independently through the existing omitted-home rules: tool-native environment variable first, then project-scoped default.
- Reject `--home` when the parsed `--tool` value names more than one tool, because one explicit path cannot safely represent multiple tool-home layouts.
- Apply the same `--skill-set`, `--skill`, and `--symlink` selection options to every selected tool.
- Preserve the current single-tool install behavior and payload shape for existing scripts.
- Document the multi-tool install syntax, the `--skill-set` rename, and the multi-tool `--home` restriction in CLI and onboarding documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-system-skills-cli`: `system-skills install` accepts comma-separated tool selections, renames named-set selection to `--skill-set`, and rejects `--home` for multi-tool selections.
- `docs-cli-reference`: CLI reference pages document the new multi-tool install syntax, the `--skill-set` flag, output shape, and home-resolution restriction.
- `readme-structure`: README onboarding examples may use the simplified multi-tool install form and `--skill-set` naming while still explaining when single-tool `--home` is valid.
- `docs-readme-system-skills`: README system-skills coverage reflects the simplified install syntax, explicit skill-set naming, and current examples.

## Impact

- Code: `src/houmao/srv_ctrl/commands/system_skills.py`
- Tests: `tests/unit/srv_ctrl/test_system_skills_commands.py`
- Docs: `README.md`, `docs/reference/cli/system-skills.md`, and `docs/reference/cli/houmao-mgr.md`
- Behavior: public install flag `--set` is renamed to `--skill-set`; no change to the shared installer, packaged catalog, selected skill resolution, projected skill layout, managed launch auto-install, or managed join auto-install
