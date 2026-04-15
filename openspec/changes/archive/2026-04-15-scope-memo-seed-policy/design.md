## Context

Launch profiles may store one memo seed with source kind `memo` or `tree` and policy `initialize`, `replace`, or `fail-if-nonempty`. The current runtime implementation loads the seed payload into three pieces: memo text, page directories, and page files. It then treats `replace` as a whole-memory operation by clearing all pages and writing the memo file even when the seed source is memo-only.

That implementation is internally simple, but it conflicts with the user-facing CLI model. `--memo-seed-text` and `--memo-seed-file` are memo-only source forms. A user who pairs one of those sources with `--memo-seed-policy replace` reasonably expects the memo file to be replaced, not unrelated pages to be cleared.

## Goals / Non-Goals

**Goals:**

- Make memo seed policies operate only on components represented by the seed source.
- Preserve unrelated memo or page state when the seed source omits that component.
- Keep existing policy names and CLI flags.
- Preserve empty memo seeds as a supported way to intentionally set `houmao-memo.md` to empty.
- Keep launch-time seed application before prompt composition and provider startup.

**Non-Goals:**

- No new policy names, flags, or seed source forms.
- No change to memo seed storage format in the project catalog.
- No migration for existing stored memo seeds.
- No attempt to infer page links from memo Markdown or synchronize memo links with pages.

## Decisions

### Component Presence Drives Scope

The runtime will derive a seed application scope from the loaded payload:

- `memo` source kind always touches `houmao-memo.md`.
- `tree` source kind touches `houmao-memo.md` only when the seed directory contains `houmao-memo.md`.
- `tree` source kind touches pages only when the seed directory contains `pages/`.

Alternatives considered:

- Keep whole-memory `replace`: rejected because it clears pages for memo-only seeds.
- Add separate policy names such as `replace-memo`: rejected because the source form already communicates the component being edited, and new names increase CLI complexity.

### Policy Checks Are Scoped

`initialize` and `fail-if-nonempty` will inspect only touched components. A memo-only seed checks only whether `houmao-memo.md` has non-whitespace content. A pages-only seed checks only whether `pages/` has authored entries. A seed that touches both components checks both.

This keeps the policy meanings stable while changing their unit of application from "entire managed memory" to "represented seed components."

### Replacement Mutates Only Touched Components

`replace` will clear and rewrite pages only when the seed touches pages. It will write `houmao-memo.md` only when the seed touches memo. A tree seed with an empty `pages/` directory touches pages and therefore intentionally clears the existing page tree under `replace`.

The empty memo case remains explicit: `--memo-seed-text '' --memo-seed-policy replace` touches memo and writes an empty memo file without touching pages.

### Result Metadata Remains Stable

The existing memo seed result payload can remain compatible: `status`, `source_kind`, `policy`, `memo_written`, `page_file_count`, and `page_directory_count` still describe what happened. Implementation may refine `memo_written` so it is true only when memo is represented and written, not merely because replacement mode was selected.

## Risks / Trade-offs

- Existing users may rely on memo-only `replace` clearing pages → This is a behavior change, but the project is explicitly unstable and the new behavior matches the CLI source semantics better.
- Existing docs or skills may still describe whole-memory replacement → Update launch-profile docs, CLI reference wording, and memory skill guidance in the same change.
- Component-scoped `initialize` can now apply a memo seed even when pages exist → This is intentional; pages are not part of a memo-only seed. Tests should cover that existing pages survive.
- Pages-only replacement needs a way to represent "touch pages, but seed no files" → An empty `pages/` directory inside a directory seed should remain valid when accompanied by supported top-level seed content rules, and under `replace` it clears pages without touching memo.
