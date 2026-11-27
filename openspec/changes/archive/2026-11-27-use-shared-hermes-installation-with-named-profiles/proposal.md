# Proposal

## Why

Every new standalone Hermes home can prepare its own Python environment before the agent starts. Issue #106 reports dependency syncs that consumed or exceeded the entire readiness window. Hermes named profiles let agents share an already prepared installation while keeping their own configuration and conversations. [Issue #106](https://github.com/igamenovoer/houmao/issues/106)

## What Changes

- Use one explicitly prepared Hermes root per selected execution owner. Ordinary agent launch, relaunch, and turns use its prepared dependencies. A missing, stale, or incompatible installation fails with owner-side setup guidance.
- Create one native named profile per managed agent under the shared root. Give the project its usual home path through a Houmao-owned symlink pointing to the canonical profile. Keep the project workspace independently selectable.
- **BREAKING**. New managed Hermes launches share the configured native gateway. Each agent owns its profile, exact session, and mode-specific client. Service, TUI, and Headless bind and verify the selected profile before publishing readiness.
- Apply launch credentials, permissions, lifecycle operations, and managed-self proof to the selected profile and generation. Ordinary stop preserves the profile for relaunch. Explicit cleanup removes the owned native profile and its verified project link.
- Existing standalone runtimes can be retired using their saved ownership. Entering the named-profile layout requires a fresh launch. Exact continuation under this layout applies to sessions already in the selected named profile.

## Capabilities

### New Capabilities

### Modified Capabilities

- `hermes-agent-runtime` covers the prepared installation, shared gateway, profile-qualified native control, and per-profile lifecycle.
- `brain-launch-runtime` binds the Hermes profile and project-local link to the owned build and runtime records.
- `houmao-managed-agent-self-identity` requires auditable profile-specific caller authority for tools descended from the shared gateway.
- `authenticated-gateway-access` qualifies current Hermes managed-self ingress against the exact served-profile authority as well as the current key registration.
- `houmao-mgr-cleanup-cli` covers preview and retryable removal of the two Hermes home artifacts after the last preserved reference is gone.
- `test-agent-launch-fixtures` qualifies multiple workers under one prepared owner installation and exercises profile-scoped cleanup and authority.

## Impact

The change affects Hermes launch preparation, provider adapters, service ownership, runtime manifests, managed-self verification, and cleanup. Operator documentation will explain how to prepare the shared root and how profile state survives stop and relaunch. The Hermes fixtures will exercise two projects in the same execution context, all three managed modes, and signed self operations when multiple profiles are live.
