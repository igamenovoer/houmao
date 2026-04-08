## 1. README.md Current Status removal

- [x] 1.1 Delete the `## Current Status` heading and the paragraph below it from `README.md` so the file jumps directly from the project tagline to `## Project Introduction`.
- [x] 1.2 Verify `README.md` no longer contains the words "stabilizing", "unstable", or "still stabilizing" in any content above the `## Project Introduction` section.

## 2. CLAUDE.md refresh

- [x] 2.1 Update the Build phase bullet under `## Architecture → Two-Phase Lifecycle` in `CLAUDE.md` so it describes recipes plus launch profiles as the current resolution model instead of `AgentPreset`.
- [x] 2.2 Update the Source Layout bullet list under `## Architecture` in `CLAUDE.md` to add bullets for `src/houmao/project/`, `src/houmao/passive_server/`, `src/houmao/mailbox/`, `src/houmao/lifecycle/`, `src/houmao/terminal_record/`, `src/houmao/shared_tui_tracking/`, and `src/houmao/server/`, each with a one-line description derived from the current source.
- [x] 2.3 Update the `config/` bullet under `## Supporting Directories` in `CLAUDE.md` so it no longer references "CAO server launcher config" as the example; describe `config/` in terms of current Houmao configuration assets.
- [x] 2.4 Grep `CLAUDE.md` for any remaining references to `houmao-cao-server`, `cao_server_launcher`, or `AgentPreset`; if any appear in a way that implies current operator use, reframe them as historical context or remove them.

## 3. docs/index.md navigation sweep

- [x] 3.1 In `docs/index.md`, under the `### CLI Surfaces` subsection of `## Reference`, add one-line description entries for `reference/cli/agents-gateway.md`, `reference/cli/agents-turn.md`, `reference/cli/agents-mail.md`, `reference/cli/agents-mailbox.md`, `reference/cli/admin-cleanup.md`, and `reference/cli/system-skills.md`.
- [x] 3.2 In `docs/index.md`, under the `### Run Phase` subsection of `## Reference`, add a one-line description entry for `reference/run-phase/managed-prompt-header.md`.
- [x] 3.3 In `docs/index.md`, under the `## Reference → Other Reference` (or equivalent) section, remove the `[Runtime-Managed Agents](reference/agents/index.md)` link.
- [x] 3.4 Verify that `docs/index.md` contains zero matches for `reference/agents/` after the edit.

## 4. Retire docs/reference/agents/ subtree

- [x] 4.1 Move `docs/reference/agents/operations/project-aware-operations.md` to `docs/reference/system-files/project-aware-operations.md`; preserve the page content as-is except for self-references (any `../../system-files/...` relative links must be rewritten to match the new location).
- [x] 4.2 Move `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md` to `docs/reference/codex-cao-approval-prompt-troubleshooting.md`; update any internal relative links inside the page so they still resolve from the new location.
- [x] 4.3 Delete `docs/reference/agents/index.md`.
- [x] 4.4 Delete `docs/reference/agents/contracts/public-interfaces.md` and the now-empty `docs/reference/agents/contracts/` directory.
- [x] 4.5 Delete `docs/reference/agents/internals/state-and-recovery.md` and the now-empty `docs/reference/agents/internals/` directory.
- [x] 4.6 Delete `docs/reference/agents/operations/session-and-message-flows.md` and the now-empty `docs/reference/agents/operations/` directory.
- [x] 4.7 Delete the now-empty `docs/reference/agents/troubleshoot/` directory.
- [x] 4.8 Delete the now-empty `docs/reference/agents/` directory.

## 5. Fix inbound links to the retired subtree

- [x] 5.1 In `docs/getting-started/system-skills-overview.md`, replace the `../reference/agents/operations/project-aware-operations.md` link with `../reference/system-files/project-aware-operations.md`.
- [x] 5.2 In `docs/getting-started/easy-specialists.md`, replace the `../reference/agents/operations/project-aware-operations.md` link with `../reference/system-files/project-aware-operations.md`.
- [x] 5.3 In `docs/reference/system-files/agents-and-runtime.md`, `docs/reference/system-files/index.md`, `docs/reference/registry/index.md`, and `docs/reference/gateway/index.md`, audit every `reference/agents/` link and either re-point it at the corresponding current home (`run-phase/session-lifecycle.md`, `run-phase/backends.md`, `cli/houmao-mgr.md`, `system-files/agents-and-runtime.md`, or `system-files/project-aware-operations.md`) or remove the link if no direct successor exists.
- [x] 5.4 In the moved `docs/reference/codex-cao-approval-prompt-troubleshooting.md`, update the self-reference bullet that points at `docs/reference/agents/operations/session-and-message-flows.md` so it either points at `docs/reference/run-phase/session-lifecycle.md` or is removed.
- [x] 5.5 Grep the entire `docs/` tree for any remaining `reference/agents/` matches; resolve every match via re-point or removal so no stale references remain.

## 6. docs/reference/index.md cleanup

- [x] 6.1 In `docs/reference/index.md`, remove the `[Runtime-Managed Agents](agents/index.md)` link entry.
- [x] 6.2 In `docs/reference/index.md`, verify no remaining link points at `agents/` paths; remove any that do.

## 7. Deprecation banner on legacy backend docs

- [x] 7.1 In `docs/reference/realm_controller.md`, immediately before the `### cao_rest` (or equivalent) heading content, insert a bold-prefixed `> **Unmaintained — Deprecated Backend.** ...` banner using the wording pattern from the change design document.
- [x] 7.2 In `docs/reference/realm_controller.md`, immediately before the `### houmao_server_rest` (or equivalent) heading content, insert the same bold-prefixed banner.
- [x] 7.3 In the moved `docs/reference/codex-cao-approval-prompt-troubleshooting.md`, insert the same bold-prefixed banner at the top of the page, immediately after the H1 heading.

## 8. Verification

- [x] 8.1 Run `pixi run docs-serve` (or `mkdocs build --strict` if available in the sandbox) and confirm no broken-link warnings for any path that this change touches.
- [x] 8.2 Grep the repo for `reference/agents/` across `docs/`, `README.md`, and `CLAUDE.md`; confirm zero matches remain.
- [x] 8.3 Grep `README.md` for `Current Status`; confirm zero matches remain.
- [x] 8.4 Grep `CLAUDE.md` for `AgentPreset` and `CAO server launcher`; confirm zero matches remain.
- [x] 8.5 Run `openspec validate refresh-top-level-docs-and-claude-md --strict` and confirm the change passes.
