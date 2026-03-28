## 1. Remove demo-pack authority from the active contract

- [x] 1.1 Delete the direct demo-pack capability specs under `openspec/specs/` that exist only to preserve the current `scripts/demo/*` workflows as maintained surface, including the pack specs for `agents-join-demo-pack`, `gateway-mail-wakeup-demo-pack`, `gateway-stalwart-cypht-interactive-demo-pack`, `houmao-server-agent-api-live-suite`, `houmao-server-dual-shadow-watch-demo`, `houmao-server-interactive-full-pipeline-demo`, `mail-ping-pong-gateway-demo-pack`, `mailbox-roundtrip-tutorial-pack`, `passive-server-parallel-validation`, `skill-invocation-demo-pack`, and `tui-mail-gateway-demo-pack`.
- [x] 1.2 Delete the companion demo-support specs that only elaborate the current demo packs, including the `mailbox-roundtrip-*` satellites and the `shared-tui-tracking-*` demo satellites that exist to preserve the current demo surface.
- [x] 1.3 Revise cross-cutting capability specs that still make current demos normative, including `cao-rest-client-contract`, `demo-agent-launch-recovery`, `runtime-agent-dummy-project-fixtures`, and relevant doc-contract specs, so the active system no longer requires current demo packs to exist or remain runnable.

## 2. Archive the current demos instead of preserving them as runnable workflows

- [x] 2.1 Move the current directories under `scripts/demo/` into `scripts/demo/legacy/` and add explicit archive-only framing that says they are historical reference, not supported runnable workflows.
- [x] 2.2 Remove or archive companion `src/houmao/demo/*` modules, wrappers, and helper-owned path defaults that only exist to support the archived demo packs as current workflows.
- [x] 2.3 Remove or demote manual/unit/integration test surfaces that still gate refactors on archived demo behavior or on `scripts/demo/*` remaining the current path.

## 3. Keep the remaining live shared surfaces canonical

- [x] 3.1 Update `tests/fixtures/agents/` so supported reusable assets live under canonical `skills/`, `roles/`, `tools/`, and optional compatibility metadata directories rather than legacy mirrors, and retire `tests/fixtures/agents/brains/api-creds.tar.gz.gpg` in favor of `tests/fixtures/agents/tools.tar.gz.enc`.
- [x] 3.2 Refactor supported non-demo tests and live explore helpers that still seed, assert, or document legacy `brains/` / `blueprints/` paths, including `src/houmao/explore/claude_code_state_tracking/interactive_watch.py`, `scripts/explore/claude-code-state-tracking/README.md`, `tests/unit/explore/test_claude_code_state_tracking_interactive_watch.py`, `tests/integration/agents/realm_controller/test_mailbox_runtime_contract.py`, and `tests/workflow/test-agent-gateway-tui-state-tracking.md`.
- [x] 3.3 Refresh supported fixture docs and snapshots whose expected path strings change because of the canonical-layout cleanup, including `tests/fixtures/agents/README.md`, `tests/fixtures/agents/skills/README.md`, and stale legacy fixture READMEs that remain in the live fixture tree.

## 4. Refresh supported docs and verify the new boundary

- [x] 4.1 Update supported docs so they no longer present current demos as maintained workflows and so any archived-demo references are clearly historical rather than current operator guidance.
- [x] 4.2 Run targeted searches across `openspec/specs`, `docs`, `tests`, and supported source packages confirming that archived demos no longer block the live contract and that the remaining supported fixture/explore surfaces no longer require old-style `brains/` or `blueprints/` directories as authoritative inputs.
