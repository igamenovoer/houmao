## Why

The `docs/` directory is heavily coupled to a CAO-centric worldview that no longer reflects the system. 51 of 87 markdown files reference CAO (187 total mentions), 26 reference outdated demo packs, and entire sections (migration/, retired reference files) describe a completed transition rather than the current architecture. Meanwhile, major subsystems — passive server, lifecycle pipelines, shared TUI tracking, the build-phase brain builder — have no dedicated documentation. The docs need a ground-up rewrite derived from source code and docstrings, not from demo walkthroughs or CAO migration narratives.

## What Changes

- **BREAKING** Remove all CAO-framed reference docs (`cao_interactive_demo.md`, `cao_server_launcher.md`, `cao_shadow_parser_troubleshooting.md`, `cao_claude_shadow_parsing.md`) and the entire `migration/` section (6 files documenting a completed CAO→Houmao transition).
- **BREAKING** Remove all demo pack references from documentation. Docs will be grounded in source modules and their docstrings, not in `scripts/demo/` walkthroughs.
- Rewrite `docs/index.md` as the canonical entry point with a new TOC reflecting the restructured documentation.
- Create a new `getting-started/` section covering architecture overview, agent definition directory layout, and a source-grounded quickstart.
- Rewrite the `reference/` section organized by system phases and subsystems: CLI surfaces, build phase, run phase, gateway, mailbox, TUI tracking, lifecycle, registry, and system files.
- Rewrite `reference/realm_controller.md` (currently 77 CAO mentions) to describe the current multi-backend session model with `local_interactive` as the primary backend.
- Rewrite `developer/` guides (TUI parsing, terminal record, houmao-server internals) to remove CAO transport framing and demo references.
- Add new reference docs for undocumented subsystems: `houmao-passive-server`, lifecycle/completion detection, and consolidated TUI tracking.
- Position `houmao-mgr` and `houmao-server`/`houmao-passive-server` as the supported CLI surfaces; `houmao-cli` and `houmao-cao-server` mentioned only as deprecated compatibility entrypoints.

## Capabilities

### New Capabilities

- `docs-site-structure`: Top-level docs/ directory structure, index.md TOC, and cross-doc navigation scheme for the rewritten documentation set.
- `docs-getting-started`: New onboarding section — architecture overview (two-phase lifecycle, backend model), agent definition directory layout, and quickstart guide derived from source docstrings.
- `docs-cli-reference`: Reference documentation for the three supported CLI surfaces (`houmao-mgr`, `houmao-server`, `houmao-passive-server`) derived from their Click command groups and module docstrings.
- `docs-build-phase-reference`: Reference documentation for the build phase — `BrainBuilder`, `BuildRequest`/`BuildResult`, `BrainRecipe`, `ToolAdapter`, launch overrides — derived from `brain_builder.py` and related modules.
- `docs-run-phase-reference`: Reference documentation for the run phase — `LaunchPlan` composition, `RuntimeSessionController`, backend model (`local_interactive`, headless backends, `houmao_server_rest`), role injection, and session manifests — derived from `realm_controller/` source.
- `docs-subsystem-reference`: Consolidated reference documentation for gateway, mailbox, TUI tracking, lifecycle/completion detection, terminal record, and agent registry — each derived from their respective source module docstrings.
- `docs-developer-guides`: Rewritten developer guides for TUI parsing architecture, terminal recording, and houmao-server internals — without CAO transport framing or demo references.
- `docs-stale-content-removal`: Removal plan for retired CAO-specific docs, migration guides, and demo-pack references across all remaining files.

### Modified Capabilities

_(No existing spec-level requirements are changing. The existing documentation specs like `agents-reference-docs`, `tui-parsing-docs`, `registry-reference-docs`, etc. describe content that will be superseded by the new doc capabilities above, but their spec-level requirements are not being modified — the new docs replace them.)_

## Impact

- **docs/**: Complete restructure. ~30 files deleted/archived, ~20 files rewritten, ~15 new files created. All demo and CAO narrative framing removed.
- **No code changes**: This is a documentation-only change. Source modules, CLI entrypoints, and tests are untouched.
- **README.md**: Not in scope (lives at repo root, has its own update cadence), but the new docs should be consistent with README positioning.
- **openspec/specs/**: Existing documentation specs (`agents-reference-docs`, `tui-parsing-docs`, `registry-reference-docs`, `mailbox-reference-docs`, `agent-gateway-reference-docs`, `system-files-reference-docs`) are not modified but may become partially superseded by the new consolidated docs.
- **context/ and magic-context/**: Not in scope — these are agent context packages, not user-facing documentation.
