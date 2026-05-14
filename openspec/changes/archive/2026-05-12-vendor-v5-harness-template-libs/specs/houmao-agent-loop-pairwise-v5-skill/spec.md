## ADDED Requirements

### Requirement: V5 generated harnesses manage local Python library dependencies
The `execplan-harness` authoring workflow SHALL teach agents to manage generated harness Python dependencies without requiring system-wide, user-site, or project-environment installation.

When a generated harness uses Jinja Markdown rendering, modular Click command routing, or JSON Schema validation, the generated harness SHALL declare the required Python libraries for those features.

The default supported library set SHALL include:
- `jinja2` for `.j2` Markdown rendering;
- `click` for modular CLI command registration;
- `jsonschema` for JSON Schema validation.

Generated harnesses SHALL record their dependency posture as environment-provided, local pip target, unavailable, or an explicitly documented equivalent.

The packaged `houmao-agent-loop-pairwise-v5` skill SHALL include an offline wheelhouse containing `.whl` files for `jinja2`, `click`, `jsonschema`, and required dependencies for use as the final local pip target fallback.

The packaged wheelhouse SHALL include metadata documenting wheel filenames, package versions, provenance, and refresh instructions.

#### Scenario: Harness declares libraries for used features
- **WHEN** a generated harness renders `.md.j2` files, validates JSON schemas, or uses a modular command CLI
- **THEN** it declares the corresponding libraries from `jinja2`, `jsonschema`, and `click`
- **AND THEN** it records the selected dependency posture for those libraries

#### Scenario: Harness dependency management avoids global installs
- **WHEN** a generated harness needs Python libraries that are not already available
- **THEN** the generated plan uses a harness-local dependency strategy
- **AND THEN** it does not require installing packages into system Python, user site-packages, or the project environment

#### Scenario: Skill includes offline wheelhouse fallback
- **WHEN** the packaged v5 skill is inspected
- **THEN** it includes `.whl` artifacts for `jinja2`, `click`, `jsonschema`, and required dependencies
- **AND THEN** it includes metadata for wheel versions, provenance, and refresh instructions

### Requirement: V5 harness generation detects libraries before local pip target installation
The `execplan-harness` authoring workflow SHALL teach agents to detect whether the intended harness Python environment already provides required libraries before generating local install steps.

Detection SHALL check the intended harness interpreter when known.

Detection SHALL check the current Python interpreter as a fallback signal when the intended harness interpreter is not known.

Detection SHALL inspect project dependency declarations such as `pyproject.toml` when present, while treating declarations as insufficient if they do not clearly apply to the harness runtime environment.

When required libraries are importable through the intended harness interpreter, the generated harness SHALL record an environment-provided dependency posture and SHALL NOT install those libraries into `execplan/harness/vendor/`.

When any required library is unavailable or the target dependency posture is uncertain, the generated harness SHALL generate a harness-local requirements file and local pip target install instructions.

The generated harness SHALL document the normal local pip target command and the final offline wheelhouse command using `python -m pip install --no-index --find-links <wheelhouse-dir> --target execplan/harness/vendor -r execplan/harness/requirements.txt` or an explicitly equivalent command.

#### Scenario: Intended interpreter provides required libraries
- **WHEN** `execplan-harness` determines that the intended harness interpreter can import all libraries required by the generated harness
- **THEN** the generated harness records environment-provided dependency posture
- **AND THEN** it does not install those packages into `execplan/harness/vendor/`

#### Scenario: Required library support is missing or uncertain
- **WHEN** `execplan-harness` cannot prove that the intended harness interpreter can import every required library
- **THEN** the generated harness includes `execplan/harness/requirements.txt`
- **AND THEN** it documents a `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt` local install step or an equivalent harness-local pip target command

#### Scenario: Network install is unavailable
- **WHEN** the generated harness needs local dependency installation and normal package-index access is unavailable
- **THEN** the generated harness can use the skill-bundled wheelhouse as the package source
- **AND THEN** it installs into `execplan/harness/vendor/` without writing to system Python, user site-packages, or the project environment

### Requirement: V5 generated harnesses bootstrap local pip target dependencies
When a generated harness uses local pip target dependency posture, the generated harness SHALL install or instruct installation of required libraries under `execplan/harness/vendor/` or an explicitly equivalent harness-local vendor root.

Generated harness entrypoints SHALL add the harness-local vendor root to `sys.path` before importing locally installed packages.

The local vendor bootstrap SHALL be local to the generated harness and SHALL NOT mutate global Python configuration.

The generated harness README, command registry, manifest, or equivalent metadata SHALL list required libraries, selected dependency posture, install command, interpreter used for detection or installation, wheelhouse source when used, and any install diagnostics.

The generated execplan manifest SHALL index `execplan/harness/requirements.txt` and the vendor directory or vendor metadata when local pip target posture is used.

Validation guidance SHALL report a generated harness as incomplete when it records local pip target posture or local wheelhouse target posture but lacks requirements metadata, local vendor bootstrap, or install diagnostics for a missing vendor directory.

#### Scenario: Local pip target harness imports work locally
- **WHEN** a generated harness selected local pip target dependency posture
- **THEN** its entrypoint prepends the harness-local vendor root to `sys.path` before importing locally installed libraries
- **AND THEN** running the harness does not require installing those packages into the global or project Python environment

#### Scenario: Local dependency metadata is indexed
- **WHEN** a generated harness includes `execplan/harness/requirements.txt` or `execplan/harness/vendor/`
- **THEN** generated harness metadata lists required package names, version constraints, install command, and dependency posture
- **AND THEN** the generated execplan manifest indexes the dependency artifacts or their metadata

#### Scenario: Wheelhouse dependency metadata is indexed
- **WHEN** a generated harness uses the offline wheelhouse fallback
- **THEN** generated harness metadata names the wheelhouse source and install command
- **AND THEN** the generated execplan manifest indexes copied wheelhouse metadata or records the skill-bundled wheelhouse reference
