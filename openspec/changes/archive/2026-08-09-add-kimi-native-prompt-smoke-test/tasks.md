## 1. Script Scaffold and Preflight

- [x] 1.1 Create `tmp/kimi-native-prompt-smoke/` with a run-agnostic layout: `scripts/` for the drivers, `<run-id>/` per execution for brains, homes, recordings, and the frozen evidence bundle.
- [x] 1.2 Write `scripts/preflight.py` asserting `kimi --version` parses and is ≥ 0.34.0, the native Kimi Code home (`$KIMI_CODE_HOME` or `~/.kimi-code`) resolves with a coherent auto credential posture — `kimi provider list --json` shows a configured provider and `kimi doctor config` accepts `config.toml` when present, with no secret values printed — and the run root is writable; hard-fail with an explicit diagnostic before any live run, credential import, or tmux session.
- [x] 1.3 Write `scripts/import_credential.py` importing the native Kimi Code home into the scratch Houmao project via `houmao-mgr project credentials kimi add --code-home <native-home>` (auto credential per `houmao-credential-mgr` Kimi kind 4), recording only the credential display name and source path in run metadata; fail explicitly on scoped OAuth token files rather than importing partial state.

- [x] 1.4 Write `scripts/build_role.py` generating the disposable role prompt with a unique frozen marker token (`KNS-<random>`) plus an unambiguous assigned-role instruction, stored under the run root for reuse by both launch surfaces.

## 2. Managed Brain Build and Artifact Verification

- [x] 2.1 Write `scripts/build_brain.py` driving the supported `houmao-mgr` CLI to create a Kimi specialist referencing the imported auto credential (with the frozen-marker role prompt) and build the managed brain, all inside the scratch project under the run root.
- [x] 2.2 Write `scripts/verify_artifact.py` implementing the artifact layer: assert managed `$KIMI_CODE_HOME/SYSTEM.md` exists with leading `${base_prompt}`, effective-prompt suffix containing the marker, and 0600 permissions; record effective and rendered SHA-256 digests; assert provenance shows `native_home_system_prompt`, `KIMI_CODE_LEGACY_FLAG=0`, and successful precedence validation.

## 3. Live Headless Verification

- [x] 3.1 Write `scripts/run_headless.py` launching one managed headless turn via `houmao-mgr` submitting `State your assigned role in one sentence.`, capturing the transcript and final response into the evidence bundle.
- [x] 3.2 Add the behavior-layer judge to `run_headless.py`: forgiving marker-token presence check on the response; the run passes only if the artifact layer (2.2) passed first and the response contains the marker token.

## 4. Live TUI Verification and Labeling

- [x] 4.1 Write `scripts/run_tui.sh` launching one unattended managed Kimi TUI session via `houmao-mgr`, recording it with `pixi run python -m tools.terminal_record` at the canonical 0.05 s interval, then stopping and freezing `pane_snapshots.ndjson` (record its digest) before any labeling.
- [x] 4.2 Submit the same role probe in the TUI session, capture the response, and apply the two-layer judge (artifact layer first, marker-token behavior check second).
- [x] 4.3 Delegate blind labeling of the frozen snapshots to a subagent: label the 7 public tracked-state fields directly from `pane_snapshots.ndjson` without tracker output; the labeled timeline must show projection completed before TUI startup and no role-bootstrap chat turn before readiness.

## 5. Relaunch Digest Check

- [x] 5.1 Write `scripts/run_relaunch.py` performing the supported managed relaunch and comparing pre- and post-relaunch `SYSTEM.md` digests and provider-start verification metadata; pass on matching digest plus fresh verification, without a third paid prompt turn.

## 6. Evidence Bundle and Wrap-Up

- [x] 6.1 Write `scripts/run_all.sh` orchestrating preflight → credential import → role → brain build → artifact verification → headless → TUI (record, probe, freeze) → relaunch, with a final pass/fail summary and the evidence bundle path.
- [x] 6.2 Execute the full smoke run once against the live Kimi 0.34.0 binary, delegate TUI labeling to a subagent, and resolve any failures in the scripts (product failures are reported, not patched).
- [x] 6.3 Freeze the evidence bundle (bytes, digests, provenance, transcripts, labeled timeline, summary) under the run root and report results for citation by `use-kimi-native-system-prompt` task 5.5.
