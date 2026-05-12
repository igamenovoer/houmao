## ADDED Requirements

### Requirement: V5 top-level skill entrypoint uses progressive-disclosure reference pages
The packaged `houmao-agent-loop-pairwise-v5` skill SHALL keep its top-level `SKILL.md` focused on activation, required loop root, source/generated-output invariants, supported operations, routing, and global constraints.

The top-level `SKILL.md` SHALL NOT carry the full detailed generated-contract defaults, bookkeeping model, TOML conventions, mail runtime model, scaffold profile details, generation-stage dependency model, or maintained-platform boundary guidance when that guidance can live in routed runtime reference pages.

The packaged skill SHALL include runtime-readable reference pages under the skill package for shared detailed guidance used by multiple routed subskills.

Runtime reference pages SHALL be outside `dev/design/`, because they are part of normal skill execution rather than maintainer-only design intent.

Runtime reference pages SHALL be organized by durable operational concern rather than by one-off implementation history.

Routed subskills that depend on shared detailed guidance SHALL include an explicit `Read first` section that lists the runtime reference pages they must read before acting.

Routed subskills SHALL avoid duplicating the detailed guidance owned by runtime reference pages unless a local operation-specific exception is needed.

The split SHALL preserve existing operation names, generated-loop behavior, scaffold profile semantics, runtime mail model, and maintained Houmao platform-boundary rules.

#### Scenario: Entry point routes without loading detailed defaults
- **WHEN** an invoking agent opens the top-level `houmao-agent-loop-pairwise-v5/SKILL.md`
- **THEN** it can determine whether the skill applies, which `<loop-dir>` invariant applies, and which routed page to read
- **AND THEN** it does not need to read full generated-contract, bookkeeping, TOML, mail-runtime, or platform-boundary defaults from the entrypoint itself

#### Scenario: Operation page declares shared references
- **WHEN** a routed authoring or execution page requires shared detailed guidance
- **THEN** the page includes a `Read first` section naming the required runtime reference pages
- **AND THEN** those links resolve within the packaged skill directory

#### Scenario: Runtime references are not maintainer-only docs
- **WHEN** shared guidance is needed during normal skill execution
- **THEN** it lives in runtime reference pages under the skill package
- **AND THEN** it is not available only through `dev/design/`

#### Scenario: Split preserves current behavior
- **WHEN** the top-level entrypoint is shortened and detailed guidance is moved into reference pages
- **THEN** existing v5 operations remain routed by the same operation names
- **AND THEN** generated artifact structure, scaffold profile meanings, mail-driven runtime semantics, and maintained Houmao platform boundaries remain unchanged
