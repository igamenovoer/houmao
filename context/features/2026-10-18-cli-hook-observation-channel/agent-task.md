# Agent Task

Status: Not started. This handoff will be written after design review and use-case stabilization.

## Objective

Implement the provider-neutral CLI Hook Observation Channel and the first Claude Code adapter so that managed-agent state tracking can merge provider lifecycle hooks with TUI parsing.

## Required Use Cases

- `UC-01`: Enable and Verify Hook Observation for a Managed Claude Launch
- `UC-02`: Merge Hook Lifecycle with TUI Surface State for a Normal Turn
- `UC-03`: Detect Permission Waits and API Failures from Hooks
- `UC-04`: Degrade to TUI-Only State When Hooks Are Unavailable

## Design References

- [Feature Requirement](feature-requirement.md)
- [Public Interfaces](design/public-interfaces.md)
- [Claude Hook Adapter](design/claude-hook-adapter.md)
- [Qualification and Rollout](design/qualification-and-rollout.md)

## Implementation Instructions

Pending design review. The implementation should follow the module map in [Design](README.md) and preserve the TUI-only fallback in every degraded state.

## Verification

Pending design review. Start with the gates in [Qualification and Rollout](design/qualification-and-rollout.md).

## Required Evidence

Evidence packs should be written to a run-specific directory under `tmp/` and should not be committed unless explicitly requested.

## Out Of Scope

- Joined sessions and unmanaged provider launches.
- Codex and Kimi adapters.
- GUI and AG-UI changes.
- Provider behavior changes or automatic remediation.

## Open Questions

- Which transport and enablement decisions require ADRs before implementation?
- Which optional Claude events are safe at the 2.1.296 floor?
