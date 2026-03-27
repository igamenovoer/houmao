## Context

The `docs/` directory contains 87 markdown files written during an era when Houmao was tightly coupled to an external CAO (CLI Agent Orchestrator) server. Since then, the system has evolved into an independent framework with its own backends (`local_interactive`, headless runners for Claude/Codex/Gemini), its own server (`houmao-server`, `houmao-passive-server`), and its own management CLI (`houmao-mgr`). CAO integration remains as a legacy backend (`cao_rest`) but is planned for removal.

The documentation gap is severe: 59% of doc files reference CAO, 30% reference outdated demo packs, and critical subsystems (passive server, lifecycle pipelines, build phase, TUI tracking engine) have no dedicated docs. The migration/ section describes a completed transition and is no longer useful.

The source code, however, is well-documented with module docstrings, class docstrings, and typed public APIs across all packages. This rewrite derives documentation from source, not demos.

## Goals / Non-Goals

**Goals:**

- Produce a self-consistent docs/ tree that accurately describes the current Houmao system as an independent agent orchestration framework.
- Ground all documentation in source module docstrings, public API signatures, and CLI command groups — not in demo walkthroughs or CAO narratives.
- Cover every major subsystem with at least one reference page: CLI surfaces, build phase, run phase, gateway, mailbox, TUI tracking, lifecycle, registry, passive server, terminal record, system files.
- Provide a getting-started path (architecture overview → agent definitions → quickstart) for new users who have never seen CAO.
- Remove all stale content: retired CAO docs, migration guides, demo-pack walkthrough references.

**Non-Goals:**

- Rewriting `README.md` (lives at repo root, separate update cadence).
- Modifying source code, tests, or CLI behavior.
- Updating `context/` or `magic-context/` agent context packages.
- Producing API-doc-style per-function reference (the codebase uses mypy strict + docstrings for that).
- Documenting demo packs or creating new tutorials — demos are explicitly out of scope.
- Changing or archiving existing openspec specs — they remain as historical records.

## Decisions

### D1: Derive docs from source, not demos

**Decision:** Every reference page will be written by reading the corresponding source module's docstrings, class signatures, and public API, not by describing demo walkthroughs.

**Rationale:** Demo packs are outdated and couple documentation to volatile example code. Source docstrings are maintained alongside the code and reflect the actual API surface. This also decouples docs freshness from demo maintenance.

**Alternative considered:** Rewrite demos first, then write docs around them. Rejected because the user explicitly excluded demos from scope, and demos are a moving target.

### D2: Organize reference docs by system phase + subsystem

**Decision:** Structure `reference/` as:
```
reference/
├── cli/                  (houmao-mgr, houmao-server, houmao-passive-server)
├── build-phase/          (brain-builder, recipes, adapters, overrides)
├── run-phase/            (launch-plan, session-lifecycle, backends, role-injection)
├── gateway/              (protocol, contracts, mailbox-adapter)
├── mailbox/              (protocol, filesystem, stalwart)
├── tui-tracking/         (state-model, detectors, replay)
├── lifecycle/            (completion-detection)
├── registry/             (agent-registry)
├── terminal-record/      (recording, replay)
└── system-files/         (filesystem layout)
```

**Rationale:** This mirrors the source package structure (`agents/brain_builder`, `agents/realm_controller/`, `mailbox/`, `lifecycle/`, etc.) making it easy to find the docs for a given module and to keep docs in sync when source changes.

**Alternative considered:** Organize by user journey (build → launch → interact → observe). Rejected because the subsystems are independently useful and a journey-based structure would scatter related content.

### D3: local_interactive is the primary backend; CAO mentioned only as legacy

**Decision:** All docs present `local_interactive` (tmux-backed) as the primary backend. Headless backends (`claude_headless`, `codex_headless`, `gemini_headless`) are documented as direct-CLI alternatives. The `cao_rest` and `houmao_server_rest` backends are mentioned in one section of the backends reference as legacy/compatibility paths, not threaded throughout the docs.

**Rationale:** The passive server docstring explicitly calls itself the "clean replacement" with no CAO. The `cao_rest` backend is 86KB of legacy code planned for removal. New users should not encounter CAO as a primary concept.

**Alternative considered:** Remove all CAO mentions entirely. Rejected because `cao_rest` is still functional code and the backends reference should be accurate about what exists.

### D4: Delete stale content outright rather than archiving in docs/

**Decision:** Retired CAO docs and migration guides are deleted from `docs/`. They are not moved to a `docs/archive/` subdirectory.

**Rationale:** The migration guides describe a completed CAO→Houmao transition. The retired CAO docs have already been superseded. Git history preserves them. An archive subdirectory adds clutter and creates confusion about what's current.

**Alternative considered:** Move to `docs/archive/`. Rejected because it suggests the content is still relevant.

### D5: Consolidate TUI tracking docs from three locations into one

**Decision:** TUI tracking documentation currently lives in `developer/tui-parsing/` (9 files), `reference/` (scattered), and `resources/tui-state-tracking/`. Consolidate into `reference/tui-tracking/` for the state model and detector reference, and `developer/tui-parsing/` for the architecture/maintenance developer guide.

**Rationale:** Readers currently must navigate three directory trees to understand TUI tracking. Two locations (reference for "what", developer for "how to maintain") is sufficient.

### D6: Existing mailbox and registry docs are mostly clean — light rewrite only

**Decision:** The 12 mailbox doc files and 5 registry doc files have 0–1 CAO mentions each. They receive a light pass (remove any stale references, verify accuracy against current source) rather than a full rewrite.

**Rationale:** These docs were written after the CAO decoupling and are already source-grounded. Full rewrite would be wasteful.

### D7: Developer guides rewritten without CAO transport framing

**Decision:** The `developer/tui-parsing/` guides (currently framed around "CAO transport surface" architecture) are rewritten to describe the TUI parsing stack in terms of the actual abstractions: `StreamStateReducer`, detector profiles, signal contracts, and the `shared_tui_tracking` package.

**Rationale:** The CAO transport framing was the original context but is no longer the primary execution path. The parsing stack works identically for `local_interactive` sessions.

## Risks / Trade-offs

- **[Scope creep]** → Mitigation: Strict "no code changes, no demo updates, no README" boundary. Each task scoped to specific files.
- **[Source docstrings may be incomplete]** → Mitigation: Where docstrings are thin, derive content from type signatures and module structure. Flag gaps for future docstring improvement but do not block doc creation.
- **[Existing links to deleted docs]** → Mitigation: `docs-stale-content-removal` task includes a grep pass for internal cross-references to deleted files, with link updates or removal.
- **[Large diff]** → Mitigation: Tasks are ordered so that deletion happens first (smallest cognitive load to review), then rewrites, then new content. Each task produces a reviewable unit.
- **[Accuracy of backend descriptions]** → Mitigation: Backend docs derived from `models.py` `BackendKind` literal and per-backend module docstrings, not from memory or external docs.
