# Terminal Recorder Maintenance

Use this checklist when changing the terminal recorder or debugging recorder regressions.

## Recorder Lifecycle Changes

When you change startup, control, or shutdown behavior:

- keep `start`, `status`, and `stop` operating through persisted run state
- preserve the explicit multi-pane failure when `--target-pane` is omitted
- keep the final pane snapshot in the shutdown path
- keep package imports light around `houmao.terminal_record`; the runtime bridge is imported from hot CAO code paths, so eager imports can create circular dependencies

The main lifecycle coverage is in `tests/unit/terminal_record/test_service.py`.

## Capture Contract Changes

When you change artifact shape or capture semantics:

- preserve `pane_snapshots.ndjson` as the authoritative replay contract
- treat `session.cast` as operator evidence only
- keep `input_capture_level`, `visual_recording_kind`, `run_tainted`, and `taint_reasons` in the manifest
- keep passive mode non-authoritative for manual input capture

If you need new fields, add them to the manifest/labels models first, then update docs and tests together.

## Managed `send-keys` Changes

When you change the runtime control-input path:

- keep tmux delivery behavior unchanged for successful `send_input_ex()` calls
- keep recorder logging additive and best-effort
- verify that active recorder runs still append `managed_send_keys` events with timing and tmux target metadata
- do not expand the contract to claim complete capture of arbitrary third-party tmux input unless the recorder actually owns that path

The critical integration coverage is in `tests/integration/agents/realm_controller/test_cao_control_input_runtime_contract.py`.

## Replay And Labels Changes

When you change replay or labeling behavior:

- keep `analyze` live-session-free; it must read persisted pane snapshots only
- preserve stable `sample_id` references across parser/state outputs and label artifacts
- keep exported labels usable outside the original run root
- prefer adding assertions on parser/state fields over relying on free-form dialog text alone

## Docs And Spec Hygiene

When you change contracts:

- update `docs/reference/terminal_record.md` for command-level and artifact-level changes
- update this developer guide for architecture or maintenance changes
- update the OpenSpec change or synced spec if the maintained contract moved
- refresh focused tests before assuming the change is safe to archive
