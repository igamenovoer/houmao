## 1. Complete Truncated CLI Reference Stubs

- [x] 1.1 Complete `docs/reference/cli/agents-gateway.md` — add full option tables and descriptions for `tui state`, `tui history`, `tui watch`, `tui note-prompt`, `mail-notifier status`, `mail-notifier enable`, `mail-notifier disable`. Derive from `srv_ctrl/commands/agents/gateway.py` Click decorators and `--help` output.
- [x] 1.2 Complete `docs/reference/cli/agents-mail.md` — add full option tables and descriptions for all 6 subcommands (`resolve-live`, `status`, `check`, `send`, `reply`, `mark-read`). Include targeting rules and authority-aware result semantics. Derive from `srv_ctrl/commands/agents/mail.py`.
- [x] 1.3 Complete `docs/reference/cli/agents-mailbox.md` — add full option tables for `register`, `unregister`, `status`. Derive from `srv_ctrl/commands/agents/mailbox.py`.
- [x] 1.4 Complete `docs/reference/cli/agents-turn.md` — add full option tables for `submit`, `status`, `events`, `stdout`, `stderr`. Derive from `srv_ctrl/commands/agents/turn.py`.

## 2. Rewrite houmao-passive-server Reference

- [x] 2.1 Rewrite `docs/reference/cli/houmao-passive-server.md` from stub to comprehensive reference. Include: when to use (vs houmao-server comparison table), serve command with all options, API routes and capabilities, which `houmao-mgr` commands are compatible. Derive from `passive_server/service.py`, `passive_server/app.py`, `passive_server/models.py`.

## 3. New Conceptual and Reference Pages

- [x] 3.1 Create `docs/reference/gateway/operations/mail-notifier.md` — explain what the mail-notifier is, configuration (enable/disable/status), email processing prompt flow, integration with gateway lifecycle. Derive from `gateway_service.py` mail-notifier methods and `mail_commands.py`.
- [x] 3.2 Create `docs/reference/agents/operations/project-aware-operations.md` — explain project-aware command resolution, the full precedence chain, `HOUMAO_PROJECT_OVERLAY_DIR` override, catalog-backed overlay storage, which commands are project-aware. Derive from `project/overlay.py`, `project/catalog.py`, and `srv_ctrl/commands/` project-aware initialization.
- [x] 3.3 Create `docs/reference/mailbox/contracts/project-mailbox-skills.md` — explain native mailbox skill projection, when it activates, what skills are injected, tool-specific behavior. Derive from `agents/mailbox_runtime_support.py` and `agents/realm_controller/assets/system_skills/`.
- [x] 3.4 Create `docs/getting-started/easy-specialists.md` — explain easy-specialist vs full presets, specialist-to-instance lifecycle, relationship to managed agents, CLI commands. Derive from `project/easy.py` and `srv_ctrl/commands/project.py`.
- [x] 3.5 Create `docs/reference/build-phase/launch-policy.md` — explain launch policy engine, `OperatorPromptMode`, provider hooks, versioned registry, integration with build phase. Derive from `agents/launch_policy/`.

## 4. Polish Quickstart

- [x] 4.1 Review and complete `docs/getting-started/quickstart.md` Workflow 1 (Join) — ensure the entire join → control → stop cycle is presented without truncation. Verify Mermaid sequence diagram is present.
- [x] 4.2 Review and complete `docs/getting-started/quickstart.md` Workflow 2 (Build) — ensure the entire init → specialist create → launch → prompt → stop cycle is presented without truncation. Add link to easy-specialist guide.

## 5. Stale Content Sweep

- [x] 5.1 Grep all `docs/**/*.md` files for `agentsys`, `.agentsys`, `AGENTSYS_` — replace with `houmao` equivalents (`.houmao`, `HOUMAO_`). Review each replacement for contextual accuracy.
- [x] 5.2 Verify no broken cross-references exist between new pages and existing pages. Spot-check links in new pages resolve to existing targets.

## 6. Update Index Pages

- [x] 6.1 Update `docs/index.md` — add links to new pages: easy-specialists guide, launch-policy reference. Verify all existing links still resolve.
- [x] 6.2 Update `docs/reference/index.md` — add links to new pages: launch-policy, project-aware-operations, project-mailbox-skills. Verify build-phase section lists both launch-overrides and launch-policy.
- [x] 6.3 Update `docs/reference/gateway/index.md` — add link to `operations/mail-notifier.md`.
- [x] 6.4 Update `docs/reference/agents/index.md` — add link to `operations/project-aware-operations.md`.
- [x] 6.5 Update `docs/reference/mailbox/index.md` — add link to `contracts/project-mailbox-skills.md`.
