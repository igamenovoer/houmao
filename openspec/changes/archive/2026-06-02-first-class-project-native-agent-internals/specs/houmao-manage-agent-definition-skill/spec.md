## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-definition` system skill
The system SHALL replace the old agent-definition skill guidance with packaged Houmao-owned guidance that separates project agent management from native-agent internals.

The canonical ordinary project guidance SHALL instruct agents to manage project-layer resources through:

- `houmao-mgr project specialist ...`
- `houmao-mgr project profile ...`
- project-scoped managed-agent lifecycle commands
- `houmao-mgr project credentials ...`
- `houmao-mgr project skills ...`

The canonical native-provider guidance SHALL instruct agents to use internal native-agent commands only when the user explicitly asks for provider-aligned native material, launch dossiers, recipes, roles, or direct native-agent root work:

- `houmao-mgr internals native-agent roles ...`
- `houmao-mgr internals native-agent recipes ...`
- `houmao-mgr internals native-agent launch-dossiers ...`
- `houmao-mgr internals native-agent tools ...`

The skill SHALL avoid using `agent definition`, `raw profile`, or `launch profile` as ordinary project terms. It SHALL define `native agent` and `launch dossier` as internal compatibility-layer terms.

The top-level skill guidance SHALL route ordinary user requests for reusable agent configuration to project specialists and project profiles unless the user explicitly asks for native-agent internals.

#### Scenario: Ordinary specialist request routes to project commands
- **WHEN** a user asks an agent to create a reusable Codex reviewer
- **THEN** the packaged guidance routes the agent to `houmao-mgr project specialist create`
- **AND THEN** it does not route the request to native-agent roles or recipes

#### Scenario: Native launch dossier request routes to internals
- **WHEN** a user explicitly asks for a native launch dossier
- **THEN** the packaged guidance routes the agent to `houmao-mgr internals native-agent launch-dossiers ...`
- **AND THEN** it treats the request as internal provider-aligned material rather than a project profile

## ADDED Requirements

### Requirement: System skills use the revised project/native vocabulary consistently
Packaged system skills that mention Houmao agent authoring or launch preparation SHALL use:

- `specialist` for reusable project-level persona/tool/credential definitions,
- `profile` for reusable project launch defaults,
- `managed agent` or `agent instance` for runtime identities,
- `native agent` for internal provider-aligned launch material,
- `launch dossier` for internal recipe-backed native launch defaults.

#### Scenario: Loop skills ask for project profiles or launch dossiers explicitly
- **WHEN** a loop skill asks an agent to prepare launch facts
- **THEN** it distinguishes project profiles from native launch dossiers
- **AND THEN** it does not use raw profile or launch profile ambiguously
