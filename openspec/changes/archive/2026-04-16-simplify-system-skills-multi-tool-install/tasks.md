## 1. CLI Implementation

- [x] 1.1 Add a `--tool` parser for `system-skills install` that trims comma-separated entries, preserves request order, and rejects empty entries, unsupported tools, and duplicates before mutation.
- [x] 1.2 Add single-tool-only validation for `--home`, with an explicit error when a multi-tool install supplies `--home`.
- [x] 1.3 Rename the public repeatable named-set flag from `--set` to `--skill-set`, without keeping `--set` as a supported alias.
- [x] 1.4 Refactor install result payload construction so single-tool invocations keep the current scalar payload shape and multi-tool invocations emit `tools` plus per-tool `installations`.
- [x] 1.5 Keep shared installer calls single-tool and sequential, applying the same skill-set, skill, and projection-mode selection to each parsed tool.
- [x] 1.6 Add selection preflight so unknown skill sets or skills fail before any multi-tool filesystem mutation.

## 2. Tests

- [x] 2.1 Add unit coverage for comma-separated multi-tool installs into project-scoped default homes for Claude, Codex, Copilot, and Gemini.
- [x] 2.2 Add unit coverage that multi-tool install rejects `--home` before creating any selected skill directories.
- [x] 2.3 Add unit coverage for malformed and duplicate tool lists such as `codex,,gemini` and `codex,codex`.
- [x] 2.4 Add unit coverage that `--skill-set` installs named system-skill sets and that the removed `--set` flag is rejected.
- [x] 2.5 Add unit coverage that single-tool install behavior and JSON payload shape remain unchanged for explicit `--home`, env redirect, project default, and `--symlink` cases.
- [x] 2.6 Add unit coverage that unknown skill-set or skill selection fails before a multi-tool install mutates any target home.

## 3. Documentation

- [x] 3.1 Update `docs/reference/cli/system-skills.md` with `--skill-set` naming, comma-separated install syntax, the multi-tool `--home` restriction, home-resolution behavior, and multi-tool JSON output shape.
- [x] 3.2 Update `docs/reference/cli/houmao-mgr.md` so the command-group summary reflects `--skill-set`, comma-separated install support, and the single-tool-only `--home` rule.
- [x] 3.3 Update README quick-start and system-skills examples to use `--skill-set`, the simplified multi-tool form where helpful, and clear guidance for when single-tool `--home` remains valid.

## 4. Verification

- [x] 4.1 Run `openspec validate simplify-system-skills-multi-tool-install --strict` and fix any proposal/spec/task issues.
- [x] 4.2 Run `pixi run test tests/unit/srv_ctrl/test_system_skills_commands.py`.
- [x] 4.3 Run `pixi run lint` or targeted Ruff checks for edited Python files.
