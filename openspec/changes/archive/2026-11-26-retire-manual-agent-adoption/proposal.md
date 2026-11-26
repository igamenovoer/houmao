# Proposal

## Why

Manual session adoption synthesizes launch metadata around a process that Houmao did not prepare. As managed launch adds provider configuration, version qualification, and execution ownership, maintaining that second path makes lifecycle authority harder to establish and verify.

## What Changes

- **BREAKING** Remove `houmao-mgr agents self join` for both TUI and headless sessions, along with the packaged `agent-instance join` route. A local agent acquires managed lifecycle authority through a supported Houmao launch.
- **BREAKING** End managed control of saved `joined_tmux` sessions. Recognize their manifests as retired, exclude them from active control and discovery, and provide fresh-launch guidance. Upgrade handling preserves the manual process and its files.
- Use the existing v6 manifest format for native launches, including existing records with null adoption fields. Keep managed terminal handoff, gateway attachment, native relaunch and chat continuation, offline mailbox membership, and communication-only remote registration available through their existing surfaces.
- Update maintained docs, packaged skills, and contract tests for the launch-only workflow. Publish cutover guidance for existing joined sessions and their gateways.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-join` retires the TUI and headless adoption capability.
- `houmao-mgr-agents-scope-cli`, `houmao-mgr-agents-launch`, `houmao-srv-ctrl-native-cli`, `houmao-mgr-native-agent-internals-cli`, and `native-cli-provider-support` remove adoption from the supported command tree and define managed launch as the local entry path.
- `brain-launch-runtime`, `agent-discovery-registry`, `agent-authorization-policy`, and `authenticated-gateway-access` retire adopted launch authority and its publication path while preserving native runtime authority.
- `agent-gateway-mail-notifier`, `agent-memory-pages`, `native-agent-home-refresh`, and `managed-agent-mailbox-registration` describe these operations for supported managed runtimes.
- `agent-mailbox-system-skills`, `houmao-admin-entrypoint-skill`, `houmao-manage-agent-instance-skill`, `houmao-shared-routines-skill`, `houmao-system-skill-actor-context`, `houmao-system-skill-entrypoint-activation`, `houmao-system-skill-families`, `houmao-system-skill-installation`, and `managed-system-skill-test-coverage` retire the adoption route, actor handoff, and managed-join install lane.
- `docs-cli-reference`, `docs-getting-started`, `docs-project-aware-operations`, `docs-readme-system-skills`, `docs-system-skills-overview-guide`, `houmao-dev-behavior-testing-skill`, `houmao-project-mgr-skill`, `mailbox-reference-docs`, and `readme-structure` replace adoption instructions and fixture obligations with supported managed-launch guidance.

## Impact

This affects manager command registration, manifest authority checks, joined-only runtime paths, passive and gateway authority resolution, cleanup safeguards, and shipped skill assets. Operators with joined sessions use the owning release to wind down their Houmao management before upgrading. This change precedes the shared TUI observation work in [refactor-managed-runtime-boundaries](../refactor-managed-runtime-boundaries/proposal.md).
