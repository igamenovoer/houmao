## Context

The v5 skill now has a shared scaffold generator and packaged assets, but generated harness implementation guidance still assumes the target Python environment can satisfy any libraries the harness chooses to import. The mature reference loop uses a good pattern for generated communication and harness behavior: `.md.j2` renderers under `specs/comms/renderers/`, JSON Schema validation, and a modular command surface. That pattern is worth teaching, but target loop environments are not controlled beyond Python 3.11+ and may not allow global or project-level package installation.

The desired dependency set for this pattern is:
- `jinja2` for Markdown renderer execution;
- `click` for modular harness CLI command registration;
- `jsonschema` for communication and record payload validation.

The normal fallback is a harness-local `pip --target` install under `execplan/harness/vendor/` when environment detection cannot prove the packages are already available. The final fallback is a skill-bundled wheelhouse: `.whl` files for the supported libraries and their required dependencies, installed with `pip --no-index --find-links` when network or package indexes are unavailable.

## Goals / Non-Goals

**Goals:**
- Teach `execplan-harness` to use `jinja2`, `click`, and `jsonschema` as the preferred libraries for generated harnesses when those features are needed.
- Detect whether the intended harness environment already provides required libraries before installing local copies.
- Generate `execplan/harness/requirements.txt` for harness-local dependencies.
- Install missing or uncertain dependencies into `execplan/harness/vendor/` with `python -m pip install --target`.
- Package an offline wheelhouse in the v5 skill for `jinja2`, `click`, `jsonschema`, and required dependencies.
- Teach generated harnesses to use the wheelhouse as the final fallback for local target installs.
- Bootstrap `execplan/harness/vendor/` locally in generated harness entrypoints.
- Make dependency posture explicit in generated harness docs, manifest entries, and validation notes.

**Non-Goals:**
- Install packages into system Python, user site-packages, or the project environment.
- Vendor package source into the v5 skill package instead of wheels.
- Require every generated harness to use all three libraries; only generate requirements for libraries the harness actually uses.
- Guarantee offline installation for platforms not covered by the bundled pure-Python wheels.
- Replace generated harness code with a maintained Houmao runtime package.

## Decisions

### Use local pip target installation as the normal fallback dependency posture

When required libraries are missing or uncertain, generated harnesses should install into:

```text
<loop-dir>/execplan/harness/vendor/
```

using a command shape like:

```bash
python -m pip install --target <loop-dir>/execplan/harness/vendor -r <loop-dir>/execplan/harness/requirements.txt
```

This avoids global permissions and keeps dependency files inside the generated loop package. The generated harness should record `dependency_posture = "local-pip-target"` or an equivalent manifest field.

Alternative considered: package vendored library source inside the v5 skill and copy it into every generated harness. Rejected because package source vendoring creates more import and license maintenance than wheel-based offline installation. Wheels keep Python packaging metadata intact and can still be installed into `execplan/harness/vendor/`.

### Provide a skill-bundled wheelhouse as final offline fallback

The v5 skill should package `.whl` files under a dedicated asset directory, for example:

```text
assets/harness-wheelhouse/
  WHEELHOUSE.md
  wheels/
    click-...
    jinja2-...
    jsonschema-...
    markupsafe-...
    attrs-...
    jsonschema_specifications-...
    referencing-...
    rpds_py-...
```

The exact wheel list should be generated from pinned or bounded requirements for `click`, `jinja2`, and `jsonschema` and include required transitive dependencies. The wheelhouse manifest should record package names, versions, filenames, source index or download URL, license name when known, and refresh instructions.

When normal network/cache install fails or is known unavailable, `execplan-harness` should copy or reference the wheelhouse and use a command shape like:

```bash
python -m pip install \
  --no-index \
  --find-links <wheelhouse-dir> \
  --target <loop-dir>/execplan/harness/vendor \
  -r <loop-dir>/execplan/harness/requirements.txt
```

The generated harness should record `dependency_posture = "local-wheelhouse-target"` or equivalent when this path is used.

Alternative considered: always install from bundled wheels even when network is available. Rejected because environment packages and normal pip resolution may be newer or already managed; the wheelhouse is a reliability fallback, not the primary dependency source.

### Detect environment support before local installation

`execplan-harness` should tell the invoking agent to check dependency availability before generating local install steps. Detection should include:
- the Python interpreter that will run the harness, when known;
- the current agent Python interpreter as a fallback signal;
- project declarations such as `pyproject.toml` when present.

Importability through the intended harness interpreter is proof. Project declarations are only evidence; if the harness execution environment is unclear, the generated plan should choose local pip target installation or record an unresolved dependency decision.

Alternative considered: always install to `execplan/harness/vendor/` for determinism. Rejected because it duplicates packages in environments that already provide them and can require network unnecessarily.

### Generate a minimal requirements file from used harness features

Generated harnesses should include only the libraries they use. Typical mappings are:
- `.md.j2` renderer support -> `jinja2`
- modular CLI command registration -> `click`
- JSON Schema validation -> `jsonschema`

The generated `requirements.txt` should use bounded version ranges by default, for example:

```text
click>=8.1,<9
jinja2>=3.1,<4
jsonschema>=4.0,<5
```

Generated plans may pin more tightly when reproducibility matters, but broad compatible ranges are acceptable for generic loops unless the user requests a locked environment.

When using the bundled offline wheelhouse, requirements should be compatible with wheelhouse contents. If the generated harness chooses stricter pins outside the wheelhouse, it must not claim the bundled wheelhouse is sufficient.

Alternative considered: one fixed requirements file for every harness. Rejected because lightweight harnesses should not pay for unused dependencies.

### Bootstrap local target imports inside generated harnesses

Generated harness entrypoints that use `local-pip-target` or `local-wheelhouse-target` posture should prepend the local vendor directory before imports:

```python
from pathlib import Path
import sys

_VENDOR = Path(__file__).resolve().parent / "vendor"
if _VENDOR.exists():
    sys.path.insert(0, str(_VENDOR))
```

This bootstrap is local to the generated harness. It must not set global environment variables, write to user site-packages, or mutate project dependency files.

Alternative considered: require operators to activate a virtual environment. Rejected because the loop package should remain runnable when the user has no permission or desire to change the surrounding project environment.

### Treat local dependencies as harness implementation support

`execplan/harness/vendor/` is not authoritative loop policy. Generated specs remain under `execplan/specs/`, renderers remain under `execplan/specs/comms/renderers/`, and schemas remain under `execplan/specs/...`. The vendor directory only supports the harness implementation.

The generated manifest and harness README should list required libraries, selected posture, install command, interpreter used for detection/install, whether installation used network/cache or wheelhouse, and whether installation succeeded or remains pending.

Alternative considered: store dependency declarations under `specs/`. Rejected because dependency management belongs to harness implementation, not loop contracts.

## Risks / Trade-offs

- [Network unavailable] -> Fall back to the skill-bundled wheelhouse with `--no-index --find-links`.
- [Pip unavailable] -> Record dependency posture as `unavailable` or `pending-local-install`, include the exact failed command and diagnostics, and avoid pretending the harness is executable.
- [Version drift] -> Generate bounded requirements by default and allow tighter pins or constraints when the loop requires reproducibility.
- [Wheelhouse drift] -> Maintain a wheelhouse manifest with package versions, filenames, provenance, and refresh instructions.
- [Environment detection false positives] -> Treat `pyproject.toml` as weak evidence unless the intended harness interpreter can import the packages.
- [Generated artifacts become larger] -> Install locally only when needed and only for used libraries.
- [Package conflicts] -> Prepend `vendor/` only when local-pip-target posture is selected; prefer environment packages when they are already importable.

## Migration Plan

1. Add a skill-bundled wheelhouse asset and wheelhouse manifest for `jinja2`, `click`, `jsonschema`, and required dependencies.
2. Update `execplan-harness` guidance to require dependency detection and recorded posture.
3. Update harness guidance to generate `requirements.txt`, normal local pip target install commands, final wheelhouse fallback commands, and local import bootstrap when needed.
4. Update validation and design docs to check dependency posture, requirements, vendor directory shape, wheelhouse metadata, bootstrap behavior, and install diagnostics.
5. Update the OpenSpec base requirement during archive so future v5 harness changes preserve this local dependency policy.
6. Verify the skill package and a small harness-local `pip --target` smoke case using the bundled wheelhouse when implementation applies the change.

Rollback is simple: restore guidance to require environment-provided dependencies only. Existing generated execplans with local `vendor/` directories can continue to work because those dependencies are loop-local artifacts.
