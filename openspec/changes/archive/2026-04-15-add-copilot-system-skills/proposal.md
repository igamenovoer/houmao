## Why

Houmao already packages its system skills as native `SKILL.md` directories and can install them into Claude, Codex, and Gemini homes, but GitHub Copilot users cannot install the same Houmao-owned management surface through `houmao-mgr system-skills`. Copilot now has a native skill directory model, so Houmao should project the existing packaged skills into Copilot without introducing a separate scope flag or a parallel catalog.

## What Changes

- Add `copilot` as a supported `houmao-mgr system-skills install|status --tool` target.
- Resolve omitted Copilot homes with the same precedence as existing tools: explicit `--home`, then `COPILOT_HOME`, then a project-scoped default.
- Use `<cwd>/.github` as Copilot's project-scoped default home and project skills under `<home>/skills/<houmao-skill>/`, yielding `.github/skills/<houmao-skill>/` by default.
- Preserve the existing set, explicit skill, CLI-default, copy, symlink, status, and owned-path replacement behavior for Copilot.
- Document Copilot in the CLI reference and system-skills overview while noting that Copilot cloud can discover repository skills but local Houmao operations still require a runtime with `houmao-mgr` and local resources available.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-system-skill-installation`: Add Copilot's visible system-skill projection root and preserve shared installer behavior.
- `houmao-mgr-system-skills-cli`: Add Copilot as a supported `--tool` target with `COPILOT_HOME` and `.github` default-home resolution.
- `docs-cli-reference`: Document Copilot support in the `system-skills` CLI reference.
- `docs-system-skills-overview-guide`: Document Copilot as another explicit external install target in the narrative overview.

## Impact

- `src/houmao/agents/system_skills.py`
- `src/houmao/srv_ctrl/commands/system_skills.py`
- `tests/unit/agents/test_system_skills.py`
- `tests/unit/srv_ctrl/test_system_skills_commands.py`
- `docs/reference/cli/system-skills.md`
- `docs/getting-started/system-skills-overview.md`
