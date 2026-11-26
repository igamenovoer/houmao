# houmao-system-skill-static-collection Specification

## Purpose
Publish six standalone system skills as static, host-discoverable assets. Shared routines own sixteen parent-scoped children, and installation projects the existing trees intact.
## Requirements
### Requirement: System skills are distributed as six static standalone roots
Houmao SHALL package exactly these current host-discoverable system-skill roots beneath `src/houmao/agents/assets/system_skills/public/`: `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Each root SHALL contain `SKILL.md` and all locally owned runtime resources. The checked-in directory SHALL be the same instruction tree installed into a tool home, apart from the projection mechanism itself.

#### Scenario: Maintainer inspects the static source collection
- **WHEN** a maintainer enumerates standalone entrypoints beneath the public source root
- **THEN** exactly six `SKILL.md` roots are found
- **AND THEN** each root can be validated without running a composer

### Requirement: Runtime installation does not compose skill content
The system SHALL NOT generate Markdown, render source placeholders, select an audience-specific route file, filter child routines, mount one skill below another, or otherwise synthesize a skill directory during installation.

Static staging SHALL copy complete source directories byte for byte or create direct symlinks to complete source directories. Validation MAY inspect staged content but SHALL NOT rewrite it.

#### Scenario: Admin pack is staged in copy mode
- **WHEN** the installer stages the admin pack
- **THEN** each selected destination tree is byte-identical to its corresponding public source directory
- **AND THEN** no local subskill tree is generated beneath `houmao-admin-entrypoint`

#### Scenario: Agent pack is staged in symlink mode
- **WHEN** the installer stages the agent pack using explicit symlink mode
- **THEN** each selected top-level destination links directly to its complete public source directory
- **AND THEN** no materialized composition directory is created

### Requirement: Static roots declare sibling dependencies without pretending to own them
Actor entrypoints SHALL declare `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` as sibling routes where applicable. They SHALL NOT link to those skills through paths relative to their own directory.

Every local Markdown link in a standalone skill SHALL resolve within that skill. Every cross-skill dependency SHALL use an explicit skill invocation or documented sibling name.

#### Scenario: Admin entrypoint source is validated by itself
- **WHEN** validation checks local files referenced by `houmao-admin-entrypoint/SKILL.md`
- **THEN** every local file exists beneath `houmao-admin-entrypoint`
- **AND THEN** shared and loop delegation appears as sibling skill invocation rather than a nonexistent local `subskills/` path

### Requirement: Static public collection supports Skills CLI discovery
The public source root SHALL be usable as a standard Agent Skills collection. Exact-`SKILL.md` discovery SHALL expose exactly the six standalone skill names, and the repository documentation SHALL provide explicit all, admin, and agent selection examples.

The documentation SHALL NOT claim that Skills CLI resolves Houmao pack dependencies automatically. Explicit admin selection SHALL include five roots, and explicit agent selection SHALL include four roots.

#### Scenario: User lists the public collection with Skills CLI
- **WHEN** a user asks Skills CLI to list or select skills from the public source root
- **THEN** the result contains exactly the six standalone Houmao skill names
- **AND THEN** no shared child logical id is offered as an independent skill

#### Scenario: User installs the admin surface explicitly
- **WHEN** a user follows the documented Skills CLI admin installation
- **THEN** the selection names admin welcome, admin entrypoint, shared routines, pro loop, and lite loop
- **AND THEN** the installed entrypoint has every required sibling available

### Requirement: Shared routines own the declared parent-scoped children
The packaged manifest SHALL declare the current shared child inventory. The directories directly under `houmao-shared-routines/subskills/` SHALL match that inventory exactly. The current inventory SHALL contain eighteen children, including `houmao-agent-access` and `houmao-agent-files`. Each child SHALL own a `SKILL-MAIN.md` entrypoint.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Each direct child SHALL contain only its role-canonical entrypoint filename. The Pro and Lite loop skills SHALL be public siblings outside the shared tree.

#### Scenario: Current shared tree matches its declaration
- **WHEN** Houmao validates the current shared source tree
- **THEN** the exact child directories match the manifest
- **AND THEN** the retained shared routines and both new children are present

#### Scenario: Exact entrypoint scanner traverses shared routines
- **WHEN** a recursive scanner registers only exact `SKILL.md` filenames
- **THEN** it registers `houmao-shared-routines` as one standalone skill
- **AND THEN** the scan returns only that root for the complete shared tree
### Requirement: Static manifest synchronizes command and alias declarations with packaged skill pages
The `manifest.toml` (`houmao-system-skills.v5`) catalog SHALL synchronize `commands` and `aliases` declarations across all six standalone skills and eighteen shared routines, using explicit `alias=canonical` pairs so every object designator and command page resolves cleanly.

#### Scenario: Messaging and mailbox manifest entries match packaged command files
- **WHEN** `manifest.toml` is validated against `src/houmao/agents/assets/system_skills/public/`
- **THEN** `houmao-agent-messaging.commands` includes `"request"` matching `commands/request.md`, and `houmao-agent-definition` retains its 13 canonical `SKILL-MAIN.md` `commands` with `aliases` mapping `authoring`, `deployment`, `batch`, `launch-instance`, and `stop-instance`
- **AND THEN** `houmao-adv-usage-pattern` retains its 5 canonical `commands` with `aliases` mapping `local-close-edge-loop`, `pairwise edge-loop`, `pairwise-edge-loop-via-gateway-and-mailbox`, `relay-loop-via-gateway-and-mailbox`, `self-notification-via-reminders`, and `self-wakeup-via-self-mail`, while `houmao-mailbox-mgr` lists all 17 executable commands (including `clear-messages`, `accounts-*`, `messages-*`, and `agent-binding-online`) in `commands` with `aliases = ["mailbox-online=agent-binding-online"]`

### Requirement: Legacy loop directories and digests remain frozen migration fixtures
All six directories under `src/houmao/agents/assets/system_skills/legacy/`, `legacy/catalog.v1.toml` (20 entries), and all twenty-six historical v1 `[[legacy_skills]]` SHA-256 `content_digest` entries (`adbdf84e`) in `manifest.toml` SHALL remain completely unmodified, with zero new, split, merged, or retired skills.

#### Scenario: Legacy SHA-256 content digests stay intact across post-3.0.0 updates
- **WHEN** the post-3.0.0 skill updates are applied to `public/` and `manifest.toml`
- **THEN** zero bytes are modified inside `legacy/houmao-agent-loop-{generic,pairwise,pairwise-v2,pairwise-v3,pairwise-v4,pairwise-v5}`, `legacy/catalog.v1.toml`, or the 26 `[[legacy_skills]]` entries in `manifest.toml`
- **AND THEN** `system_skill_lifecycle.py` continues resolving symlinked legacy paths under `legacy/*` and matching copied legacy installations against the 26 historical `content_digest` entries while new loop behavior lives in `houmao-agent-loop-pro` and `houmao-agent-loop-lite`

### Requirement: Static collection enforces Imsight structural conformance and link containment
Every skill under `public/` SHALL preserve `metadata.houmao_version` on the six standalone `SKILL.md` roots, exact `metadata.skill_invocation_notation` on entrypoints and designator-bearing pages, intra-owner relative Markdown links, `## Actor Frame Gate` on all eighteen `SKILL-MAIN.md` children, and `imsight-agent-skill-handling` formatting.

#### Scenario: Automated manifest and version checks pass after structural refactoring
- **WHEN** cross-skill boilerplate is stripped locally without cross-subskill relative links and monolithic entrypoints are decomposed into `commands/` and `references/`
- **THEN** `load_system_skill_manifest()`, `check_system_skill_versions.py`, `tests/unit/agents/test_system_skill*`, `tests/unit/srv_ctrl/test_system_skill*`, and `tests/unit/docs/test_system_skills_docs.py` pass with zero escaping links or undeclared designators
