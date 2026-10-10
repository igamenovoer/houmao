## 1. Trust-Record Writer

- [x] 1.1 Add a Kimi workspace-trust module (sibling to `src/houmao/agents/kimi_system_prompt.py`) implementing `encodeWorkDirKey` parity in Python (path normalization, slugify with the 40-char truncation and edge-case rules, sha256 prefix) and `ensure_kimi_workspace_trust(home_path, workdir)` writing the canonical `{"root", "trustedAt"}` record by atomic replacement under `<home>/workspace-trust/`, returning typed provenance (state, path, workspace key).
- [x] 1.2 Add unit tests pinning the verified live vector (`run-20260809T123938Z` workdir → `wd_run-20260809t123938z_8f56092721df`), slug edge cases (uppercase, spaces, trailing slash, overlong basename, dot names), canonical record bytes, idempotent no-change re-write, and drift repair after record deletion.

## 2. Launch Integration

- [x] 2.1 Call the writer from Kimi provider-start planning (`_ensure_kimi_native_system_prompt_for_start` path in `src/houmao/agents/realm_controller/launch_plan.py`, covering fresh headless, fresh TUI, and relaunch) with the launch plan's actual working directory, gated on `operator_prompt_mode == unattended`, repairing drift and recording launch verification in `LaunchPlan.metadata` and the session manifest alongside the native-prompt verification.
- [x] 2.2 Prove `as_is` launches write no trust record, with tests for both headless and local-interactive gating.

## 3. Verification

- [x] 3.1 Run targeted unit tests plus `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
- [x] 3.2 Update `tmp/kimi-native-prompt-smoke/scripts/run_tui.py` to treat an appearing trust modal as a failure (remove the acceptance path, keep the detection), then re-run the TUI leg live and confirm `trust_dialog_accepted: false` with the marker probe still passing.
- [x] 3.3 Update launch-policy/run-phase reference docs with the unattended trust pre-seed boundary and run `openspec validate preseed-kimi-workspace-trust --strict`.
