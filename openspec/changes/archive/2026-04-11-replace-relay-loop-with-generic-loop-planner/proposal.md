## Why

The current `houmao-agent-loop-relay` skill is named and specified as a relay-only planner, but the loop-planning layer now needs to own generic communication-graph decomposition across both elemental pairwise local-close edges and elemental relay lanes. Keeping the relay-only name would make agents route composed graph planning to the wrong mental model and would duplicate behavior that belongs in the pairwise planners or the elemental advanced-usage pattern pages.

## What Changes

- **BREAKING** Rename the packaged skill from `houmao-agent-loop-relay` to `houmao-agent-loop-generic`, including its asset directory, skill metadata, catalog key, catalog asset subpath, docs references, and OpenSpec capability.
- Replace the relay-only skill content with a generic loop graph planner and run controller that decomposes user intent into typed loop components.
- Require authored generic loop plans to classify each component as either:
  - a pairwise local-close component that uses the elemental pairwise edge-loop protocol, or
  - a relay-root component that uses the elemental relay-loop protocol.
- Keep `houmao-adv-usage-pattern` focused on elemental protocols and route composed topology, graph rendering, graph policy, run charters, and `start`/`status`/`stop` control to `houmao-agent-loop-generic`.
- Preserve the specialized pairwise skills as explicit pairwise-only planning choices while making the generic skill the replacement for relay-only planning and mixed graph decomposition.
- Update packaged skill catalog membership and README/docs/system-skill references from `houmao-agent-loop-relay` to `houmao-agent-loop-generic`.

## Capabilities

### New Capabilities
- `houmao-agent-loop-generic-skill`: Defines the renamed packaged generic loop graph planner, including decomposition into pairwise and relay-root components, plan/graph/charter structure, and `start`/`status`/`stop` run-control boundaries.

### Modified Capabilities
- `houmao-agent-loop-relay-skill`: Retires the relay-only packaged skill contract in favor of `houmao-agent-loop-generic-skill`.
- `houmao-adv-usage-pattern-skill`: Updates composed-loop routing references so elemental pairwise and relay protocol pages send graph planning to `houmao-agent-loop-generic`.
- `houmao-system-skill-installation`: Replaces `houmao-agent-loop-relay` with `houmao-agent-loop-generic` in the packaged catalog and `user-control` set requirements.
- `houmao-mgr-system-skills-cli`: Updates system-skill inventory and install-result requirements to surface the generic loop skill instead of the relay-only skill.
- `docs-cli-reference`: Updates the CLI system-skills reference to describe `houmao-agent-loop-generic` and remove the relay-only skill from current install selections.
- `docs-system-skills-overview-guide`: Updates the overview catalog and auto-install guidance to list `houmao-agent-loop-generic`.
- `docs-readme-system-skills`: Updates README system-skill catalog and `user-control` set descriptions to list `houmao-agent-loop-generic`.

## Impact

- Affected assets:
  - `src/houmao/agents/assets/system_skills/houmao-agent-loop-relay/` renamed and rewritten as `src/houmao/agents/assets/system_skills/houmao-agent-loop-generic/`
  - `src/houmao/agents/assets/system_skills/catalog.toml`
  - README and system-skills docs that enumerate packaged skills
  - OpenSpec main specs for the relay/generic loop skill, advanced-usage routing, catalog installation, system-skills CLI, and documentation surfaces
- The change is intentionally breaking: callers and docs should use `houmao-agent-loop-generic`; no compatibility alias for `houmao-agent-loop-relay` is required unless a future decision explicitly asks for migration support.
