## Why

`houmao-mgr system-skills install --tool codex,claude,gemini` currently reports only each resolved tool home in plain output. That is misleading for Gemini because the resolved home is the project root while Houmao-owned skills are installed under `.gemini/skills/`, so the console output can make a successful install look like it did not install in the Gemini-visible location.

## What Changes

- Report each tool's skill projection root or projected skill paths in `system-skills install` plain output, so operators can see where skills were actually installed.
- Preserve the existing distinction between effective home and tool-native skill projection paths, especially for Gemini's `<home>/.gemini/skills/` layout.
- Keep existing install semantics, selection behavior, projection modes, and structured JSON fields intact unless new additive fields are needed to make the projection root explicit.
- Update status/uninstall plain output only where needed for consistent terminology around effective homes and projected skill paths.
- Update tests and CLI reference docs to lock the improved operator-facing output.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-mgr-system-skills-cli`: Clarify `system-skills install` and related plain output so resolved homes are not confused with actual skill projection locations.
- `docs-cli-reference`: Document the improved `system-skills` output semantics for effective homes versus skill projection roots.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/system_skills.py`
- Affected tests: `tests/unit/srv_ctrl/test_system_skills_commands.py`
- Affected docs: `docs/reference/cli/system-skills.md`
- No dependency, data-format, or install-layout changes are expected.
