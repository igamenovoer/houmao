## ADDED Requirements

### Requirement: V5 generated harnesses use Houmao-installed Python dependencies with import-failure guidance
The packaged v5 skill SHALL teach generated harnesses to use `click`, `jinja2`, and `jsonschema` as normal Python dependencies when generated harness features need modular command routing, Markdown template rendering, or JSON Schema validation.

The Houmao project SHALL declare `jinja2` and `jsonschema` as runtime dependencies so the uv-installed Houmao environment provides them. The existing `click` runtime dependency SHALL continue to satisfy modular CLI command-routing support.

Generated harnesses SHALL import only the non-stdlib libraries required by the features they implement.

When a generated harness entrypoint cannot import a required non-stdlib dependency, it SHALL fail with actionable guidance that names the missing dependency and tells the caller to either install the dependency into the Python environment used to run the harness or run the harness with the Python environment associated with the installed Houmao uv tool.

Generated harness import-failure guidance SHALL avoid hardcoding a uv tool environment path. It SHALL suggest inspection or refresh commands such as `uv tool list --show-paths --show-python` or reinstalling/updating the Houmao uv tool environment when appropriate.

The v5 harness authoring guidance SHALL tell agents to test generated harnesses after writing them. If a harness test fails because required harness libraries are missing, the active interpreter appears different from the intended runtime, or dependency posture is ambiguous, the agent SHALL retry the same harness test through the Houmao uv-installed environment before treating the failure as a harness implementation bug.

Generated harnesses MAY provide `execplan/harness/requirements.txt` and optional local `pip --target execplan/harness/vendor` instructions for standalone/custom execution, but the packaged v5 skill SHALL NOT require or ship a bundled wheelhouse for these dependencies.

The packaged v5 skill SHALL NOT include source-bundled `.whl` files for `click`, `jinja2`, `jsonschema`, or their transitive dependencies.

Validation guidance SHALL report generated v5 execplans as stale or non-conforming when they claim a skill-bundled wheelhouse fallback for these harness libraries.

#### Scenario: Houmao install provides common harness libraries
- **WHEN** Houmao is installed as a uv-managed tool from the project package
- **THEN** the installed environment includes `click`, `jinja2`, and `jsonschema`
- **AND THEN** generated harnesses can instruct users to use that Houmao environment when another Python interpreter lacks those libraries

#### Scenario: Harness import failure gives actionable recovery paths
- **WHEN** a generated harness imports a required non-stdlib library and that import fails
- **THEN** the harness reports the missing library by name
- **AND THEN** the message tells the caller to install the library into the active harness Python environment or use the Python environment associated with the installed Houmao uv tool

#### Scenario: Harness author retries failed tests through Houmao uv environment
- **WHEN** an agent tests a generated harness and the test fails because a required harness library is missing or the active interpreter appears to be the wrong runtime
- **THEN** the v5 skill guidance tells the agent to retry the same test through the Houmao uv-installed environment
- **AND THEN** the agent does not rewrite harness logic until distinguishing dependency environment failure from implementation failure

#### Scenario: Harness dependencies are feature-scoped
- **WHEN** a generated harness does not render `.md.j2` templates
- **THEN** it does not need to declare or import `jinja2`
- **AND WHEN** a generated harness does not validate JSON Schema payloads
- **THEN** it does not need to declare or import `jsonschema`

#### Scenario: Skill does not ship wheelhouse fallback
- **WHEN** the packaged v5 skill assets are inspected
- **THEN** they do not contain a bundled harness wheelhouse of `.whl` files for `click`, `jinja2`, `jsonschema`, or transitive dependencies
- **AND THEN** v5 harness guidance does not claim a skill-bundled wheelhouse fallback exists

#### Scenario: Optional standalone local target remains possible
- **WHEN** a generated loop intentionally supports running its harness outside the Houmao-installed environment
- **THEN** it may include `execplan/harness/requirements.txt` and a local `python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt` instruction
- **AND THEN** this local target path is documented as caller-managed standalone support, not as a skill-bundled offline fallback
