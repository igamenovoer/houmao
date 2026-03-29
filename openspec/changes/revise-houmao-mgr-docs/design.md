## Context

`docs/reference/` covers CLI, subsystem (agents, gateway, registry, mailbox), and system-files topics. As `houmao-mgr` absorbed more and more of the operator surface (brains build flag rename, `houmao-mgr agents` replacing direct `realm_controller` module use, gateway send-keys moving under `agents gateway send-keys`), several pages were never updated.

The outdated content falls into four layers that require different editorial approaches:

| Layer | Description | Files |
|---|---|---|
| A — Wrong flags | Brains build option table and example command use old flag names | `houmao-mgr.md`, `houmao_server_pair.md` |
| B — Surface shift | Operator-facing reference pages show raw `realm_controller` module CLI as primary examples | `public-interfaces.md`, `discovery-and-cleanup.md`, `realm_controller_send_keys.md` |
| C — Capability gap | Stalwart mailbox transport is not exposed via `houmao-mgr agents launch`; the doc should name that gap | `stalwart-setup-and-first-session.md` |
| D — Diagram verbs | Mermaid sequence diagrams use `start-session`/`send-prompt`/`stop-session` abstract verbs from the old module CLI | 5 ops/internals docs |
| E — Minor stale | Single mention of `build-brain` instead of `houmao-mgr brains build` | `roots-and-ownership.md` |

## Goals / Non-Goals

**Goals:**
- Correct all wrong flag names in CLI reference material
- Make `houmao-mgr agents` the documented primary operator path in all operator-facing reference pages
- Update Mermaid diagrams to match the current CLI vocabulary so new users following examples arrive at working commands
- Document the stalwart access gap explicitly

**Non-Goals:**
- Source code changes
- Adding documentation for new features not yet implemented
- Rewriting purely architectural or internal documentation where abstract runtime verbs are the right abstraction (e.g., `agents/index.md` Key Terms section)
- Changing the stalwart workflow itself — the note documents the gap but does not bridge it

## Decisions

### Decision 1: Low-level section rather than deletion for Layer B

Raw `python -m houmao.agents.realm_controller` access still works and remains relevant for power users, scripting, and future paths that have no `houmao-mgr` equivalent yet (e.g., stalwart). Deleting those examples would break users with existing scripts or advanced targeting needs.

Chosen approach: move raw module examples to a clearly-labelled "Low-level access" section at the bottom of each affected page, with a brief note that `houmao-mgr agents` is the preferred operator surface.

Alternative considered: delete raw examples entirely. Rejected because stalwart and manifest-path control have no houmao-mgr equivalents yet.

### Decision 2: Diagram verbs use full `houmao-mgr agents ...` command form, not shortened aliases

Mermaid labels have limited width but abbreviating to `agents prompt` without the `houmao-mgr` prefix could mislead readers into thinking there is a standalone `agents` binary. Use `houmao-mgr agents launch` etc., wrapping with `<br/>` if needed.

### Decision 3: Delta specs modify `docs-cli-reference` and `docs-subsystem-reference`, no new spec

The two affected doc specs already have accuracy requirements. The delta specs add explicit scenario-level requirements that pin flag names and operator surface primacy. No new top-level spec is warranted because the capability boundaries have not moved — the change is a correction, not a capability extension.

## Risks / Trade-offs

- **Risk: Mermaid label overflow** → Use `<br/>` line breaks in node labels; test that diagrams render in GitHub Markdown before committing.
- **Risk: Raw module examples become stale again** → After this revision, the low-level section clearly labels its stability; documentation owners should maintain it alongside CLI changes.
- **Risk: stalwart note becomes incorrect if/when houmao-mgr exposes the flag** → The note should be written as a present-tense gap notice, not a permanent architectural statement, so it is easy to remove when the gap closes.
