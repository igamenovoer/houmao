## Why

Gateway mail notifications currently use a fixed wake-up prompt assembled from gateway-owned template text, notifier mode, and runtime gateway coordinates. Operators cannot attach runtime-specific guidance to that notifier state, which makes it awkward to steer mailbox rounds with per-session context that should travel with the live notifier configuration itself.

## What Changes

- Extend gateway mail-notifier state with an optional `appendix_text` string that is stored with the notifier configuration and appended to rendered notifier prompts when non-empty.
- Allow direct gateway `GET /v1/mail-notifier` reads to return the effective `appendix_text`.
- Allow direct gateway `PUT /v1/mail-notifier` writes to update `appendix_text` when provided, preserve the existing appendix when omitted, and clear it when an empty string is sent.
- Preserve existing `DELETE /v1/mail-notifier` behavior as notifier disablement rather than config erasure.
- Expose the same appendix field through passive/server-managed managed-agent gateway proxy routes and the native `houmao-mgr agents gateway mail-notifier` CLI surface.
- Allow shared launch profiles to store a default gateway mail-notifier appendix for future launches.
- Expose that stored default through both `houmao-mgr project agents launch-profiles ...` and `houmao-mgr project easy profile ...` authoring lanes.
- Materialize launch-profile-owned notifier appendix defaults into runtime gateway notifier state at launch time so later live notifier enablement can reuse them.
- Document appendix behavior as notifier-owned wake-up context rather than as a replacement for the mailbox-processing skill workflow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: extend notifier request/status state and prompt rendering with queryable, modifiable appendix text.
- `passive-server-gateway-proxy`: preserve notifier appendix text unchanged through managed-agent gateway mail-notifier proxy routes.
- `houmao-srv-ctrl-native-cli`: expose notifier appendix configuration through `houmao-mgr agents gateway mail-notifier`.
- `docs-gateway-mail-notifier-reference`: document notifier appendix state, API semantics, CLI usage, and prompt-rendering behavior.
- `agent-launch-profiles`: extend the shared launch-profile model with an optional gateway mail-notifier appendix default.
- `houmao-mgr-project-agents-launch-profiles`: expose the launch-profile appendix default on the explicit recipe-backed profile CLI.
- `houmao-mgr-project-easy-cli`: expose the same launch-profile appendix default on the easy profile CLI.
- `brain-launch-runtime`: seed launch-profile-owned notifier appendix defaults into runtime gateway notifier state during launch resolution.
- `docs-launch-profiles-guide`: document launch-profile-owned notifier appendix defaults and how they materialize into runtime gateway state.

## Impact

- Affected code in gateway notifier models, SQLite-backed notifier storage, gateway prompt rendering, passive/server gateway clients and service routes, and native `agents gateway mail-notifier` commands.
- Affected code in shared launch-profile catalog/models, explicit launch-profile CLI, easy profile CLI, and launch/runtime materialization.
- Affected tests for direct gateway runtime behavior, proxy behavior, CLI forwarding, and notifier prompt rendering.
- Affected documentation for gateway mail-notifier API/CLI behavior and launch-profile defaults.
