## 1. Stop Response Locators

- [x] 1.1 Extend managed-agent action response models to carry optional `manifest_path` and `session_root` fields without breaking existing clients.
- [x] 1.2 Update local `houmao-mgr agents stop` handling to capture `manifest_path` and `session_root` from the resolved target before registry cleanup.
- [x] 1.3 Update `houmao-server` managed-agent stop handling for headless targets to return cleanup locators when authority metadata exists.
- [x] 1.4 Update `houmao-server` managed-agent stop handling for TUI-backed targets to return cleanup locators when tracked identity metadata exists.
- [x] 1.5 Update pair/passive/server client parsing or compatibility wrappers for the extended stop response shape.
- [x] 1.6 Update `houmao-mgr project easy instance stop` to preserve locator fields from the underlying stop result while keeping overlay validation before stop.

## 2. Cleanup Runtime-Root Fallback

- [x] 2.1 Add a focused stopped-session discovery helper that scans the effective runtime root's `sessions/*/*/manifest.json` envelopes and matches persisted `agent_id` or `agent_name`.
- [x] 2.2 Wire `agents cleanup session|logs|mailbox --agent-id/--agent-name` to use the runtime-root fallback only after fresh shared-registry resolution misses.
- [x] 2.3 Ensure the fallback resolves exactly one stopped session or fails closed with candidate `agent_id`, `agent_name`, `manifest_path`, and `session_root` metadata.
- [x] 2.4 Ensure cleanup fallback does not change live-control discovery for prompt, interrupt, state, gateway, mail, or ordinary `agents list`.
- [x] 2.5 Keep malformed-manifest behavior explicit: selector fallback may match only manifests with readable identity metadata, while `--manifest-path` and `--session-root` remain the authority for malformed envelopes.

## 3. Guidance And Docs

- [x] 3.1 Update `houmao-agent-instance` cleanup guidance to prefer stop-returned `--manifest-path` or `--session-root` for post-stop cleanup.
- [x] 3.2 Update cleanup guidance to describe `--agent-id` and `--agent-name` as valid cleanup selectors that may use runtime-root fallback after live registry removal.
- [x] 3.3 Ensure packaged guidance does not introduce stopped-session tombstones, stopped-agent indexes, or unsupported registry state.
- [x] 3.4 Update CLI/reference docs that describe stop output, cleanup targeting, and registry-vs-runtime cleanup recovery.

## 4. Tests

- [x] 4.1 Add unit coverage proving local `agents stop` and `project easy instance stop` outputs include cleanup locators when manifest authority is known.
- [x] 4.2 Add server/API unit coverage proving headless and TUI managed-agent stop responses include locators when known and omit them when unavailable.
- [x] 4.3 Add cleanup unit coverage for stopped-session recovery by `--agent-id` after registry removal.
- [x] 4.4 Add cleanup unit coverage for stopped-session recovery by `--agent-name` after registry removal.
- [x] 4.5 Add cleanup unit coverage for ambiguous stopped-session selector matches and no-match diagnostics.
- [x] 4.6 Add or update system-skill projection tests for the revised `houmao-agent-instance` cleanup guidance.

## 5. Verification

- [x] 5.1 Run focused cleanup and managed-agent command tests.
- [x] 5.2 Run focused server/API response tests.
- [x] 5.3 Run focused system-skill asset tests.
- [x] 5.4 Run `pixi run openspec status --change fix-stopped-agent-cleanup-resolution` and confirm the change is apply-ready.
