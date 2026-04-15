## 1. Factual Fixes

- [x] 1.1 Fix `schema_version=3` → `schema_version=4` in the mermaid diagram in `docs/getting-started/overview.md` line 13.

## 2. Mailbox Answered State Documentation

- [x] 2.1 Add `answered` to the mutable-state enumeration in `docs/reference/mailbox/contracts/canonical-model.md` (the sentence that lists "Read, starred, archived, deleted").
- [x] 2.2 Add a brief note about the `answered/` archive lane in `docs/reference/mailbox/operations/common-workflows.md`.

## 3. Writer-Team Example Cross-References

- [x] 3.1 Add a "See also" cross-reference to `examples/writer-team/` in `docs/getting-started/loop-authoring.md` near the skill-selection table.
- [x] 3.2 Add an "Examples" entry in `docs/index.md` linking to `examples/writer-team/`.
- [x] 3.3 Add `examples/writer-team/` to or adjacent to the "Runnable Demos" section in `README.md`.

## 4. Copilot Framing in Opening Text

- [x] 4.1 Update the README "What It Is" opening paragraph to acknowledge Copilot as a system-skills install target with a parenthetical qualifier.
- [x] 4.2 Update the `docs/index.md` intro to acknowledge Copilot as a skill-install surface alongside the launch-capable tools.

## 5. Validation

- [x] 5.1 Verify no remaining stale `schema_version=3` references in docs.
- [x] 5.2 Verify writer-team is reachable from both docs index and loop authoring guide.
