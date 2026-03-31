## Context

The `docs/` directory has grown to 88 files (~12,600 lines) through incremental feature additions. Most subsystem docs (gateway, mailbox, registry, TUI tracking) are well-organized under dedicated subdirectories with index → contracts → internals → operations structure. However, the CLI reference area has not kept pace with the actual `houmao-mgr` command surface, and several reference files accumulated at the `docs/reference/` root without clear organizational homes.

Current state:
- `houmao-mgr.md` is a 327-line monolith covering all 6 top-level command groups (~100+ leaf commands). Only 5 of ~11 command families have dedicated pages.
- The `project` subsystem (the primary onboarding path) has zero dedicated documentation — it's inline bullet points in the monolith.
- 6 flat files sit at `docs/reference/` root; some overlap with organized subdirectory content.
- `mkdocs.yml` uses auto-discovery (no `nav:` section), so file placement determines navigation.

## Goals / Non-Goals

**Goals:**
- Every `houmao-mgr` command group gets a dedicated CLI reference page at the same depth as existing pages (agents-gateway.md, agents-turn.md, etc.).
- Slim `houmao-mgr.md` to an overview hub: command tree + brief descriptions + links to dedicated pages.
- Eliminate content overlap between `realm_controller.md` and `run-phase/session-lifecycle.md`.
- Move orphaned flat files into their logical subdirectories.
- Remove the archived stub `houmao_server_agent_api_live_suite.md`.
- Cleanly separate deprecated entrypoint documentation from current CLI surface.

**Non-Goals:**
- Rewriting subsystem docs (gateway, mailbox, registry, TUI tracking) — these are already well-organized.
- Adding new conceptual or tutorial content beyond what currently exists.
- Changing `mkdocs.yml` theme, plugins, or build configuration.
- Touching developer guides (`docs/developer/`).
- Updating or removing legacy backend documentation in `run-phase/backends.md` — those are correctly labeled.

## Decisions

### 1. One dedicated page per command group under `cli/`

Each undocumented command group becomes its own file: `project.md`, `server.md`, `mailbox.md`, `brains.md`, `agents-cleanup.md`. This mirrors the existing pattern (agents-gateway.md, agents-turn.md, etc.) and keeps each page focused and scannable.

**Alternative considered**: Keep the monolith and add anchored sections. Rejected because it doesn't improve navigation — auto-discovery can't produce sidebar entries for anchors within a single file.

### 2. `cli.md` becomes `cli/index.md`

The module-level CLI entry points doc belongs with the other CLI reference files. As `cli/index.md` it becomes the section hub under auto-discovery.

**Alternative considered**: Rename to `cli/overview.md`. Rejected because MkDocs material uses `index.md` as the section landing page when `navigation.indexes` is enabled (which it is).

### 3. Merge `realm_controller.md` into `run-phase/session-lifecycle.md`

Both documents cover session lifecycle, InteractiveSession protocol, start/resume mechanisms, and backend types. Merging eliminates ~60% content duplication. The unique content from `realm_controller.md` (high-level orchestration overview, CLI surface note) folds into existing sections of `session-lifecycle.md`.

### 4. Move flat files to logical subdirectories

- `realm_controller_send_keys.md` → `agents/operations/send-keys.md` (it documents session interaction, not infrastructure)
- `managed_agent_api.md` → `agents/contracts/api.md` (it's an API contract document with route/payload shapes)
- `houmao_server_pair.md` stays at root — it's a top-level foundational concept that serves as the primary architecture entry point

### 5. Internal cross-reference updates only

All internal `[text](path)` links in moved/renamed files and files that reference them will be updated. No external URL changes since the site uses `use_directory_urls: true` and we're not changing the URL scheme.

## Risks / Trade-offs

- **[Stale external links]** → Any bookmarks to old file locations will break. Mitigation: This is an internal docs site with low external link traffic; the MkDocs build with `strict` mode will catch broken internal links.
- **[Merge loses nuance]** → Folding `realm_controller.md` into `session-lifecycle.md` could make the latter too long. Mitigation: The merge adds ~80 lines of unique content to a 222-line doc; the result (~300 lines) is still manageable and shorter than `houmao_server_pair.md` (417 lines).
- **[Navigation auto-discovery order]** → Without explicit `nav:` in mkdocs.yml, file alphabetical order determines sidebar. Mitigation: The new filenames are chosen to sort naturally (agents-cleanup, brains, mailbox, project, server). If ordering is unacceptable post-implementation, a `nav:` section can be added later as a separate change.
