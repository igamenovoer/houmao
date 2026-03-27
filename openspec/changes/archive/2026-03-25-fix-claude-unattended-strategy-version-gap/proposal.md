## Why

Managed Claude launch now depends on version-specific unattended strategy coverage before provider startup. That fail-closed behavior is correct, but the repository currently lags the installed Claude Code version on this machine, breaking both headless and interactive runtime-managed launch for recipes that request `operator_prompt_mode: unattended`.

The issue is broader than one stale version entry: the launch-policy registry is maintained as narrow hand-authored version windows rather than clearer dependency-style supported-version declarations, runtime-managed launch does not honor the documented `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` process override, and the user-facing `houmao-mgr agents launch` contract does not clearly explain or diagnose provider-version compatibility failures.

## What Changes

- Revise launch-policy strategy metadata to declare supported tool versions with dependency-style range expressions (for example `>=2.1.81,<2.2`) while keeping strict matching against the detected executable version.
- Extend the maintained Claude unattended launch-policy contract so supported installed Claude versions can launch when strategy assumptions are still valid, and unsupported versions fail with precise version/capability diagnostics rather than falling back to nearest-lower or latest-known strategies.
- Repair runtime-managed launch-policy override handling so `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` reaches launch-plan policy resolution as documented.
- Clarify the local `houmao-mgr agents launch` contract so operator-visible failures distinguish backend/mode selection from unattended-strategy compatibility blocking.
- Add coverage that detects Claude unattended strategy drift on the maintained runtime-managed launch path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: runtime-managed launch policy resolution must match detected tool versions against declared supported version ranges, honor documented strategy override input, and preserve precise compatibility failures before provider startup.
- `claude-cli-noninteractive-startup`: Claude unattended strategy support must declare maintained supported version ranges explicitly and fail with actionable version-aware diagnostics when unsupported.
- `houmao-mgr-agents-launch`: local managed launch must surface unattended strategy compatibility failures clearly when launch mode/backend selection succeeds but provider startup is blocked.
- `versioned-launch-policy-registry`: strategy registry entries must declare supported tool versions with dependency-style range expressions instead of the old min/max range mapping.

## Impact

- Claude unattended launch-policy registry data under `src/houmao/agents/launch_policy/registry/claude.yaml`
- Launch-policy models/parser and runtime strategy resolution in `src/houmao/agents/launch_policy/`
- Runtime launch-plan composition and policy-resolution environment plumbing
- Local managed launch diagnostics in `houmao-mgr agents launch`
- Regression and operational coverage for Claude unattended strategy compatibility
