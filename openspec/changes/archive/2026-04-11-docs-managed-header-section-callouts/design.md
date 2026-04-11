## Context

The managed prompt header was refactored from a monolithic block into five independently controllable sections (`identity`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, `mail-ack`). Six detailed docs pages have already been updated to reflect this. Two high-visibility entry points remain stale: the README's managed-header callout (line 349) and the docs site index entry (line 46 of `docs/index.md`).

## Goals / Non-Goals

**Goals:**

- Update the README managed-header callout to describe the section architecture, section defaults, and the `--managed-header-section` CLI surface.
- Update the docs/index.md index entry to mention per-section control.
- Keep both edits proportionate — the README is a front-door summary, not a reference page.

**Non-Goals:**

- Rewriting the full README managed-header callout into a multi-paragraph reference. The reference page at `docs/reference/run-phase/managed-prompt-header.md` already covers that.
- Updating any other docs pages — the six detailed pages are already current in the working tree.
- Changing code, tests, or specs beyond the two doc files.

## Decisions

**Decision 1: README callout stays as a single blockquote paragraph.**
The current format is `> **Managed prompt header.** ...` — one blockquote with ~3 sentences. The rewrite keeps this form factor. The five section names, their on/off defaults, and the two CLI surfaces (`--managed-header-section`, `--no-managed-header`) fit comfortably in 3-4 sentences. A longer treatment would shift the README toward reference material that belongs in the dedicated doc.

**Decision 2: Mention `automation-notice` behavior explicitly.**
The `automation-notice` section is the most operationally important one (prohibits `AskUserQuestion`, routes mailbox clarification). The current README text omits this entirely. The rewrite names the automation-notice behavior alongside identity and runtime guidance so operators scanning the README understand the most impactful default.

**Decision 3: docs/index.md gets a minimal wording change.**
The index entry is a one-line description. Adding "per-section control" or "five independently controllable sections" is sufficient to signal the feature without bloating the index.

## Risks / Trade-offs

- [Callout length] The rewritten README paragraph is slightly longer than the original. → Acceptable because the added content (section names, defaults, CLI flag) is high-value for operators scanning the README.
- [Staleness coupling] If sections are added or renamed later, the README callout will need another touch. → Mitigated by keeping the README at summary level and linking to the reference page for the canonical section list.
