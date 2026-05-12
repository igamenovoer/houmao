## Why

Generated v5 harnesses should be able to use robust, familiar Python libraries without assuming permission to install packages into the system or project environment. A harness-local `pip --target` install lets generated loops use `jinja2`, `click`, and `jsonschema` while keeping all installed files under the generated `execplan/harness/` directory, and a skill-bundled wheelhouse provides a final offline fallback when network or package indexes are unavailable.

## What Changes

- Teach `execplan-harness` to prefer environment-provided `jinja2`, `click`, and `jsonschema` when available.
- Teach `execplan-harness` to detect library availability through the intended harness Python interpreter, current Python interpreter, and applicable project dependency declarations such as `pyproject.toml`.
- Teach `execplan-harness` to generate `execplan/harness/requirements.txt` and install missing or uncertain libraries with `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt`.
- Add skill-bundled `.whl` files for `jinja2`, `click`, `jsonschema`, and their required dependencies, and teach `execplan-harness` to use them as the final fallback with `pip --no-index --find-links`.
- Teach generated harness entrypoints to prepend `execplan/harness/vendor/` to `sys.path` before importing locally installed packages.
- Update validation and developer design guidance so local pip target dependencies and offline wheelhouse provenance are manifest-indexed and recorded as harness-owned implementation support rather than generated loop contracts.
- **BREAKING** Generated v5 harness guidance will no longer treat these harness libraries as ad hoc imports. Harness generation must detect, declare, or install them locally when the generated harness uses them.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-agent-loop-pairwise-v5-skill`: Define local dependency management for generated harnesses that use Jinja rendering, Click command routing, or JSON Schema validation.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`
- New packaged assets likely under `assets/harness-wheelhouse/` or equivalent
- Affected authoring guidance: `subskills/authoring/execplan-harness.md`, `validate-execplan.md`, design notes, and OpenSpec requirements
- Affected generated execplans: harnesses may include `execplan/harness/requirements.txt`, `execplan/harness/vendor/`, dependency posture metadata, and `sys.path` bootstrap code
- Dependency/runtime impact: local pip target install requires `pip`; network is optional when the generated plan can install from the skill-bundled wheelhouse copied or referenced for the loop
