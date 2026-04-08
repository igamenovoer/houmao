## Why

Managed local launch currently fails when an operator tries to relaunch a managed agent identity that is still owned by another fresh live session. Operators need an explicit takeover path for replacing that existing managed session without turning registry ownership into a blind overwrite mechanism.

## What Changes

- Add a launch-time force takeover option for managed local launch and easy instance launch.
- Support two force modes:
- `keep-stale` as the default when the operator supplies bare `--force`, which stops the current managed predecessor and reuses its managed build home without cleaning untouched stale artifacts.
- `clean`, which stops the current managed predecessor and removes predecessor-owned replaceable launch artifacts before rebuilding the managed home from a clean state.
- Keep force mode launch-owned only; it SHALL NOT be persisted into reusable launch profiles or easy profiles.
- Preserve strict shared-registry ownership semantics by resolving the predecessor and making it stand down before the replacement launch publishes its own live record.
- Define operator-responsibility semantics for `keep-stale`: leftover stale artifacts are left in place and launch failures caused by that stale state are not automatically remediated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-launch`: add the managed launch force takeover surface and its runtime-only semantics.
- `houmao-mgr-project-easy-cli`: allow easy instance launch to delegate the same managed force takeover behavior without persisting it into easy profiles.
- `brain-launch-runtime`: define predecessor takeover, cleanup boundaries, and replacement-launch behavior for managed local runtime sessions.
- `component-agent-construction`: allow explicit managed-home reuse or scrub-and-recreate behavior when force takeover requests reuse an existing managed home.

## Impact

Affected areas include `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/brain_builder.py`, and related runtime cleanup and mailbox bootstrap helpers. The public CLI surface changes for managed local launch and easy instance launch, while launch profiles, easy profiles, and shared-registry ownership rules remain otherwise unchanged.
