## 1. Project Dependencies

- [x] 1.1 Add `jinja2` and `jsonschema` to `pyproject.toml` runtime dependencies with version bounds compatible with Python 3.11+.
- [x] 1.2 Refresh or verify the development lock/environment metadata needed by repository tooling after dependency changes, if applicable.

## 2. Remove Bundled Wheelhouse

- [x] 2.1 Remove `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/assets/harness-wheelhouse/` and all bundled `.whl` files.
- [x] 2.2 Remove wheelhouse provenance, refresh, compatibility, and `local-wheelhouse-target` guidance from v5 skill docs and developer design docs.

## 3. Harness Guidance

- [x] 3.1 Revise `execplan-harness` to teach `click`, `jinja2`, and `jsonschema` as feature-scoped normal imports provided by the Houmao-installed environment when available.
- [x] 3.2 Revise `execplan-harness` to require generated entrypoints to emit actionable import-failure guidance that names missing dependencies and suggests either installing into the active harness Python environment or using the Houmao uv tool environment.
- [x] 3.3 Revise `execplan-harness` to keep `execplan/harness/requirements.txt`, `vendor/`, and `pip --target` guidance only as optional standalone/custom execution support.
- [x] 3.4 Revise `execplan-harness` to tell authoring agents to test generated harnesses and retry failed dependency/interpreter tests through the Houmao uv-installed environment before treating them as harness implementation bugs.
- [x] 3.5 Revise top-level `SKILL.md` and `agents/openai.yaml` to remove bundled wheelhouse fallback language and mention Houmao-installed dependency availability plus import-failure guidance.

## 4. Validation And Design Docs

- [x] 4.1 Update `validate-execplan` to check feature-scoped dependency declarations and import-failure guidance for generated harnesses that import non-stdlib libraries.
- [x] 4.2 Update `validate-execplan` to report skill-bundled wheelhouse fallback claims as stale or non-conforming.
- [x] 4.3 Update developer design docs to explain the Houmao-installed dependency model, uv-environment recovery guidance, optional standalone `pip --target`, and no source-bundled wheelhouse policy.

## 5. Verification

- [x] 5.1 Validate the updated v5 skill package.
- [x] 5.2 Run a smoke import check for `click`, `jinja2`, and `jsonschema` through the project environment.
- [x] 5.3 Run `git diff --check` and confirm the OpenSpec change is apply-ready.
