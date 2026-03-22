## 1. Authoring Plan And Operator Guidance

- [x] 1.1 Update the shared TUI demo-pack maintainer docs to describe the real-fixture authoring workflow from live scouting through canonical promotion, including the post-labeling `review.mp4` generation step.
- [x] 1.2 Document the first-wave Claude and Codex case matrix with concrete prompts, operator actions, and target transition families.
- [x] 1.3 Document the canonical promoted artifact set versus temporary authoring artifacts that stay under `tmp/`.

## 2. Claude First-Wave Real Fixtures

- [x] 2.1 Capture temporary Claude authoring runs under `tmp/demo/shared-tui-tracking-demo-pack/authoring/` for `explicit_success`, `interrupted_after_active`, `slash_menu_recovery`, and `tui_down_after_active`.
- [x] 2.2 Author full span-based ground-truth labels for the Claude authoring runs directly from `recording/pane_snapshots.ndjson` plus supporting runtime observations.
- [x] 2.3 Run `recorded-validate --skip-video` for the Claude authoring runs and fix labels or recapture until replay mismatches reach zero.
- [x] 2.4 After recording and state labeling are complete, run full recorded validation to generate `review.mp4` for the passing Claude authoring runs and inspect the generated summary and issue artifacts before promotion.
- [x] 2.5 Promote the passing Claude canonical artifact sets into `tests/fixtures/shared_tui_tracking/recorded/`.

## 3. Codex First-Wave Real Fixtures

- [x] 3.1 Capture temporary Codex authoring runs under `tmp/demo/shared-tui-tracking-demo-pack/authoring/` for `explicit_success`, `interrupted_after_active`, and `tui_down_after_active`.
- [x] 3.2 Author full span-based ground-truth labels for the Codex authoring runs directly from `recording/pane_snapshots.ndjson` plus supporting runtime observations.
- [x] 3.3 Run `recorded-validate --skip-video` for the Codex authoring runs and fix labels or recapture until replay mismatches reach zero.
- [x] 3.4 After recording and state labeling are complete, run full recorded validation to generate `review.mp4` for the passing Codex authoring runs and inspect the generated summary and issue artifacts before promotion.
- [x] 3.5 Promote the passing Codex canonical artifact sets into `tests/fixtures/shared_tui_tracking/recorded/`.

## 4. Corpus Finalization

- [x] 4.1 Replace or archive the lightweight authored fixture directories that are superseded by promoted real captures.
- [x] 4.2 Run corpus-wide recorded validation against the committed fixture tree after the promotion batch and confirm the first-wave corpus remains mismatch-free.
- [x] 4.3 Update the maintained specs or docs if the real authoring pass reveals detector semantics or labeling rules that need to be clarified for future fixture work.
