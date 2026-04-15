## Context

Launch profiles are catalog-backed, operator-owned birth-time configuration. They already store prompt overlays as managed content references and apply profile defaults before direct launch-time overrides. Managed-agent memo state is resolved per agent id under the active overlay, with one fixed `houmao-memo.md` file and one contained `pages/` directory. The current memo contract deliberately treats memo text and page links as caller-owned Markdown, and it avoids generated indexes or implicit memo mutations.

The missing piece is deterministic launch-time initialization of that memo state. Today an operator can put setup context into the role prompt or prompt overlay, but that does not create `pages/`, does not persist as memo state before the first turn, and asks the model to perform bookkeeping that Houmao can safely do before startup.

## Goals / Non-Goals

**Goals:**

- Let easy profiles and explicit launch profiles seed `houmao-memo.md` and contained `pages/` before a profile-backed managed launch starts.
- Use public terminology based on `memo`, such as `memo_seed` and `--memo-seed-file`; do not introduce public `memory_seed` language.
- Support three source forms: inline memo text, one Markdown memo file, and one directory shaped like the managed memo tree.
- Preserve existing memo ownership rules by treating a memo seed as explicit operator-authored content, not generated indexes or implicit side effects.
- Avoid surprise data loss with a conservative default policy for existing non-empty memo/page state.
- Keep seed payloads in catalog-managed content files or trees rather than inline SQLite text or absolute user paths.

**Non-Goals:**

- Do not add live runtime memo edits, gateway memo routes, or pair-server memo APIs beyond the existing surfaces.
- Do not create automatic memo indexes, link repair, page taxonomies, or generated memo sections.
- Do not support provider-native memory systems.
- Do not apply memo seeds to direct non-profile launches in this change.
- Do not merge seeded pages into non-empty existing pages on a file-by-file basis; the launch policy decides whether the seed applies as a unit.

## Decisions

### Store memo seeds as managed content references

Add a new catalog content kind for memo seeds and store a launch-profile reference to either one file or one tree. Inline text and `--memo-seed-file` normalize into a file-backed seed whose content becomes `houmao-memo.md`. `--memo-seed-dir` snapshots a tree that may contain root `houmao-memo.md` and a `pages/` subtree.

Rationale: this matches the managed-content direction already used by prompt overlays and auth/setup trees while avoiding large Markdown payloads in SQLite. It also prevents launch profiles from retaining absolute source file paths that may be machine-specific.

Alternative considered: store inline text directly in the launch profile row. That is simpler for text seeds but does not handle directory seeds cleanly and would make large memo content awkward to inspect and preserve.

### Use one memo seed policy with conservative default initialization

Supported policies:

- `initialize`: default. Apply the seed only when `houmao-memo.md` is missing or empty and `pages/` is missing or empty.
- `replace`: delete and rewrite the memo and pages from the seed for each profile-backed launch.
- `fail-if-nonempty`: abort launch if the target memo or pages already contain content.

Rationale: launch profiles commonly reuse a stable agent id, so relaunch should not erase accumulated memo state unless the operator explicitly asks for destructive replacement. A single policy is easier to reason about than partial merge flags.

Alternative considered: always overwrite on launch. That makes demos reproducible but is risky for long-lived agents because a normal relaunch could destroy useful memo state.

### Apply memo seeds after identity resolution and before runtime startup

The launch flow already resolves managed identity before computing the memo paths. The seed should apply after identity and memo path resolution, after any force takeover cleanup, and before the provider runtime starts or the session is published.

Rationale: the seed target depends on the authoritative agent id and active overlay. Applying before provider startup guarantees the managed header's memo cue points at already-materialized content.

Alternative considered: apply the seed after session publication through the gateway or CLI memo APIs. That would expose a short live window where the agent can start before its memo is initialized and would make launch completion depend on post-start messaging.

### Validate directory seeds as memo-shaped trees

A directory seed is valid when it contains at least one supported entry and no unsupported top-level entries. Supported entries are:

- `houmao-memo.md`
- `pages/`

All page files must be UTF-8 text, must not contain NUL bytes, and must resolve below the contained `pages/` directory. Symlinks are rejected in seed sources. Empty directories may be copied only under `pages/` when they are part of the authored seed tree.

Rationale: this reuses the current memo/page containment model and prevents directory seeds from becoming an arbitrary file-copy feature into `.houmao/memory`.

Alternative considered: copy the tree wholesale into the memo root. That would be faster to implement but would violate the fixed memo root contract and make it easy to smuggle unrelated files beside `houmao-memo.md`.

### Surface memo seed metadata without leaking full payloads by default

Profile `get` and list payloads should report whether a memo seed is present, its source kind (`memo` or `tree`), and its policy. They should not print full memo text or page contents by default. The compatibility projection may include managed content paths for inspection, but profile-backed launch should use catalog references as authoritative state.

Rationale: profile inspection should remain concise and secret-conscious. Memo content is not credential material, but it can contain operator notes or task context that should not appear in every profile listing.

Alternative considered: inline seed text into projected launch-profile YAML. That is convenient for tiny text seeds but does not scale to tree seeds and diverges from the catalog-managed source of truth.

## Risks / Trade-offs

- Existing memo state may cause default `initialize` seeds to be skipped silently if operators expected replay on each launch. Mitigation: report memo seed status in launch completion or structured output, and document `replace` for reproducible reset workflows.
- `replace` can destroy useful memo/page content. Mitigation: require the explicit stored `replace` policy, document it as destructive, and cover it with focused tests.
- Catalog schema migration touches launch-profile storage. Mitigation: add a narrow migration from the current schema version and keep missing memo seed columns equivalent to “no seed”.
- Directory seed validation may reject user trees that contain helper files such as `README.md`. Mitigation: document the exact accepted tree shape and fail with a clear path-specific message.
- Applying seeds inside shared launch code affects both easy and explicit profile-backed launch paths. Mitigation: implement seed resolution as a small helper with unit tests, then call it from the existing shared launch path using profile-derived input.
