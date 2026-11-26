# Spec Delta

## ADDED Requirements

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
