## MODIFIED Requirements

### Requirement: Launch-profiles conceptual guide exists

The getting-started section SHALL include a page at `docs/getting-started/launch-profiles.md` that explains the shared launch-profile semantic model and the two user-facing authoring lanes.

The page SHALL explain:

- what a launch profile IS: reusable, operator-owned, birth-time launch configuration that is distinct from reusable source definitions and distinct from live managed-agent instances,
- the two authoring lanes: easy `profile` (specialist-backed, opinionated) and explicit `launch-profile` (recipe-backed, low-level),
- the shared catalog-backed model that backs both lanes,
- the five-layer effective-launch precedence order,
- prompt overlay modes (`append` and `replace`) and where overlay composition happens relative to backend-specific role injection,
- that launch profiles may store a gateway mail-notifier appendix default as birth-time launch configuration,
- that explicit `project agents launch-profiles ...` and easy `project easy profile ...` authoring lanes both support that stored notifier appendix default,
- that launch-time materialization seeds that stored appendix into runtime gateway notifier state for the launched session,
- how launch-profile provenance flows into runtime metadata and is reported by inspection commands,
- when to use which lane.

The page SHALL link to:

- `docs/getting-started/easy-specialists.md` for the easy lane operator workflow,
- `docs/getting-started/agent-definitions.md` for the recipe authoring path and the `.houmao/agents/` projection layout,
- `docs/reference/cli/houmao-mgr.md` for the canonical CLI surfaces,
- `docs/reference/build-phase/launch-overrides.md` for how launch-profile defaults compose with launch overrides during build.

The page SHALL be derived from the active spec capabilities `agent-launch-profiles`, `houmao-mgr-project-easy-cli`, `houmao-mgr-project-agents-launch-profiles`, `houmao-mgr-agents-launch`, `brain-launch-runtime`, and `project-config-catalog`.

The page SHALL NOT introduce CLI shapes, env vars, or precedence behavior that are not present in those active spec capabilities.

#### Scenario: Reader understands what a launch profile is

- **WHEN** a reader opens the launch-profiles guide for the first time
- **THEN** they find a clear explanation that a launch profile is reusable birth-time launch configuration
- **AND THEN** they understand it is distinct from reusable source definitions (specialists and recipes) and distinct from live managed-agent instances
- **AND THEN** they understand that persisting, listing, inspecting, or removing a launch profile does not by itself create, stop, or mutate a live instance

#### Scenario: Reader understands the easy-versus-explicit lane split

- **WHEN** a reader scans the launch-profiles guide for the two user-facing surfaces
- **THEN** they find that the easy lane uses `project easy profile ...` and is specialist-backed
- **AND THEN** they find that the explicit lane uses `project agents launch-profiles ...` and is recipe-backed
- **AND THEN** they find that both lanes write into one shared catalog-backed launch-profile object family

#### Scenario: Reader understands notifier appendix defaults as launch-owned config

- **WHEN** a reader studies the launch-profiles guide for gateway-related launch defaults
- **THEN** the page explains that launch profiles may store a gateway mail-notifier appendix default
- **AND THEN** it explains that launch-time materialization seeds that appendix into runtime gateway notifier state rather than enabling notifier polling by itself
