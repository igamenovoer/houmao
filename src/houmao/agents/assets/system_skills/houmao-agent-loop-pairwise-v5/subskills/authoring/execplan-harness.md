# Execplan Harness

## Preconditions

- Process and contract specs are current.
- The loop needs validation, dynamic lookup, rendering, query, completion, explanation, or controlled record application.

## Inputs

Require:
- `<loop-dir>`;
- generated process specs;
- generated contract specs that harness commands will read.

## Outputs

Generate or update `execplan/harness/` and harness-facing docs or references for:
- validation;
- objective and policy rendering;
- communication schema lookup, payload validation, rendering, lifecycle apply, and query;
- record schema lookup, validation, controlled apply, and query;
- state query and completion checks;
- structured explanation output when generated contracts provide explainable comments;
- structured machine-readable command envelopes.

Use this package shape when a harness is generated:

```text
<loop-dir>/execplan/harness/
  README.md
  commands.toml
  dependency-posture.toml
  requirements.txt
  schemas/
    command-envelope.schema.json
  refs/
    <relative symlinks to package artifacts>
  bin/
    <command-wrapper>
  src/
    <implementation files>
  vendor/
    <optional harness-local pip target packages>
```

`commands.toml` is the registry for generated harness commands. `dependency-posture.toml` is required when the harness imports non-stdlib libraries. `requirements.txt` and `vendor/` are optional standalone/custom execution support only. `bin/` and `src/` may be omitted only when the harness is a documented external or no-code surface, but the omission must be explicit. Do not leave command descriptions only as loose prose in `execplan/docs/`.

Path and schema rules:
- Treat `<loop-dir>/execplan/` as the generated loop-definition package.
- Harness config and command registries may refer to any generated artifact in that package by relative path.
- Prefer paths relative to `execplan/harness/`, such as `../specs/comms/templates.toml`, `../specs/comms/schemas/<message-family>.schema.json`, `../specs/collab/records/<record-family>.schema.json`, `../specs/state/state-model.toml`, `../specs/workspace/workspace.toml`, or `../agents/bindings.toml`.
- When harness scripts need stable local paths, create relative symlinks under `execplan/harness/refs/` that point to authoritative artifacts elsewhere in the package.
- Symlink targets must be relative, not absolute. For example, `execplan/harness/refs/comms-templates.toml` can point to `../../specs/comms/templates.toml`.
- If symlink creation is unavailable or blocked by filesystem permissions, do not copy the artifact. Have the harness script or `commands.toml` use the direct relative path to the authoritative artifact instead.
- Use `harness/schemas/` only for schemas owned by the harness itself, such as the command envelope schema.
- Do not copy communication, record, state, workspace, participant, or objective schemas into `harness/`; reference the authoritative files under `specs/` or other package directories.
- Avoid absolute paths for generated package references unless a generated contract explicitly defines an external runtime path.

Harness library policy:
- Use `click` when the generated harness needs modular CLI command registration or grouped subcommands.
- Use `jinja2` when the generated harness renders `.md.j2` Markdown templates.
- Use `jsonschema` when the generated harness validates communication payloads, record payloads, command envelopes, or generated schemas.
- Generate dependencies only for libraries the harness actually imports.
- Do not ask the user whether these common harness libraries are allowed when the generated features need them; ask only for stricter versioning, platform, or deployment constraints.
- Treat these libraries as normal Houmao runtime dependencies. A user who installed Houmao with `uv` should have them in the Houmao uv-installed environment.

Dependency detection:
- Identify the intended harness interpreter first, when known from the loop, workspace, or operator direction.
- Check importability through the intended harness interpreter with a command such as:

```bash
<python> -c "import click, jinja2, jsonschema"
```

- If the intended interpreter is unknown, check the current interpreter as a weak fallback signal and record that the target interpreter is unresolved.
- Inspect applicable project dependency declarations such as `pyproject.toml`, lock files, or environment docs, but treat declarations as evidence only; importability through the intended interpreter is the proof for that interpreter.
- If every required library is importable through the intended harness interpreter, record dependency posture as `environment-provided` or an equivalent value.
- If the active interpreter cannot import required libraries, generated harness entrypoints must fail with an actionable guide that names the missing dependency and gives both recovery paths:
  - install the dependency into the Python environment used to run the harness;
  - run or retest the harness with the Python environment associated with the installed Houmao uv tool.
- Do not hardcode uv tool environment paths. Point the caller to inspection or refresh commands such as:

```bash
uv tool list --show-paths --show-python
uv tool install --force houmao
```

- For editable development installs, mention the project-supported command when applicable:

```bash
uv tool install --force --editable .
```

- Record dependency posture, required packages, interpreter evidence, and import-failure guidance in `dependency-posture.toml`, `README.md`, `manifest.toml`, or an equivalent indexed artifact.

Import-failure helper:
- Generated entrypoints may use a small helper around optional non-stdlib imports. Keep the message short, actionable, and specific to the missing library.

```python
def _missing_harness_dependency(package: str) -> SystemExit:
    message = f"""
Missing generated harness dependency: {package}

Use a Python environment that provides this package. Options:
- install it into the Python environment running this harness;
- run or retest the harness with the Python environment associated with the installed Houmao uv tool.

Helpful checks:
- uv tool list --show-paths --show-python
- uv tool install --force houmao
"""
    raise SystemExit(message.strip())
```

Authoring test rule:
- After generating harness implementation files, run a basic harness test or self-check when the generated command surface provides one.
- If the test fails because required harness libraries are missing, the active interpreter appears different from the intended runtime, or dependency posture is ambiguous, retry the same test through the Houmao uv-installed environment before rewriting harness logic.
- Treat a repeated failure under the intended Houmao uv environment as a harness implementation or contract problem and inspect the generated code, command registry, paths, schemas, and inputs.

Optional standalone local pip target:
- Use `execplan/harness/vendor/` only when the generated loop intentionally supports running the harness outside the Houmao-installed environment.
- Generate `execplan/harness/requirements.txt` with only required libraries. Broad compatible ranges are acceptable:

```text
click>=8.1,<9
jinja2>=3.1,<4
jsonschema>=4.0,<5
```

- Document the local target install command only as caller-managed standalone support:

```bash
python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt
```

- Record dependency posture as `houmao-env`, `environment-provided`, `local-pip-target`, `pending-local-install`, `unavailable`, or an equivalent explicit value.
- Record the interpreter used for detection or installation, required packages, version constraints, install command when local target support exists, and any diagnostics in `dependency-posture.toml`, `README.md`, `manifest.toml`, or an equivalent indexed artifact.
- Do not install into system Python, user site-packages, or the surrounding project environment.

Local import bootstrap:
- When optional standalone `vendor/` support may be used, place the bootstrap before imports of locally installed packages in each generated entrypoint:

```python
from pathlib import Path
import sys

_VENDOR = Path(__file__).resolve().parents[1] / "vendor"
if _VENDOR.exists():
    sys.path.insert(0, str(_VENDOR))
```

- Adjust the parent calculation if the entrypoint is not under `execplan/harness/bin/`, but keep the bootstrap local to the generated harness.

## Actions

1. Generate harness surfaces from generated contracts only.
2. Keep output intended for agents machine-readable where practical.
3. Use a common envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or document an equivalent.
4. Make command definitions declare the artifact paths they read, validate, render, query, or apply, including whether each path is a harness-local relative symlink or a direct relative path to another package artifact.
5. Keep apply commands narrow and schema-validated.
6. Document any harness commands generated skills are expected to call.
7. Document the harness dependency posture and recovery guidance whenever generated harness code imports non-stdlib libraries.

## Downstream Effects

- Changes here invalidate generated skills, agent bindings that install harness helper skills, final docs, and final manifest.

## Constraints

- Do not make the harness own mailbox delivery, gateway discovery, managed-agent lifecycle, memory management, or workspace creation.
- Do not invent process or contract semantics that are absent from upstream specs.
- Do not rely on ad hoc undeclared imports for `click`, `jinja2`, `jsonschema`, or their dependencies.
- Do not claim a packaged offline wheel bundle exists for generated harness dependencies.
