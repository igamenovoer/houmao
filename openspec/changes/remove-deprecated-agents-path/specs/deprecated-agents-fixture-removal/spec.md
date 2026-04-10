## ADDED Requirements

### Requirement: Repository SHALL not retain the deprecated `tests/fixtures/agents/` path as a tracked fixture surface
The repository SHALL remove `tests/fixtures/agents/` from the tracked maintained tree instead of keeping it as a redirect, stub, compatibility alias, or partially populated fixture root.

Maintained docs, maintained specs, and runnable maintained repository surfaces SHALL point directly at the owning replacement lane:

- `tests/fixtures/plain-agent-def/` for plain direct-dir workflows,
- `tests/fixtures/auth-bundles/` for local-only credential bundles, or
- owned overlay-local or demo-local generated trees for maintained project-aware flows.

Historical archived artifacts MAY retain historical path strings as historical record, but the live maintained repository contract SHALL NOT present `tests/fixtures/agents/` as a usable path.

#### Scenario: Maintainer inspects the tracked fixture tree after removal
- **WHEN** a maintainer inspects the tracked `tests/fixtures/` tree after this change
- **THEN** the repository does not track `tests/fixtures/agents/` as a directory, redirect stub, or compatibility README
- **AND THEN** the maintained fixture guidance points directly at `tests/fixtures/plain-agent-def/`, `tests/fixtures/auth-bundles/`, or owned generated trees

#### Scenario: Maintained guidance does not reintroduce the deprecated path
- **WHEN** a maintainer reads live maintained docs, specs, or runnable maintained demo guidance after this change
- **THEN** those maintained surfaces do not instruct operators to use `tests/fixtures/agents/`
- **AND THEN** any archived surface that still depends on the removed path is treated as archived or guarded separately rather than presented as a maintained workflow
