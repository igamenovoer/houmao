## 1. Shared Cleanup Foundations

- [x] 1.1 Add shared cleanup planning/result models that cover dry-run, applied actions, blocked actions, preserved actions, and scope-resolution metadata.
- [x] 1.2 Add runtime artifact classification helpers for session roots, build manifest-home pairs, log-style artifacts, and runtime-owned mailbox credential files.
- [x] 1.3 Reuse or extend the existing manifest-first current-session resolution helpers so local cleanup commands can target one managed session from `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `--manifest-path`, or `--session-root`.

## 2. Admin Cleanup Commands

- [x] 2.1 Add the native `houmao-mgr admin cleanup` group with canonical `registry` and `runtime` subcommands, while retaining `admin cleanup-registry` as a compatibility alias if that path is still present.
- [x] 2.2 Extend shared-registry cleanup helpers to support `--dry-run` planning and optional local liveness-aware stale classification for tmux-backed records.
- [x] 2.3 Implement `houmao-mgr admin cleanup runtime sessions` so it removes only stopped or otherwise removable session envelopes and optionally their manifest-persisted job dirs.
- [x] 2.4 Implement `houmao-mgr admin cleanup runtime builds` so it removes only unreferenced or broken build manifest-home pairs.
- [x] 2.5 Implement `houmao-mgr admin cleanup runtime logs` so it removes only log-style or ephemeral runtime artifacts and preserves durable gateway or manifest state.
- [x] 2.6 Implement `houmao-mgr admin cleanup runtime mailbox-credentials` so it removes only Stalwart credential files whose `credential_ref` is no longer referenced by preserved session manifests.

## 3. Agent-Scoped Cleanup Commands

- [x] 3.1 Add the native `houmao-mgr agents cleanup {session,logs,mailbox}` command family as local managed-session cleanup commands.
- [x] 3.2 Implement `houmao-mgr agents cleanup session` so it blocks live sessions, removes stopped session roots, and optionally removes the resolved `job_dir`.
- [x] 3.3 Implement `houmao-mgr agents cleanup logs` so it removes only session-local log-style artifacts for the resolved session and preserves durable gateway state.
- [x] 3.4 Implement `houmao-mgr agents cleanup mailbox` so it removes only session-local mailbox secret material derived from the resolved session authority.
- [x] 3.5 Add unit coverage for explicit selector targeting, explicit path targeting, current-session fallback, and live-session block behavior.

## 4. Mailbox Root Cleanup

- [x] 4.1 Add `houmao-mgr mailbox cleanup` for inactive or stashed filesystem mailbox registrations with the same mailbox-root resolution rules as the rest of the mailbox CLI.
- [x] 4.2 Implement mailbox-layer cleanup helpers that preserve active registrations, preserve canonical `messages/` content, and report dry-run versus applied cleanup results clearly.
- [x] 4.3 Add unit coverage that verifies inactive or stashed registrations can be cleaned while active registrations and canonical message history remain intact.

## 5. Documentation And Verification

- [x] 5.1 Update CLI, registry, mailbox, and system-files reference docs to describe the grouped cleanup tree, `--dry-run`, current-session cleanup defaults, and durable-versus-cleanup-sensitive artifact boundaries.
- [x] 5.2 Run targeted CLI, registry, runtime, and mailbox test coverage for the new cleanup flows and confirm `openspec status --change add-houmao-mgr-cleanup-commands` is apply-ready.
