## Context

The previous managed-memory proposal correctly narrowed the filesystem layout to:

```text
<active-overlay>/memory/agents/<agent-id>/
  houmao-memo.md
  pages/
```

But it still treated `houmao-memo.md` as a Houmao-mutated artifact by inserting a generated pages index. That undermines the most important product boundary: the memo is the one file users and LLMs can freely edit without having to preserve generated sections.

The corrected model is closer to a small operator-visible notebook. Houmao provides stable paths, containment, and remote/local access methods. It does not author or maintain memo content.

## Goals / Non-Goals

**Goals:**
- Make `houmao-memo.md` fully user/LLM-owned free-form Markdown.
- Ensure page create/write/append/delete operations never mutate the memo as a side effect.
- Remove the memory reindex operation from CLI, gateway, pair-server, and passive-server surfaces.
- Add or standardize path-resolution responses that return:
  - the page path relative to `pages/`,
  - a memo-friendly relative link such as `pages/notes/run.md`,
  - the absolute filesystem path,
  - existence and kind metadata when available.
- Preserve page containment rules so gateway and pair-server memory operations do not become arbitrary filesystem APIs.
- Update docs and system skills so memo links to pages are described as authored references, not generated indexes.

**Non-Goals:**
- No migration or cleanup of existing `houmao-memo.md` contents.
- No recognition of old generated marker comments.
- No automatic link insertion, link repair, index generation, or Markdown parsing.
- No search database, vector index, or semantic retrieval behavior.
- No new generic artifact directory outside `pages/`.

## Decisions

### Decision: `houmao-memo.md` is entirely caller-authored content

Houmao creates `houmao-memo.md` if missing and exposes read, replace, and append operations. Those operations mutate the memo only because the caller explicitly requested a memo mutation.

Houmao does not inspect the memo for managed sections, marker comments, page links, headings, or metadata. Any old generated index text is ordinary Markdown and remains untouched unless the caller edits it.

Rationale: users and LLMs need one stable, low-friction file they can edit directly. Generated sections make that file feel like a controlled artifact and require callers to learn hidden preservation rules.

Alternative considered: keep generated markers but make them optional. Rejected because optional generation still requires ownership logic and creates ambiguity about who controls the memo body.

### Decision: Page operations are independent from memo operations

Contained page operations under `pages/` remain supported, but they do not call memo helpers. A page write changes only the page file. A page delete deletes only the addressed page path. A page list reads only `pages/`.

Rationale: this keeps operations predictable. If a user wants a page referenced from the memo, they or the LLM can add a normal Markdown link.

Alternative considered: auto-append a link only when a page is created. Rejected because even a one-line append is still unsolicited memo mutation.

### Decision: Replace reindex with path discovery

There is no page index to rebuild, so `reindex` should be removed from all public memory surfaces.

The replacement affordance is path discovery. Callers need enough information to edit a page directly or to author a memo link manually:

```json
{
  "path": "notes/run.md",
  "relative_link": "pages/notes/run.md",
  "absolute_path": "/repo/.houmao/memory/agents/researcher-id/pages/notes/run.md",
  "exists": false,
  "kind": null
}
```

Tree/list and read/write/delete responses may carry the same path metadata for existing pages. A dedicated resolve operation should also work for not-yet-existing contained page paths.

Rationale: path discovery solves the practical need that the generated index was trying to solve without taking ownership of memo content.

Alternative considered: keep `tree` only. Rejected because callers often need the full path for a page they are about to create.

### Decision: No migration behavior

This repository permits breaking changes. The implementation should not scan, remove, preserve, or transform previous generated index blocks. Existing files are filesystem state owned by users and agents.

Rationale: any migration that edits `houmao-memo.md` repeats the ownership problem. The safest correction is to stop generating content immediately.

Alternative considered: remove old generated blocks once. Rejected because that is still a tool-authored edit to a file now defined as free-form caller content.

### Decision: Keep containment as the core safety boundary

Path resolution continues to reject empty paths, absolute paths, parent traversal, symlink escapes, and NUL-containing content. Returning `absolute_path` must not weaken containment. The absolute path is an output for transparency and direct editing, not an input that bypasses the page-relative API.

Rationale: gateway and pair-server routes can expose useful filesystem handles without becoming arbitrary file managers.

Alternative considered: accept absolute page paths under `pages/`. Rejected because relative addressing keeps the API simpler and safer.

## Risks / Trade-offs

- [Risk] Users may expect a page list to appear automatically in the memo after the previous implementation. -> Update docs and tests to make authored memo links the supported behavior.
- [Risk] Memo files with stale generated index blocks may confuse users. -> Treat them as ordinary Markdown and document that Houmao no longer owns or updates them.
- [Risk] Removing `reindex` breaks callers that adopted it immediately. -> This is an intentional breaking correction before archive; callers should use `tree` or `resolve`.
- [Trade-off] Manual links are less automatic than generated indexes. -> The free-form memo ownership boundary is more important than automatic navigation.

## Migration Plan

No migration behavior is implemented.

Deployment is a direct code and documentation update:

1. Stop generating or refreshing memo index content.
2. Remove reindex commands, models, routes, clients, and tests.
3. Add page path-resolution responses and tests.
4. Update docs and skill guidance.

Rollback is a code rollback only. Existing `houmao-memo.md` and `pages/` files remain ordinary filesystem state.

## Open Questions

None. The user decision is explicit: no migration considerations.
