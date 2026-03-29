## MODIFIED Requirements

### Requirement: User-facing source directories

When the system consumes a filesystem-backed reusable agent-definition source tree, it SHALL organize that source under a stable on-disk layout rooted at `agents/`.

At minimum, that filesystem-backed source layout SHALL include:

- `agents/skills/<skill>/SKILL.md`
- `agents/roles/<role>/system-prompt.md`
- `agents/roles/<role>/presets/<tool>/<setup>.yaml`
- `agents/tools/<tool>/adapter.yaml`
- `agents/tools/<tool>/setups/<setup>/...`
- `agents/tools/<tool>/auth/<auth>/...`

Project-local catalog-backed overlays MAY persist canonical semantic relationships outside that directory layout, provided they still resolve to the same canonical parsed or domain semantics before construction.

User-facing reusable launch metadata for filesystem-backed trees SHALL continue to live in role-scoped presets plus tool-scoped setup and auth directories rather than in a separate recipe plus blueprint layer.

#### Scenario: Developer locates source files in a filesystem-backed source tree

- **WHEN** a developer needs to add or modify reusable agent-definition sources in a filesystem-backed tree
- **THEN** skill packages SHALL live under `agents/skills/`
- **AND THEN** role prompts SHALL live under `agents/roles/`
- **AND THEN** launchable preset files SHALL live under `agents/roles/<role>/presets/`
- **AND THEN** tool-specific setup and auth material SHALL live under `agents/tools/<tool>/`

#### Scenario: Project-local catalog-backed overlay does not need filesystem nesting as its canonical graph

- **WHEN** a project-local overlay stores its canonical semantic relationships in a catalog-backed format
- **THEN** the system MAY keep large payloads file-backed without requiring `agents/roles/...` and `agents/tools/...` nesting to remain the authoritative semantic graph
- **AND THEN** project-aware construction still resolves the same canonical role, preset, setup, auth, skill, launch, mailbox, and `extra` semantics before downstream use

### Requirement: Source parsing yields a canonical agent catalog

The system SHALL resolve reusable agent-definition inputs into one canonical parsed or domain catalog before selector resolution or brain construction.

That canonical parsed or domain catalog SHALL capture semantic agent-definition data independently of source-layout-specific field names, file layering, or whether the project-local source originated from:

- a filesystem-backed `agents/` source tree, or
- a project-local catalog-backed overlay plus managed content references.

Downstream selector resolution, brain construction, and launch code SHALL consume only canonical parsed definitions or derived resolved launch and build specifications and SHALL NOT depend directly on raw preset-source mappings, legacy recipe files, legacy blueprint files, or project-local directory nesting as the authoritative semantic graph.

#### Scenario: Selector resolution uses the canonical catalog regardless of source backing

- **WHEN** a launch selector is resolved
- **THEN** resolution SHALL operate on the canonical parsed or domain catalog
- **AND THEN** downstream launch and build code SHALL NOT need to inspect raw source files or raw project-local catalog tables directly

#### Scenario: Future storage revisions preserve downstream contracts

- **WHEN** a future storage backend preserves the same role, tool, setup, auth, launch, mailbox, and `extra` semantics
- **THEN** downstream build and launch components SHALL continue to consume the same canonical parsed/domain contract without storage-specific changes
