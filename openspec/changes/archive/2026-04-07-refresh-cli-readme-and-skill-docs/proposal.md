## Why

The previous doc-refresh pass landed on `2026-04-07 18:10` (system-skills CLI ref), but the same day a wave of feature commits shipped after it — managed prompt header injection, the unified `houmao-agent-email-comms` skill, the `manage-agent-definition` and `manage-agent-instance` skills, the `houmao-mgr --version` flag, the `--workdir` launch flag, easy gateway-on-by-default, the symlink-mode `system-skills install --link`, and the `--yolo` removal. As a result the CLI reference pages, the README skill catalog, and the conceptual coverage are now out of step with the live code, and there is no narrative page for the system-skills surface or the managed prompt header at all. Operators and agents reading the docs today will hit broken examples (`--yolo`), missing flags (`--version`, `--workdir`), and a skill list that no longer matches what `system-skills install` projects.

## What Changes

- **Resync `agents` CLI reference pages** to current Click decorators and `--help` output: `agents-mail.md`, `agents-mailbox.md`, `agents-turn.md`, `agents-gateway.md`, `admin-cleanup.md`, `houmao-server.md`. Verify the pages reflect post-`--yolo` state and the unified email-comms behavior.
- **Resync `houmao-mgr.md`** to add the new `--version` flag, the `agents launch --workdir` option, the unified `--model` selector, and remove every remaining `--yolo` mention. Verify the `project agents launch-profiles` and `project easy` subsurfaces are documented end to end.
- **Add new conceptual page `docs/reference/run-phase/managed-prompt-header.md`** explaining the Houmao-owned prompt header that is now prepended to every managed launch by default — what it injects, ordering relative to prompt-overlay resolution and backend role-injection, the `--no-managed-header` opt-out, and how easy profiles and explicit launch profiles persist that policy.
- **Add new narrative page `docs/getting-started/system-skills-overview.md`** that walks through the eight current packaged system skills (`houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, `houmao-manage-agent-instance`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`), their managed-home auto-install vs external-home CLI-default install behavior, and the canonical pointers into the full CLI reference.
- **Polish `README.md`**:
  - Add a `houmao-agent-email-comms` row to the skill catalog table and reconcile the default-install paragraph against the current `system_skills.py` defaults.
  - Add one short note about the managed prompt header in "What You Get After Joining."
  - Add `--version` to the CLI Entry Points table (or footnote it).
  - Re-evaluate the "In development — not ready for use" status text for `houmao-passive-server` against the rewritten reference page.
- **Cleanup sweep across `docs/`**:
  - grep for `--yolo`, `manage-yolo`, removed flag references and remove or rewrite each.
  - grep for the legacy `specialist` skill name (vs the renamed `houmao-manage-specialist`) and the long-removed `agentsys` / `.agentsys` strings.
  - Verify `docs/index.md` and `docs/reference/index.md` link the two new pages and that no existing cross-reference 404s.

This change explicitly defers refreshing the older subsystem reference pages under `reference/system-files/`, `reference/mailbox/contracts/`, `reference/mailbox/operations/`, `reference/gateway/operations/`, `reference/registry/`, `reference/lifecycle/`, and `reference/run-phase/session-lifecycle.md`. Those pages have not been touched since `2026-04-04 19:48` and need their own bounded pass.

## Capabilities

### New Capabilities
- `docs-managed-launch-prompt-header-reference`: Reference documentation for the Houmao-owned managed prompt header — what it injects, ordering vs role injection and prompt overlays, opt-out flags, persistence in launch profiles.
- `docs-system-skills-overview-guide`: Narrative getting-started page that tours the packaged system-skills surface, explains managed vs external install defaults, and bridges README and the CLI reference.

### Modified Capabilities
- `docs-cli-reference`: Update `agents-mail`, `agents-mailbox`, `agents-turn`, `agents-gateway`, `admin-cleanup`, `houmao-server`, and `houmao-mgr` requirements to match the post-`2026-04-07` CLI surface, including `--version`, `agents launch --workdir`, unified `--model` selection, and the removal of `--yolo`.
- `docs-readme-system-skills`: Reflect the unified `houmao-agent-email-comms` skill, the managed prompt header note, and the `--version` flag in the README requirements.
- `docs-site-structure`: Require the two new pages to be linked from `docs/index.md` and `docs/reference/index.md`.
- `docs-stale-content-removal`: Add `--yolo` and stale `specialist` skill-name references to the sweep contract.

## Impact

- **Files modified**: ~7 CLI reference pages, `README.md`, `docs/index.md`, `docs/reference/index.md`, plus targeted edits anywhere a `--yolo` or stale skill name still lives.
- **Files added**: `docs/reference/run-phase/managed-prompt-header.md`, `docs/getting-started/system-skills-overview.md`.
- **Specs**: 2 new spec files, 4 modified spec deltas.
- **Code**: Zero code changes — docs-only.
- **Out of scope**: subsystem internals/contracts pages under `reference/system-files/`, `reference/mailbox/`, `reference/gateway/operations/`, `reference/registry/`, `reference/lifecycle/`, and the older `run-phase/session-lifecycle.md`. These will be addressed in a follow-up change.
