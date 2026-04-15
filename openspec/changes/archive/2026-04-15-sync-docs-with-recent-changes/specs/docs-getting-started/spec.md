## MODIFIED Requirements

### Requirement: Architecture overview explains two-phase lifecycle

The getting-started section SHALL include an architecture overview document that explains the two-phase lifecycle (build phase → run phase), the agent definition directory model, the backend abstraction, and the current operator-facing CLI surfaces. The content SHALL be derived from `brain_builder.py`, `realm_controller/`, and the current `houmao-mgr` and `houmao-server` command trees. The build-phase mermaid diagram SHALL reference the current manifest schema version (`schema_version=4`).

#### Scenario: Reader understands build-then-run flow

- **WHEN** a reader opens the architecture overview
- **THEN** they find a clear explanation of: (1) build phase producing a BrainManifest from a preset-backed build specification, (2) run phase composing manifest plus role into a LaunchPlan dispatched to a backend, and (3) `houmao-mgr` as the primary operator CLI for the supported workflow

#### Scenario: Manifest schema version is current

- **WHEN** the architecture overview mermaid diagram mentions a manifest schema version
- **THEN** the referenced version SHALL be `4`, matching `SESSION_MANIFEST_SCHEMA_VERSION` in `src/houmao/agents/realm_controller/manifest.py`

### Requirement: Loop authoring guide cross-references runnable examples

The loop authoring guide SHALL cross-reference the `examples/writer-team/` template as a concrete end-to-end pairwise loop example. The cross-reference SHALL appear near the skill-selection guidance so readers can see a working plan alongside the conceptual explanation.

#### Scenario: Reader discovers writer-team example from loop authoring guide

- **WHEN** a reader is on the loop authoring guide page
- **THEN** they find a visible cross-reference to `examples/writer-team/` with a brief description of what the example demonstrates
