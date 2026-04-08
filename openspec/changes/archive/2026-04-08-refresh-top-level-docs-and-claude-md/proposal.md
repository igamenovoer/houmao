## Why

The April 2026 refactor wave (preset→recipe+launch-profile split, `houmao-project-mgr` skill, managed prompt header, mailbox manager, system-skill renames) landed with in-PR doc updates, but several top-level framing and navigation surfaces were not swept:

- `README.md` still opens with a "Current Status" paragraph that tells readers the operator interface is unstable — that framing is now misleading because the `houmao-mgr` + `houmao-server` surface has settled around v0.4.0.
- `CLAUDE.md` in the repo root still describes the build phase in terms of the retired `AgentPreset` model, lists `config/` as "CAO server launcher config", and omits the `project/`, `passive_server/`, `mailbox/`, `lifecycle/`, `terminal_record/`, and `shared_tui_tracking/` subsystems that now exist under `src/houmao/`. This is the file future agent sessions load as project context, so staleness here silently degrades every downstream interaction.
- `docs/index.md` under-surfaces current reference pages that `docs/reference/index.md` already exposes: the managed-launch prompt-header reference, and the `agents-gateway`, `agents-turn`, `agents-mail`, `agents-mailbox`, `admin-cleanup`, and `system-skills` CLI reference pages.
- `docs/reference/agents/` is a dedicated runtime-managed-agent subtree that predates the April refactors. Its contract, operations, and internals pages now duplicate material covered more accurately by `docs/reference/run-phase/`, `docs/reference/system-files/`, and `docs/reference/cli/`, and its framing still leans on pre-project-overlay vocabulary.
- The `cao_rest` and `houmao_server_rest` backend sections of `docs/reference/realm_controller.md` are still documented as if maintained, but the repo policy is now to leave them as deprecated escape hatches without active doc upkeep — readers have no signal that the content may be wrong.

## What Changes

- **BREAKING** Retire the `docs/reference/agents/` reference subtree. Delete `index.md`, `contracts/public-interfaces.md`, `internals/state-and-recovery.md`, and `operations/session-and-message-flows.md` outright — their material is already covered by `docs/reference/run-phase/session-lifecycle.md`, `docs/reference/run-phase/backends.md`, `docs/reference/system-files/agents-and-runtime.md`, and `docs/reference/cli/houmao-mgr.md`. No compatibility redirects.
- **BREAKING** Move `docs/reference/agents/operations/project-aware-operations.md` to `docs/reference/system-files/project-aware-operations.md` and update every inbound link (in `docs/getting-started/system-skills-overview.md`, `docs/getting-started/easy-specialists.md`, any other references) to the new path.
- **BREAKING** Move `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md` to `docs/reference/codex-cao-approval-prompt-troubleshooting.md` and prepend a prominent "Unmaintained — Deprecated Backend" banner stating the content may be incorrect and is retained as a historical escape hatch only.
- Remove the "Current Status" section (and its surrounding framing sentence) from `README.md`.
- Refresh `CLAUDE.md`:
  - Replace the `AgentPreset` wording in the Build phase description with the current recipe + launch-profile vocabulary.
  - Add `project/`, `passive_server/`, `mailbox/`, `lifecycle/`, `terminal_record/`, and `shared_tui_tracking/` to the Source Layout section.
  - Drop the `config/ — CAO server launcher config` example and replace it with a current, non-CAO description.
- Update `docs/index.md` to:
  - Add a top-level link to `reference/run-phase/managed-prompt-header.md` under the Run Phase section.
  - Add top-level links to the `reference/cli/agents-gateway.md`, `agents-turn.md`, `agents-mail.md`, `agents-mailbox.md`, `admin-cleanup.md`, and `system-skills.md` reference pages under CLI Surfaces.
  - Remove the `reference/agents/index.md` link (the subtree no longer exists).
- Update `docs/reference/index.md` to remove the `reference/agents/*` links and point any residual "runtime-managed agents" framing at the current `run-phase/` and `system-files/` pages.
- Add a prominent "Unmaintained — Deprecated Backend" banner to the `cao_rest` and `houmao_server_rest` sections of `docs/reference/realm_controller.md` stating that these backends remain in the code as escape hatches but their documentation is frozen and may be incorrect.

## Capabilities

### New Capabilities

- `docs-project-instructions-file`: CLAUDE.md accuracy bar — the repo-root `CLAUDE.md` must describe the current build/run phases, current source layout (including `project/`, `passive_server/`, `mailbox/`, `lifecycle/`, `terminal_record/`, `shared_tui_tracking/`), and must not describe retired constructs (`AgentPreset`, CAO launcher config) as current.

### Modified Capabilities

- `agents-reference-docs`: Retired. Every existing requirement moves to REMOVED; the `docs/reference/agents/` subtree no longer exists and its material is owned by `docs-run-phase-reference`, `system-files-reference-docs`, and `docs-cli-reference`.
- `docs-project-aware-operations`: Update the required page path from `docs/reference/agents/operations/project-aware-operations.md` to `docs/reference/system-files/project-aware-operations.md`; the resolution rules and required content remain the same.
- `docs-site-structure`: Update the `docs/index.md` navigation requirements to include the managed-prompt-header reference and the six CLI reference pages currently missing from the top-level index, and to drop the `reference/agents/` subtree link.
- `docs-readme-system-skills`: Add a requirement that `README.md` SHALL NOT contain a "Current Status" stability paragraph asserting interfaces are changing.
- `docs-run-phase-reference`: Add a requirement that `docs/reference/realm_controller.md` SHALL mark the `cao_rest` and `houmao_server_rest` backend sections with an "unmaintained — may be incorrect" deprecation banner visible before any descriptive content.

## Impact

- Deleted files: `docs/reference/agents/index.md`, `docs/reference/agents/contracts/public-interfaces.md`, `docs/reference/agents/internals/state-and-recovery.md`, `docs/reference/agents/operations/session-and-message-flows.md`, and the now-empty `docs/reference/agents/` directory.
- Moved files: `docs/reference/agents/operations/project-aware-operations.md` → `docs/reference/system-files/project-aware-operations.md`; `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md` → `docs/reference/codex-cao-approval-prompt-troubleshooting.md`.
- Edited files: `README.md` (remove Current Status), `CLAUDE.md` (source layout + terminology), `docs/index.md` (navigation sweep), `docs/reference/index.md` (drop agents subtree links), `docs/reference/realm_controller.md` (deprecation banner), `docs/getting-started/system-skills-overview.md` and `docs/getting-started/easy-specialists.md` (relink project-aware-operations).
- Affected OpenSpec main specs on archive: `agents-reference-docs` (retired), `docs-project-aware-operations`, `docs-site-structure`, `docs-readme-system-skills`, `docs-run-phase-reference`.
- No code changes. No changes to `src/houmao/**` source. No backend behavior changes. `mkdocs.yml` navigation is not curated as part of this change (user decision: "just update what is necessary").
