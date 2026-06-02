## ADDED Requirements

### Requirement: Plain direct-dir fixture guidance SHALL stay aligned with scoped CLI and native-root terminology
Repository guidance inside `tests/fixtures/plain-agent-def/` SHALL describe that fixture as tracked, secret-free plain native-agent seed material for direct internals, copied temp roots, and project-overlay seeding.

That guidance SHALL use the current fixture-relative paths:

- `roles/<role>/system-prompt.md`
- `skills/<skill>/SKILL.md`
- `presets/<preset>.yaml`
- `launch-profiles/<profile>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`
- `tools/<tool>/auth/<auth>/...`

That guidance SHALL NOT describe stale `agents/roles`, `agents/skills`, retired `brains/`, or retired `blueprints/` paths as current locations in this fixture root.

That guidance SHALL NOT present root-level `houmao-mgr agents launch`, `houmao-mgr agents stop`, or `houmao-mgr agents cleanup` as maintained public command paths.

When fixture guidance needs to discuss managed-agent lifecycle, it SHALL distinguish:

- project-backed birth through `houmao-mgr project agents launch`,
- selected-agent follow-up through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`,
- current-session operations through `houmao-mgr agents self ...`,
- direct native-agent build plumbing through `houmao-mgr internals native-agent brain build`.

#### Scenario: Maintainer reads the plain fixture workflow guidance
- **WHEN** a maintainer reads `tests/fixtures/plain-agent-def/README.md` and `tests/fixtures/plain-agent-def/MIGRATION.md`
- **THEN** the guidance describes direct native-agent build usage through `houmao-mgr internals native-agent brain build`
- **AND THEN** it does not instruct the maintainer to launch with root-level `houmao-mgr agents launch`
- **AND THEN** it points public managed-agent birth to `houmao-mgr project agents launch` when a launch is needed

#### Scenario: Maintainer reads fixture role and skill guidance
- **WHEN** a maintainer reads `tests/fixtures/plain-agent-def/roles/README.md` and `tests/fixtures/plain-agent-def/skills/README.md`
- **THEN** the guidance uses fixture-relative `roles/` and `skills/` terminology
- **AND THEN** it does not present `agents/roles/` or `agents/skills/` as the current paths inside the plain fixture root

#### Scenario: Server API smoke role avoids retired server wording
- **WHEN** a maintainer inspects the `server-api-smoke` fixture role documentation and system prompt
- **THEN** the role is described in terms of maintained managed-agent API or passive-server smoke validation
- **AND THEN** it does not describe the maintained smoke target as retired standalone `houmao-server`
