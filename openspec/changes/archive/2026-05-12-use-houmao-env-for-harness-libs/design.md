## Context

The current v5 harness guidance was moving toward a skill-bundled wheelhouse fallback for `click`, `jinja2`, `jsonschema`, and transitive dependencies. That works offline, but it puts platform-specific binary wheels in the source tree and creates a refresh burden for a small set of general-purpose harness libraries.

Houmao is normally installed and invoked through `uv` tooling. If `jinja2` and `jsonschema` become normal Houmao runtime dependencies, then the uv-installed Houmao environment can provide the same libraries that generated harnesses need. `click` is already a Houmao runtime dependency. Generated harnesses can still be run from arbitrary Python environments, but import failures should become a clear operator-facing guide rather than a hidden dependency problem.

## Goals / Non-Goals

**Goals:**

- Make `click`, `jinja2`, and `jsonschema` available from the normal Houmao-installed environment.
- Remove source-bundled harness `.whl` files and wheelhouse provenance maintenance from the v5 skill.
- Teach generated harnesses to import these libraries normally and fail with actionable guidance when the chosen interpreter does not provide them.
- Preserve standalone/custom execution by documenting local installation into the caller's chosen Python environment or optional harness-local `pip --target`.
- Keep generated harnesses from mutating system Python, user site-packages, or project environments automatically.

**Non-Goals:**

- Provide a fully offline, source-bundled dependency fallback.
- Auto-discover and execute arbitrary uv internals from generated harness scripts.
- Force every generated harness to use every library.
- Replace generated harness code with a Houmao core harness runtime.

## Decisions

### Add harness libraries to Houmao runtime dependencies

Add `jinja2` and `jsonschema` to `pyproject.toml` project dependencies. Keep `click` as the existing command-routing dependency.

This means `uv tool install houmao` or `uv tool install --force --editable .` installs the common harness libraries into the same uv-managed environment as the Houmao command-line tools. Generated harnesses can then tell operators to run through the Houmao uv environment when their current Python interpreter lacks those libraries.

Alternative considered: keep wheel files under the v5 skill. Rejected because it increases source size and requires platform-specific wheel refreshes for compiled dependencies.

### Prefer normal imports plus explicit import-failure guidance

Generated harness code should import `click`, `jinja2`, and `jsonschema` only when it uses the corresponding feature. If an import fails, the generated entrypoint should print a concise guide that names the missing package and gives two recovery paths:

- install the package into the Python environment being used to run the harness; or
- run the harness with the Python environment associated with the installed Houmao uv tool.

The guide should also point users to inspect the Houmao tool environment with commands such as `uv tool list --show-paths --show-python` and to refresh the tool install when needed. Generated scripts should not assume one fixed uv tool directory layout.

Alternative considered: generated harnesses silently search uv tool directories and inject the uv environment onto `sys.path`. Rejected because uv internals and tool environment paths are not a stable harness contract, and implicit path injection can hide which interpreter is actually executing the harness.

### Test generated harnesses through the Houmao uv environment when local interpreter tests fail

Agents authoring generated harnesses should run a basic harness test after generation. If that test fails because imports are missing, the active interpreter differs from the intended runtime, or dependency posture is otherwise ambiguous, the skill should tell the agent to retry the same test through the Houmao uv-installed environment before changing harness logic.

This distinguishes real harness bugs from "wrong Python environment" failures. The authoring guidance should still avoid hardcoding uv internals; it can point the agent to `uv tool list --show-paths --show-python`, a refreshed `uv tool install`/editable install, or a maintained Houmao runner when one exists.

Alternative considered: treat all local harness test failures as code failures. Rejected because dependency/interpreter mismatches are expected when generated harness code is tested outside the Houmao-installed environment.

### Keep local pip target as optional standalone support

If a loop needs a standalone harness execution path independent of Houmao's uv-managed environment, the generated harness may still provide `execplan/harness/requirements.txt` and a local install command:

```bash
python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt
```

When this posture is selected, generated entrypoints still need a local `vendor/` `sys.path` bootstrap. This is a standalone/custom fallback, not the default offline fallback, and it depends on the caller having package-index or cache access.

Alternative considered: remove `pip --target` guidance entirely. Rejected because some generated loops may be copied away from a Houmao environment or intentionally run with a custom Python interpreter.

### Remove the skill-bundled wheelhouse

Delete `assets/harness-wheelhouse/` from the v5 skill. Remove wheelhouse references from authoring guidance, validation guidance, design notes, and top-level routing. Generated harness metadata should no longer record a `local-wheelhouse-target` posture or claim that the skill ships offline wheel assets.

Alternative considered: keep wheelhouse files as a last-resort fallback even after adding runtime dependencies. Rejected because that preserves the maintenance burden this change is meant to remove.

## Risks / Trade-offs

- [User runs harness with arbitrary Python] -> The harness import-failure guide explains how to install dependencies into that Python or use the Houmao uv environment.
- [Agent tests harness with the wrong interpreter] -> The skill tells the agent to retry through the Houmao uv environment before rewriting generated harness code.
- [Network unavailable and current Python lacks packages] -> Without bundled wheels, the user must use an environment where the packages are already installed, such as the uv-installed Houmao environment.
- [Houmao package dependencies grow] -> The added dependencies are general-purpose harness support libraries and are already common in Python packaging; this is smaller operationally than maintaining source-bundled wheel files.
- [uv tool environment path varies] -> Guidance uses uv inspection commands rather than hardcoding paths.
- [Existing generated harness docs mention wheelhouse fallback] -> Update skill guidance and validation to report such references as stale for newly generated execplans.

## Migration Plan

1. Add `jinja2` and `jsonschema` to project runtime dependencies.
2. Remove `assets/harness-wheelhouse/` from the v5 skill package.
3. Revise `execplan-harness` to replace wheelhouse fallback guidance with import-failure guidance, Houmao-uv retry guidance for failed harness tests, and optional local `pip --target`.
4. Revise `validate-execplan` to reject skill-bundled wheelhouse claims and check for import-failure guidance when non-stdlib harness imports are used.
5. Update top-level skill text, `agents/openai.yaml`, and developer design docs.
6. Validate the skill package and run a smoke import check using the project environment.

Rollback is to restore wheelhouse assets and wheelhouse fallback guidance, but that reintroduces platform-specific bundled files.

## Open Questions

- Whether Houmao should later provide a first-class CLI wrapper for running generated harness commands inside the installed Houmao environment. This proposal only requires guidance and dependency availability, not a new runner.
