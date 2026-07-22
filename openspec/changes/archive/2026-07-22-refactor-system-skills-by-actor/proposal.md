## Why

Houmao currently projects every maintained routine as a peer, top-level system skill, so the assistant does not get a reliable reminder of whether it is acting for a human operator or as a managed Houmao agent. The flat layout also duplicates routing guidance, exposes implementation-oriented skills directly, and gives first-time operators no stable welcome surface after the touring skill is retired.

## What Changes

- Add an admin pack with two public skills installed and managed atomically: the read-only `houmao-admin-welcome` guide and the executable `houmao-admin-entrypoint` router.
- Add a separate managed-agent pack whose only public skill is `houmao-agent-entrypoint`.
- Add a protected `houmao-shared-routines` skill bundle that owns reusable commands, references, and true nested subskills. The installer composes an audience-appropriate copy beneath each executable entrypoint, never beneath the welcome skill.
- Give both executable entrypoints an explicit, immutable actor contract. The admin entrypoint acts for a human operator against explicit targets; the agent entrypoint verifies its managed self identity and uses self-scoped routes unless a routine explicitly permits another scope.
- Define an audience routing matrix for admin-only, agent-only, and shared routines. Shared routines receive the actor context from the entrypoint and follow actor-specific branches without inferring or switching identity.
- Keep `houmao-admin-welcome` self-contained and read-only. It provides first-use orientation, presents curated guided paths, and hands executable work to `houmao-admin-entrypoint` with the selected context preserved.
- Reorganize large skills as lean `SKILL.md` routers with `commands/`, `references/`, and genuine nested `subskills/<name>/SKILL.md` packages. Existing procedure pages that do not own private resources become commands or references rather than nominal subskills.
- **BREAKING**: Replace the flat `core` / `extensions` / `all` catalog and per-skill projection model with audience packs, public skills, protected capabilities, mounts, and pack-aware install receipts.
- **BREAKING**: Retire direct installation and top-level discovery of the current low-level `houmao-*` skill names. Preserve those names only as stable internal routine identifiers where useful; do not add public compatibility wrappers.
- **BREAKING**: Replace the public `houmao-touring` skill with `houmao-admin-welcome`, and remove the compatibility-only `houmao-specialist-mgr` wrapper in favor of the canonical agent-definition routine.
- Keep `houmao-auto-system-prompt` in the separate managed auto-skill asset tree and outside the public/protected system-skill catalog.

## Capabilities

### New Capabilities

- `houmao-system-skill-protected-packaging`: Defines audience packs, public and protected assets, protected mounts, recursive validation, atomic installation, and pack-aware receipts.
- `houmao-system-skill-actor-context`: Defines immutable admin versus managed-agent actor context, route eligibility, scope rules, and fail-closed identity handling.
- `houmao-admin-welcome-skill`: Defines the public, read-only first-user tour and its handoff contract to the admin entrypoint.
- `houmao-admin-entrypoint-skill`: Defines the public human-operator execution router, explicit target handling, and welcome delegation.
- `houmao-agent-entrypoint-skill`: Defines the public managed-agent router, self-identity verification, and self-scoped execution posture.
- `houmao-shared-routines-skill`: Defines the protected routine bundle, command and subskill structure, audience metadata, and actor-aware delegation contract.

### Modified Capabilities

- `houmao-system-skill-installation`: Replace independent flat-skill selection and projection with pack selection, composition, atomic lifecycle operations, and recorded ownership.
- `houmao-mgr-system-skills-cli`: Replace set and low-level skill selectors with audience-pack operations and pack-aware list, install, status, upgrade, and uninstall output.
- `houmao-system-skill-flat-layout`: Replace the all-flat asset rule with top-level public discovery plus nested protected implementation.
- `houmao-system-skill-families`: Replace `core`, `extensions`, and `all` defaults with separate admin and managed-agent packs.
- `houmao-system-skill-help-operation`: Move public help to the welcome and entrypoint routers while requiring protected routines to expose route summaries rather than peer top-level help surfaces.
- `houmao-system-skill-input-questions`: Make system-input collection actor-aware and move first-user guided questions to `houmao-admin-welcome`.
- `agent-mailbox-system-skills`: Route managed mailbox workflows through `houmao-agent-entrypoint` and protected mailbox routines instead of projecting mailbox skills as top-level peers.
- `houmao-touring-skill`: Retire `houmao-touring` and transfer its maintained guided-tour behavior to `houmao-admin-welcome`.
- `houmao-create-specialist-skill`: Remove the compatibility-only `houmao-specialist-mgr` public wrapper and route the maintained behavior through the canonical agent-definition routine.
- `docs-system-skills-overview-guide`: Document actor packs, public discovery, protected routing, and the admin welcome paths instead of a flat skill inventory.
- `docs-readme-system-skills`: Replace the flat catalog summary with the three-skill public surface and audience installation defaults.
- `docs-cli-reference`: Document pack selectors, pack lifecycle semantics, and actor-aware invocation designators.
- `readme-structure`: Present the admin welcome as the first-use path and distinguish public entrypoints from protected routines.
- `managed-system-skill-test-coverage`: Cover manifest validation, audience composition, atomic pack lifecycle, actor route matrices, and managed-agent defaults at the appropriate test layers.

## Impact

This change affects packaged assets under `src/houmao/agents/assets/system_skills/`, the catalog and JSON Schema, the shared installer and system-skills CLI, managed launch and join defaults, skill-content validation, install-state handling, system-skill tests, and system-skill documentation. Existing external homes must uninstall or upgrade the old flat Houmao projections before using the new admin pack; managed homes receive the agent pack during launch, rebuild, relaunch, or join. The change does not turn protected assets into an authorization boundary, so CLI and runtime commands remain responsible for enforcing real permissions and target validity.
