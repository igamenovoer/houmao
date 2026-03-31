## Why

The `docs/reference/cli/houmao-mgr.md` page has grown into a 327-line monolith covering 100+ commands across 6 top-level groups, while only some command families got dedicated reference pages (agents-gateway, agents-turn, agents-mail, agents-mailbox, admin-cleanup). The entire `project` subsystem — now the primary getting-started path — has no dedicated page. Meanwhile, several reference files sit as flat orphans at `docs/reference/` with content overlap (e.g., `realm_controller.md` vs `run-phase/session-lifecycle.md`), and a 5-line archived stub remains published.

## What Changes

- **Split `houmao-mgr.md`** into focused CLI reference pages for each undocumented command group: `project`, `server` (mgr subcommands), `mailbox` (standalone admin), `brains`, and `agents-cleanup`. Slim the monolith down to an overview + command tree + links.
- **Create `docs/reference/cli/project.md`** — the largest gap. Covers `project init`, `project status`, `project agents tools` (claude/codex/gemini with setups + auth), `project agents roles` (with presets), `project easy specialist/instance`, and `project mailbox`.
- **Reorganize flat reference files**: move `realm_controller_send_keys.md` → `agents/operations/send-keys.md`, move `managed_agent_api.md` → `agents/contracts/api.md`, move `cli.md` → `cli/index.md`.
- **Merge overlapping content**: fold `realm_controller.md` into `run-phase/session-lifecycle.md` and delete the original.
- **Delete stubs**: remove `houmao_server_agent_api_live_suite.md` (5-line redirect with no independent value).
- **Clean up deprecated entrypoint noise** in `cli.md` → `cli/index.md` by isolating `houmao-cli` and `houmao-cao-server` references into a clearly separated "Deprecated Entrypoints" section.

## Capabilities

### New Capabilities
- `docs-cli-dedicated-pages`: Extract five new dedicated CLI reference pages (project, server, mailbox, brains, agents-cleanup) from the houmao-mgr monolith and slim the monolith to an overview hub.
- `docs-reference-restructure`: Move, merge, and delete reference files to eliminate flat-file orphans, content overlap, and archived stubs.

### Modified Capabilities

## Impact

- `docs/reference/cli/` — 5 new files, 1 file slimmed, 1 file moved+renamed
- `docs/reference/` — 3 files moved to subdirectories, 1 merged and deleted, 1 deleted
- `mkdocs.yml` — may need `nav:` additions if auto-discovery doesn't handle the new structure
- `docs/reference/index.md` — link updates to reflect new file locations
- No code changes. No API changes. Pure documentation restructuring.
