## Why

Several docs and the project README have fallen out of sync with recent 0.7.0rc1/rc2 changes. The architecture overview references `schema_version=3` while the code is at v4, the mailbox canonical model omits the new `answered` state, the `examples/writer-team/` template has no docs-site presence, and the Copilot system-skills install target isn't reflected in the opening framing of the README or docs index.

## What Changes

- Fix stale manifest `schema_version=3` → `schema_version=4` in `docs/getting-started/overview.md` mermaid diagram.
- Add `answered` / `is_answered` state to the mailbox canonical model reference at `docs/reference/mailbox/contracts/canonical-model.md` and mention the `answered/` archive lane in `docs/reference/mailbox/operations/common-workflows.md`.
- Reference the `examples/writer-team/` template from the loop authoring guide (`docs/getting-started/loop-authoring.md`) and the docs index (`docs/index.md`).
- Add writer-team to the README "Runnable Demos" section (or add a sibling "Examples" subsection).
- Acknowledge Copilot as a system-skills install target in the README opening paragraph and docs index intro (without implying it is a launch backend).

## Capabilities

### New Capabilities

_None — this change is purely documentation corrections and additions._

### Modified Capabilities

- `docs-getting-started`: Fix schema version in overview, add writer-team cross-reference in loop authoring guide.
- `docs-site-structure`: Add examples entry and writer-team link in `docs/index.md`.
- `readme-structure`: Fix README demos/examples section and opening framing for Copilot.

## Impact

- `docs/getting-started/overview.md` — factual fix.
- `docs/getting-started/loop-authoring.md` — new cross-reference.
- `docs/reference/mailbox/contracts/canonical-model.md` — contract gap fix.
- `docs/reference/mailbox/operations/common-workflows.md` — workflow gap fix.
- `docs/index.md` — new entry.
- `README.md` — framing and demo section updates.
- No code changes, no test impact, no breaking changes.
