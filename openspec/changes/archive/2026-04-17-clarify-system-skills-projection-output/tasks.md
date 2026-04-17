## 1. Renderer Helpers

- [x] 1.1 Add a small plain-rendering helper in `src/houmao/srv_ctrl/commands/system_skills.py` that derives projection display data from `home_path` plus projected relative dirs.
- [x] 1.2 Ensure the helper returns clear effective-home and projection-location text for normal `skills/<name>` tools and Gemini `.gemini/skills/<name>` tools without hard-coding Gemini-specific prose.
- [x] 1.3 Keep existing structured JSON fields unchanged, adding only optional additive fields if implementation needs them.

## 2. CLI Plain Output

- [x] 2.1 Update single-tool `system-skills install` plain output to show the effective home and installed projected skill path or projection root.
- [x] 2.2 Update multi-tool `system-skills install` plain output to show each tool's effective home plus skill projection location, including Gemini `.gemini/skills`.
- [x] 2.3 Update `system-skills status` plain output so each discovered skill includes its projected relative or absolute path alongside projection mode.
- [x] 2.4 Update `system-skills uninstall` plain output so removed or absent locations are represented by projection roots or representative projected paths, especially for Gemini.

## 3. Tests

- [x] 3.1 Add or update unit tests for multi-tool plain install output covering `codex,claude,gemini` and asserting Gemini reports `.gemini/skills`.
- [x] 3.2 Add or update unit tests for single-tool Gemini plain install output showing `.gemini/skills/<skill>`.
- [x] 3.3 Add or update unit tests for Gemini plain status output showing the discovered `.gemini/skills/<skill>` path.
- [x] 3.4 Add or update unit tests for multi-tool uninstall plain output showing Gemini removed or absent projection information.
- [x] 3.5 Confirm existing JSON output tests still pass and still assert `home_path` plus `projected_relative_dirs`.

## 4. Documentation

- [x] 4.1 Update `docs/reference/cli/system-skills.md` to describe effective homes versus projection locations in install/status/uninstall output.
- [x] 4.2 Include a Gemini example or note showing that effective home `/workspace/repo` maps to skill projection root `/workspace/repo/.gemini/skills/`.

## 5. Validation

- [x] 5.1 Run `pixi run pytest tests/unit/srv_ctrl/test_system_skills_commands.py`.
- [x] 5.2 Run `pixi run lint` if the implementation changes Python formatting or imports.
- [x] 5.3 Run `openspec status --change clarify-system-skills-projection-output` and confirm the change is apply-ready.
