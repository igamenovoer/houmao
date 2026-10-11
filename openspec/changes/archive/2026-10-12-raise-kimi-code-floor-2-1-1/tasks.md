# Tasks

## 1. Registry floor cut

- [x] 1.1 Add `UnsupportedToolVersionError` (app id, observed version, floor) to `shared_tui_tracking/registry.py` and make `_select_best_registration` raise it when an app has registrations but no compatible and no fallback one. Verify: unit test resolving `kimi_code` below floor and with unparseable version raises; claude/codex fallback behavior unchanged (`pixi run pytest tests/unit/shared_tui_tracking -q`).
- [x] 1.2 Replace the kimi registrations with a single entry (minimum `(2, 1, 1)`, maximum `None`, factory `KimiCodeSignalDetectorV2_1_X`) and remove the kimi fallback registration; delete `FallbackKimiCodeSignalDetector` and `KimiCodeSignalDetectorV0_34_PLUS`; add optional `qualified_through_version` to `DetectorProfileRegistration` and surface it in resolved-profile payloads/notes. Verify: registry unit tests cover floor resolve, below-floor error, unparseable error, silent above-floor resolve with qualified-through metadata.
- [x] 1.3 Contain the error at call sites: tracker/session construction propagates to the initiating operation; the server TUI supervisor catches it per session and marks that session's tracking errored without killing the poll loop. Verify: unit test or integration check that a below-floor kimi session reports an errored/unsupported tracking posture while other sessions track normally.

## 2. Detector promotion

- [x] 2.1 Move the campaign candidate (`scripts/explore/kimi-code-tui-parsing/campaign_lib/patches.py`, v3) into `src/houmao/shared_tui_tracking/apps/kimi_code/profile.py` as `KimiCodeSignalDetectorV2_1_X` with `qualified_through_version = "2.1.1"`: spinner-union busy evidence, 2.1.x activity labels (including `… Agent Running (…)` subagent rows and `Compacting context…` bullet), modal detection (approvals, question dialog, goal-start prompt) as `modal_blocked` active evidence, composer-accepts-while-busy acceptance, stale-interrupt suppression, live-edge-scoped queue hints. Verify: `pixi run typecheck` and `pixi run lint` clean; detector unit tests from refreshed fixtures pass.
- [x] 2.2 Update exports in `shared_tui_tracking/detectors.py` and `shared_tui_tracking/__init__.py` (drop the removed classes, add the new one, repoint the `KimiCodeSignalDetector` alias). Verify: `pixi run test` green.

## 3. Parser modal coverage and honest preset version

- [x] 3.1 In `server/tui/parser.py`, add the `Trust this folder?` startup-modal needle and map the question dialog and goal-start prompt to `awaiting_operator`/`modal`; thread the resolved detector version into the kimi parse path so `parser_preset_version` reflects it (analyze path passes `observed_version`; live path uses the session's resolved profile version). Verify: parser unit tests for trust modal, question dialog, goal prompt, and preset-version provenance.
- [x] 3.2 Mirror the same modal branches in `terminal_record/service.py::_parse_kimi_snapshot_payload` so recorded replay parser output matches the live parser. Verify: analyze on the campaign session-1 recording emits `startup_modal` for the trust span and session-2 emits modal contexts for approval/question spans.

## 4. Fixtures and qualification

- [x] 4.1 Refresh `tests/fixtures/shared_tui_tracking/kimi_code/*.txt` slices from the frozen campaign recordings (idle, editing, busy-thinking, busy-tool, approval, plan review, question dialog, trust modal, queue, interrupt-resume), recording provenance to the run roots in each fixture header or a sidecar README. Verify: fixture consumers updated and green under `pixi run test`.
- [x] 4.2 Add a qualification test that replays both campaign session recordings (`tmp/houmao-dev-tui-testing/2026-10-10-kimi-2.1.1-session1-lifecycle` and `…-session2-attempt-002`, copied into `tests/fixtures/` with their frozen labels) through production replay and asserts zero false-ready and zero false-busy plus >=99% agreement on `surface_accepting_input` and `surface_ready_posture`. Verify: the test fails on the pre-change detector and passes on the new one.

## 5. Campaign wrap-up and docs

- [x] 5.1 Update the campaign artifacts: mark KQ-2 closed (escape channels dead via tmux capture, evidence in iteration 1 Arm B), record the modal `turn_phase=active`-with-blocked convention as the labeling-rubric convention going forward, and link this change from the campaign README. Verify: campaign docs render and cross-link.
- [x] 5.2 Sweep docs and skills for kimi version references that now contradict the floor (`skillset/dev/`, `docs/`, `tools/terminal_record/README.md` stale paths noted during the campaign). Verify: `grep -R "0\.23\|0\.34" docs/ skillset/ tools/` returns no version-support claims; `pixi run docs-build` passes if docs changed.
- [x] 5.3 (scope addition surfaced during apply) Move the launch-side kimi floor to match the tracking floor — `launch_policy/registry/kimi.yaml` strategies renamed to `kimi-unattended-2.1-plus` / `kimi-tui-unattended-2.1-plus` with `supported_versions: ">=2.1.1"`, `launch_plan.py` and `brain_builder.py` payloads and error text updated, launch tests re-stubbed to 2.1.1. Rationale: the user directive is that nothing below 2.1.1 is supported; a launch floor at 0.34 would let below-floor kimi launch managed and then fail loudly only in tracking, and the 5.2 docs sweep would contradict the launch code.

## Workflow follow-up

- Regenerate the maintained 20 fps kimi corpus under the retargeted `kimi-tui-signal-corpus` spec (separate change; this change's 5 fps campaign captures seed fixtures only).
- Open KQ-3 (hooks / stream-json event channels as a ground-truth oracle) if future qualification wants machine-checked labels.
