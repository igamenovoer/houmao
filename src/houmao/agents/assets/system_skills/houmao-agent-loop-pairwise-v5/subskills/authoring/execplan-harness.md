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

Generate or update `execplan/harness/` for loop-local:
- validation, lookup, rendering, query, completion checks, and explanation;
- communication schema/render/lifecycle helpers;
- record schema/validate/apply/query helpers;
- structured command output for agent use.

Use this package shape when a harness is generated:

```text
<loop-dir>/execplan/harness/
  README.md
  commands.toml
  dependency-posture.toml        # only when non-stdlib imports exist
  requirements.txt               # optional standalone/custom execution
  schemas/
    command-envelope.schema.json
  refs/
    <relative symlinks to package artifacts>
  bin/
    <command-wrapper>
  src/
    <implementation files>
  vendor/                        # optional pip --target support
```

File rules:
- `commands.toml` is the command registry.
- `dependency-posture.toml` records non-stdlib dependency posture.
- `requirements.txt` and `vendor/` are only for standalone/custom execution outside the Houmao environment.
- `bin/` and `src/` may be omitted only for an explicit no-code or external harness.
- Do not leave command definitions only as loose prose in `execplan/docs/`.

## Package References

- Treat `<loop-dir>/execplan/` as the generated loop-definition package.
- Refer to package artifacts by relative path from `execplan/harness/`.
- Use direct paths by default:
  - `../specs/comms/templates.toml`
  - `../specs/comms/schemas/<message-family>.schema.json`
  - `../specs/collab/records/<record-family>.schema.json`
  - `../specs/state/state-model.toml`
  - `../specs/workspace/workspace.toml`
  - `../agents/bindings.toml`
- If stable local names help, create relative symlinks under `harness/refs/`.
- If symlinks are blocked, use direct relative paths. Do not copy authoritative artifacts.
- Use `harness/schemas/` only for schemas owned by the harness itself, such as the command envelope schema.
- Avoid absolute paths unless a generated contract defines an external runtime path.

Example:

```text
harness/refs/comms-templates.toml -> ../../specs/comms/templates.toml
```

## Python Dependencies

Use only the libraries needed by generated features:

| Feature | Library |
| --- | --- |
| CLI command groups | `click` |
| `.md.j2` rendering | `jinja2` |
| JSON Schema validation | `jsonschema` |

Defaults:
- Treat these as normal Houmao runtime dependencies.
- Do not ask whether they are allowed when a feature needs them.
- Ask only for stricter version, platform, or deployment constraints.

Dependency posture values:
- `houmao-env`: use the Houmao uv-installed environment.
- `environment-provided`: intended interpreter imports required libraries.
- `local-pip-target`: optional standalone `vendor/` support.
- `pending-local-install`: standalone target is documented but not installed.
- `unavailable`: no usable interpreter or install path is available.

Record posture in `dependency-posture.toml`, `README.md`, `manifest.toml`, or an equivalent indexed artifact.

### Import Check

Check the intended harness interpreter first:

```bash
<python> -c "import click, jinja2, jsonschema"
```

If the intended interpreter is unknown:
- check the current interpreter as weak evidence;
- inspect project dependency declarations as evidence only;
- record that the target interpreter is unresolved.

### Import Failure

Generated entrypoints that import non-stdlib libraries must fail with a short guide:
- name the missing package;
- suggest installing it into the active harness Python environment;
- suggest running or retesting with the Houmao uv-installed environment;
- never hardcode uv tool environment paths.

Useful commands to include:

```bash
uv tool list --show-paths --show-python
uv tool install --force houmao
uv tool install --force --editable .
```

Example helper:

```python
def _missing_harness_dependency(package: str) -> SystemExit:
    message = f"""
Missing generated harness dependency: {package}

Options:
- install it into the Python environment running this harness
- run or retest with the Python environment associated with the installed Houmao uv tool

Helpful checks:
- uv tool list --show-paths --show-python
- uv tool install --force houmao
"""
    raise SystemExit(message.strip())
```

### Authoring Test

- Run a basic harness test or self-check when generated commands provide one.
- If the test fails due to missing libraries, wrong interpreter, or unclear dependency posture, retry through the Houmao uv-installed environment before rewriting harness logic.
- If it still fails there, inspect harness code, command registry, paths, schemas, and inputs.

### Optional Standalone Target

Use this only when the loop intentionally supports running the harness outside the Houmao-installed environment.

`requirements.txt`:

```text
click>=8.1,<9
jinja2>=3.1,<4
jsonschema>=4.0,<5
```

Install:

```bash
python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt
```

Bootstrap before local-package imports:

```python
from pathlib import Path
import sys

_VENDOR = Path(__file__).resolve().parents[1] / "vendor"
if _VENDOR.exists():
    sys.path.insert(0, str(_VENDOR))
```

Rules:
- Include only required libraries.
- Keep `vendor/` local to the generated harness.
- Do not install into system Python, user site-packages, or the surrounding project environment.
- Adjust `_VENDOR` if the entrypoint is not under `execplan/harness/bin/`.

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
