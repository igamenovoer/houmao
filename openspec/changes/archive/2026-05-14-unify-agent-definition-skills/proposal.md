## Why

Houmao currently splits closely related pre-launch agent-definition workflows across `houmao-agent-definition`, `houmao-specialist-mgr`, and part of `houmao-project-mgr`, which makes agents ask avoidable routing questions and makes the preferred easy-profile path feel less canonical than the advanced low-level paths. Issue #52 also asks for a one-click/single-command style path that creates a ready-to-launch managed-agent profile from a specialist without manually stitching together specialist, profile, mailbox, gateway, notifier, and launch defaults.

## What Changes

- **BREAKING** Unify specialist/easy-profile guidance into `houmao-agent-definition` as the canonical skill for persisted agent definitions before launch.
- Expand `houmao-agent-definition` into routed subskills for:
  - low-level roles and recipes;
  - explicit recipe-backed launch profiles;
  - project-easy specialists and easy profiles;
  - one-click ready easy-profile creation;
  - easy launch/stop entry points with handoff to live-agent lifecycle guidance.
- Add a one-click ready-profile path that creates or selects a specialist, creates an easy profile, stores launch defaults, and prints the launch command without launching the agent.
- Preserve `houmao-specialist-mgr` only as a temporary compatibility redirect, or remove it from current install sets when the implementation chooses not to keep a stub.
- Move explicit recipe-backed launch-profile authoring guidance out of `houmao-project-mgr` ownership and into `houmao-agent-definition`; keep project overlay lifecycle and layout on `houmao-project-mgr`.
- Keep credential bundle CRUD, mailbox administration, workspace creation, and broad live-agent lifecycle on their existing dedicated skills.
- Update system-skill catalogs, docs, routing references, and loop-skill guidance to prefer the unified skill and the easy-profile path.

## Capabilities

### New Capabilities
- `houmao-agent-ready-profile-workflow`: Covers the one-click ready managed-agent profile workflow that creates/selects a specialist, creates an easy profile, wires launch defaults, and reports a launch command without launching.

### Modified Capabilities
- `houmao-manage-agent-definition-skill`: Expand the packaged `houmao-agent-definition` skill from low-level roles/recipes into the canonical routed skill for low-level definitions, explicit launch profiles, specialists, easy profiles, ready-profile generation, and limited easy launch/stop entry points.
- `houmao-create-specialist-skill`: Retire or redirect `houmao-specialist-mgr` as a current specialist-management skill while preserving its behavior inside the unified `houmao-agent-definition` easy subskills.
- `houmao-create-specialist-credential-sources`: Move create-action credential-source and lookup guidance under the unified `houmao-agent-definition` easy specialist/ready-profile paths.
- `houmao-project-mgr-skill`: Remove explicit recipe-backed launch-profile authoring from project-manager ownership and route it to `houmao-agent-definition`.
- `houmao-system-skill-installation`: Update current packaged skill inventory and install-set membership for the unified skill and any compatibility redirect.
- `houmao-mgr-system-skills-cli`: Update `system-skills` install/status behavior and examples to reflect the unified skill inventory.
- `docs-readme-system-skills`: Update README system-skill inventory prose.
- `readme-structure`: Update README skill table expectations.
- `docs-system-skills-overview-guide`: Update system-skill overview routing guidance.
- `docs-cli-reference`: Update CLI system-skill reference and routing examples.

## Impact

- Affected system-skill assets:
  - `src/houmao/agents/assets/system_skills/houmao-agent-definition/`
  - `src/houmao/agents/assets/system_skills/houmao-specialist-mgr/`
  - `src/houmao/agents/assets/system_skills/houmao-project-mgr/`
  - loop skills and adjacent routing references that mention `houmao-specialist-mgr`
- Affected system-skill catalog/install code that exposes packaged skills and install sets.
- Affected documentation under README, getting-started guides, and CLI reference pages.
- No new runtime dependency is expected; this is primarily packaged skill guidance, routing, and documentation.
