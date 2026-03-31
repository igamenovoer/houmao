## 1. Create dedicated CLI reference pages

- [ ] 1.1 Create `docs/reference/cli/project.md` — extract all `houmao-mgr project` content from `houmao-mgr.md`: `init`, `status`, `agents tools` (claude/codex/gemini with setups + auth), `agents roles` (with presets), `easy specialist` (create/list/get/remove), `easy instance` (launch/list/get/stop), and `mailbox` (init/status/register/unregister/repair/cleanup/accounts/messages). Verify against actual CLI surface in `src/houmao/srv_ctrl/commands/project.py`.
- [ ] 1.2 Create `docs/reference/cli/server.md` — extract `houmao-mgr server` content from `houmao-mgr.md`: `start` (with all startup options), `stop`, `status`, and `sessions` (list/show/shutdown). Clarify this documents the manager-side commands, not the server binary.
- [ ] 1.3 Create `docs/reference/cli/mailbox.md` — extract `houmao-mgr mailbox` content from `houmao-mgr.md`: `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `accounts` (list/get), `messages` (list/get). Verify against `src/houmao/srv_ctrl/commands/mailbox.py`.
- [ ] 1.4 Create `docs/reference/cli/brains.md` — extract `houmao-mgr brains build` content from `houmao-mgr.md` with all build options. Verify against `src/houmao/srv_ctrl/commands/brains.py`.
- [ ] 1.5 Create `docs/reference/cli/agents-cleanup.md` — extract `houmao-mgr agents cleanup` content from `houmao-mgr.md`: `session`, `logs`, `mailbox` with options and dry-run support. Verify against `src/houmao/srv_ctrl/commands/agents/cleanup.py`.

## 2. Slim down houmao-mgr.md to overview hub

- [ ] 2.1 Rewrite `docs/reference/cli/houmao-mgr.md` as a hub page: keep the command tree hierarchy with one-line descriptions per group, replace full option documentation with links to dedicated pages (project.md, server.md, mailbox.md, brains.md, agents-cleanup.md, and existing agents-gateway.md, agents-turn.md, agents-mail.md, agents-mailbox.md, admin-cleanup.md). Retain any introductory text about output styles and global options.

## 3. Relocate flat reference files

- [ ] 3.1 Move `docs/reference/cli.md` to `docs/reference/cli/index.md`. Isolate `houmao-cli` and `houmao-cao-server` references into a clearly labeled "Deprecated Entrypoints" section.
- [ ] 3.2 Move `docs/reference/realm_controller_send_keys.md` to `docs/reference/agents/operations/send-keys.md`.
- [ ] 3.3 Move `docs/reference/managed_agent_api.md` to `docs/reference/agents/contracts/api.md`.

## 4. Merge overlapping content

- [ ] 4.1 Merge unique content from `docs/reference/realm_controller.md` (high-level orchestration overview, CLI surface note) into `docs/reference/run-phase/session-lifecycle.md`. Remove duplicated content. Delete `realm_controller.md` after merge.

## 5. Delete stubs

- [ ] 5.1 Delete `docs/reference/houmao_server_agent_api_live_suite.md`. Remove or redirect any references to it in index pages.

## 6. Update cross-references

- [ ] 6.1 Find all markdown files that link to moved/renamed/deleted paths (`realm_controller.md`, `realm_controller_send_keys.md`, `managed_agent_api.md`, `houmao_server_agent_api_live_suite.md`, `cli.md`) and update links to new locations.
- [ ] 6.2 Update `docs/reference/index.md` to reflect the new file structure and link to new pages.

## 7. Verify

- [ ] 7.1 Run `mkdocs build --strict` (or equivalent) and confirm zero broken-link warnings. Fix any remaining link issues.
