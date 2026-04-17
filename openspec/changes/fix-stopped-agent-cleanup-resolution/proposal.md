## Why

Stopped managed-agent sessions are currently hard to clean by name because successful stop tears down the live shared-registry record that `agents cleanup --agent-id/--agent-name` relies on. Operators and packaged system-skill users need a supported way to clean stopped-session artifacts without having saved launch output manually.

## What Changes

- Extend managed-agent stop responses to include durable cleanup locators, at minimum `manifest_path` and `session_root`, before the live registry record is removed.
- Preserve those locators through `houmao-mgr agents stop`, pair-managed stop responses, and `houmao-mgr project easy instance stop`.
- Teach `houmao-mgr agents cleanup session|logs|mailbox --agent-id/--agent-name` to fall back to scanning the effective runtime root for stopped session manifests when no fresh shared-registry record exists.
- Keep the fallback bounded to local runtime-owned session envelopes and fail explicitly on ambiguity or missing matches.
- Update `houmao-agent-instance` cleanup guidance to prefer stop-returned `--manifest-path` or `--session-root` for post-stop cleanup and to describe name/id cleanup as capable of runtime-root fallback.
- Do not add a stopped-session tombstone, durable stopped-agent index, or new registry state store.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-cleanup-cli`: allow stopped-session cleanup selectors to recover targets through bounded runtime-root scanning when live registry metadata is gone.
- `houmao-mgr-registry-discovery`: require managed-agent stop results from `houmao-mgr agents stop` to surface durable cleanup locators before live registry cleanup makes name/id discovery unavailable.
- `houmao-server-agent-api`: require pair-managed stop responses to include durable cleanup locators when the stopped agent has manifest/session-root authority.
- `houmao-mgr-project-easy-cli`: preserve managed-agent stop cleanup locators in `project easy instance stop` output.
- `houmao-manage-agent-instance-skill`: update packaged cleanup guidance to use stop-returned locators first and avoid recommending registry-only selectors as the primary post-stop path.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/srv_ctrl/commands/runtime_cleanup.py`, `src/houmao/srv_ctrl/commands/project_easy.py`, and `src/houmao/srv_ctrl/commands/agents/cleanup.py`.
- Affected server/API models: managed-agent stop/action response models and pair/passive/server clients that parse them.
- Affected system skill assets and tests: `src/houmao/agents/assets/system_skills/houmao-agent-instance/actions/cleanup.md` plus system-skill projection tests.
- Affected docs/tests: cleanup CLI reference, registry/discovery docs where stop and cleanup recovery are described, and unit coverage for stopped-agent cleanup by selector.
