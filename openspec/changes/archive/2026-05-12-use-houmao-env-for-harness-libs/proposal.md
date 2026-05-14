## Why

Bundling platform-specific wheel files inside the loop-authoring skill adds package size and ongoing refresh work. Houmao users commonly install the project with `uv`, so common generated-harness libraries can be normal Houmao dependencies and harness import failures can guide users toward either their own Python environment or the Houmao uv-managed environment.

## What Changes

- Add `jinja2` and `jsonschema` to Houmao project runtime dependencies; keep using existing `click`.
- Remove the v5 skill-bundled harness wheelhouse and wheelhouse metadata from source.
- Revise harness guidance to teach agents to use `click`, `jinja2`, and `jsonschema`, but not to vendor or install wheelhouse files from the skill.
- Revise generated harness guidance so import failures print a clear recovery guide:
  - install required libraries into the Python environment used to run the harness; or
  - run the harness through the Houmao uv-installed environment.
- Revise harness authoring guidance so agents testing generated harnesses retry through the Houmao uv-installed environment when tests fail because the active interpreter lacks required harness libraries or otherwise appears to be the wrong execution environment.
- Keep harness-local `pip --target` as an optional fallback for standalone/custom execution, but do not treat it as the main offline fallback.
- Update validation and design docs so they check dependency declarations, import guidance, and removal of bundled wheels.
- **BREAKING** The v5 skill will no longer package offline `.whl` files for generated harness dependencies.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Generated harness dependency guidance changes from skill-bundled wheelhouse fallback to Houmao-installed dependency availability plus clear import-failure remediation.

## Impact

- Affected packaging: `pyproject.toml` runtime dependencies.
- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Removed source assets: `assets/harness-wheelhouse/` and bundled `.whl` files.
- Affected authoring guidance: `execplan-harness`, `validate-execplan`, top-level routing prompt, and developer design notes.
- Generated execplans may still include `execplan/harness/requirements.txt` for custom standalone execution, but should not reference a packaged wheelhouse.
