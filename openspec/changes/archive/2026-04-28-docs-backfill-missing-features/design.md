## Context

The `docs/` tree has fallen behind the codebase. Four recent feature areas landed without reference coverage:

1. **Degraded/stale active tmux recovery** (`a0651efa`) — `probe_tmux_backed_authority()` and the recovery helpers for `agents stop`/`relaunch` when a registry record says `active` but tmux is broken.
2. **Symlink mutation safety** (`bdc9612a`) — hardening against symlink-based path mutations during cleanup and runtime operations.
3. **Source-aware project asset registry** (`986f6a34`) — registry tracks project-owned assets for discovery and verification.
4. **Preserve relaunchable agent registry** (`6b5b66d0`) — stopped sessions retain lifecycle records for later relaunch.

The existing docs cover the happy path well (start, prompt, stop, relaunch) but omit the degraded-stale recovery branch entirely. The registry docs mention `--purge-registry` in passing without explaining when or why to use it.

## Goals / Non-Goals

**Goals:**
- Add a single, authoritative docs page for degraded/stale recovery.
- Update session-lifecycle, CLI, and subsystem reference docs to cross-reference the new page.
- Update the docs index and getting-started overview so readers can discover the material.

**Non-Goals:**
- Rewriting unaffected docs pages.
- Changing source code, APIs, or CLI behavior.
- Documenting features older than the four listed above.

## Decisions

**Where does the new page live?**
- `docs/reference/run-phase/degraded-stale-recovery.md` — alongside `session-lifecycle.md` and `backends.md` in the run-phase reference section.
- Rationale: recovery is a runtime concern, not a build-phase or subsystem concern. Placing it in run-phase keeps it near the lifecycle docs it extends.

**What structure does the new page use?**
- Four sections:
  1. **When recovery triggers** — registry says `active` but tmux session is missing or degraded.
  2. **Probe classification** — `healthy`, `degraded_missing_primary`, `stale_missing_session`.
  3. **Recovery paths** — stop vs. relaunch behavior for each classification.
  4. **Cleanup integration** — `agents cleanup session --purge-registry` for confirmed broken authority.
- Rationale: mirrors the mental model of the implementation (`probe_tmux_backed_authority()` → classify → route).

**How do we update existing pages without bloat?**
- Add a one-paragraph recovery subsection to `session-lifecycle.md` with a link to the dedicated page.
- Update `discovery-and-cleanup.md` to reference the recovery page when explaining `--purge-registry`.
- Update `houmao-mgr.md` to mention degraded/stale handling in the `agents stop` and `agents relaunch` descriptions.
- Rationale: avoids duplicating content; readers who want depth follow the link.

## Risks / Trade-offs

- **[Risk]** The new page may drift from source if the recovery logic changes. → **Mitigation**: Page is scoped to the current three-class probe model; future probe classes require an explicit docs update.
- **[Risk]** Readers may not discover the new page if cross-references are sparse. → **Mitigation**: Link from session-lifecycle, registry cleanup, managed-agent API, and the docs index.
