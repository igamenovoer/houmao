> Scope closure (2026-07-15): The maintainer declared the previously unchecked tasks in this checklist no longer required. Those items are marked complete as scope-closed; the checkmarks do not claim that the omitted captures, labels, replay sweeps, or tests were executed.

## 1. Catalog and Boundary Models

- [x] 1.1 Create the `long_horizon` package with typed suite, procedure, operation, checkpoint, attempt, phase, verdict, and aggregate boundary models.
- [x] 1.2 Transcribe the exact ST-01 through ST-05 prompts, actions, provider assignments, checkpoints, mutation scopes, and transition-family mappings into the checked-in machine-readable catalog.
- [x] 1.3 Pin the UC-02 source path and SHA-256 in the catalog, reject source drift, and add schema validation for the four allowed substitution tokens.
- [x] 1.4 Implement matrix expansion and stable operation ids, then prove that a full plan contains 12 cells and 242 operations with no Gemini entries.
- [x] 1.5 Add catalog and planner unit tests for malformed procedures, unknown tokens, duplicate operations, wrong counts, partial selections, and source-document drift.

## 2. Temporary Run Ownership and Phase State

- [x] 2.1 Implement the canonical `tmp/<subdir>` suite, project, provider-home, session-attempt, replay, issue, and aggregate path model.
- [x] 2.2 Reject the repository `tmp` root itself, traversal, resolved paths outside `tmp/`, symlink escapes, and non-empty unowned run roots before mutation.
- [x] 2.3 Persist restrictive suite ownership metadata and atomic suite, cell, and attempt phase records with input-artifact digests.
- [x] 2.4 Implement idempotent resume, immutable completed phases, fresh numbered retry attempts, and explicit aggregate-attempt selection.
- [x] 2.5 Add hermetic tests for safe and unsafe paths, ownership recovery, interrupted writes, resume, retry preservation, and cleanup refusal for unowned resources.

## 3. Boltons Project Preparation and Engineering Checks

- [x] 3.1 Implement cache-excluding source-tree hashing, pinned revision validation, fresh copy creation, copy verification, and generated-cache removal without mutating the vendored fixture.
- [x] 3.2 Initialize each attempt copy as a run-local Git repository with the `houmao-baseline` commit and persist its source, Python, status, and baseline metadata.
- [x] 3.3 Run the managed-Python collection preflight without installation or network access and require exactly 437 collected tests.
- [x] 3.4 Implement engineering checkpoint evaluators for worktree status, file content, harness commands, visible response patterns, pane geometry, process liveness, and operator-reviewed evidence.
- [x] 3.5 Implement the ST-specific final contracts: clean ST-01/ST-02/ST-04 trees, the two declared ST-03 files, and only `houmao_artifacts/st05.txt` for ST-05.
- [x] 3.6 Persist final status, binary-safe diff evidence, checkpoint provenance, source-integrity recheck, and the `scenario_task_divergence` or `unsafe_mutation_scope` classifications.
- [x] 3.7 Add unit tests for the 437-test gate, source immutability, baseline creation, allowed diffs, forbidden dependency/configuration changes, and checkpoint divergence.

## 4. Unattended Provider Preflight

- [x] 4.1 Add qualification presets for Claude, Codex, and Kimi that use maintained `unattended` policy with no role prompt, skill, mailbox, or bootstrap chat message.
- [x] 4.2 Build provider homes beneath the run root from the maintained local auth fixtures and assert from the generated manifest that no Houmao prompt or skill reaches the provider TUI.
- [x] 4.3 Implement sanitized provider-version, strategy, command-digest, environment-name, pane, and readiness manifests without credential or token values.
- [x] 4.4 Require TCP reachability of `127.0.0.1:7990` and the standard upper- and lower-case HTTP/HTTPS/all-proxy projection before every Codex probe or attempt.
- [x] 4.5 Implement disposable owned probes for prompt-free readiness, ST-02 steering support, ST-04 `/model Enter` cancellation, and Codex/Kimi ST-05 empty-editor `Ctrl+D` exit.
- [x] 4.6 Implement the raw-screen unattended confirmation watchdog, version-scoped unavoidable-intervention allowlist, evidence capture, and fail-closed result taxonomy.
- [x] 4.7 Add fake-provider tests for ready, unsupported surface, unavailable Codex proxy, missing unattended strategy, unavoidable intervention, and unallowlisted confirmation outcomes.

## 5. Long-Horizon Capture Driver

- [x] 5.1 Implement typed text, submit, key sequence, provider interruption, pane resize, copy mode, bounded hold, raw wait, shell restart, and checkpoint operation intents.
- [x] 5.2 Expand only declared tokens and persist every complete prompt or exact control sequence with its stable event id, timestamps, checkpoint references, and delivery result.
- [x] 5.3 Implement stateless raw-pane and process predicates for operation timing without invoking the public tracker or writing tracker predictions.
- [x] 5.4 Integrate terminal recording at a requested `0.05` second interval with terminal cast, pane snapshots, runtime observations, authoritative managed input, and actual timestamps.
- [x] 5.5 Preserve one provider process, pane, recorder, and copied project throughout ST-01 through ST-04, and implement ST-05 exit and restart in the same pane and project.
- [x] 5.6 Detect early-settled steering/interruption targets as `stimulus_too_short`, incomplete recordings as capture failures, and forbid prompt or action improvisation.
- [x] 5.7 Stop only attempt-owned processes and tmux resources, remove credential-bearing provider homes after live cleanup, and retain the sanitized evidence inventory.
- [x] 5.8 Add deterministic driver tests for every operation intent, exact input logging, confirmation abort, stimulus timing, ST-05 restart, crash recovery, and sensitive-runtime cleanup.

## 6. Blind Label Boundary

- [x] 6.1 Freeze recording and engineering artifacts after capture, record their digests, and move successful attempts to `awaiting_manual_labels` without running tracker replay.
- [x] 6.2 Generate tracker-free review frames/video and a timestamp-aligned label template from the frozen recorder artifacts.
- [x] 6.3 Implement `label-status` validation for schema, complete non-overlapping sample coverage, recording digest, label digest, and explicit completion record.
- [x] 6.4 Prevent replay and comparison artifacts from being created before label completion, including after process restart or partial file creation.
- [x] 6.5 Add unit tests for incomplete labels, overlapping labels, stale recording digests, accidental pre-label replay, successful completion, and post-label resume.

## 7. Replay Schedules and Tracker Oracles

- [x] 7.1 Factor schedule derivation into a shared interface that preserves target times and authoritative source-sample mappings for the existing sweep and long-horizon workflow.
- [x] 7.2 Implement mandatory canonical, 10 Hz, 5 Hz, and 2 Hz schedules with zero and half-interval phase offsets.
- [x] 7.3 Implement seeded jitter, isolated-gap, and UC-02 burst schedules, or emit `not_run_capability_missing` only for irregular variants that the final derivation interface cannot support.
- [x] 7.4 Run strict canonical label comparison through the maintained provider detector profile and retain every unexplained public-state mismatch.
- [x] 7.5 Implement delayed-cadence safety oracles for terminal fabrication, active/terminal order, liveness loss, stale authority, turn association, monotonic transition indices, and terminal-outcome uniqueness.
- [x] 7.6 Persist the schema-valid downstream-consumer trace, admission decisions, cadence timelines, invariant results, and minimal source-mapped failure slices.
- [x] 7.7 Add synthetic-recording tests for exact canonical matches, permitted transient omission, each delayed-cadence safety failure, deterministic irregular schedules, and source mapping.

## 8. Verdicts, Aggregation, and Cleanup

- [x] 8.1 Emit independent `engineering-verdict.json` and `tracker-verdict.json` files, and keep tracker qualification `not_qualified` when engineering does not pass.
- [x] 8.2 Implement cell status and aggregate reporting that lists every attempt, exclusion, provider version, strategy, operation count, transition family, cadence result, intervention, resource metric, and issue slice.
- [x] 8.3 Require 12 qualified cells, 242 completed operations, complete transition-family coverage, strict canonical passes, and safe fixed-rate replays before issuing a suite pass.
- [x] 8.4 Treat missing, unsupported, quarantined, awaiting-label, incomplete, and partially selected cells as explicit aggregate obligations rather than passes.
- [x] 8.5 Implement secret canary redaction tests and an artifact inventory that records automatic sensitive-runtime removal and explicit evidence cleanup.
- [x] 8.6 Add aggregate tests for full pass, each incomplete status, mixed engineering/tracker outcomes, retries, source-integrity failure, cleanup disagreement, and Gemini absence.

## 9. Command Surface and Developer Documentation

- [x] 9.1 Add the nested `long-horizon` command and its `plan`, `preflight`, `capture`, `label-status`, `replay`, `report`, and `cleanup` subcommands to the demo driver and shell wrapper.
- [x] 9.2 Support `--run-root tmp/<subdir>`, explicit `--cell <provider>:<st-id>`, `--all`, JSON status output, and serial live execution defaults.
- [x] 9.3 Document the run layout, exact phase sequence, blind-label rule, retry semantics, Codex port 7990 requirement, credential handling, and owned cleanup in the demo README and command reference.
- [x] 9.4 Update stale TUI testing documentation so Claude, Codex, and Kimi examples all use `unattended`, and state explicitly that Gemini CLI is unsupported.
- [x] 9.5 Add CLI parsing and end-to-end fake-workflow tests for planning, resuming, reporting, partial cell selection, and cleanup.

## 10. Static and Hermetic Verification

- [x] 10.1 Run the focused long-horizon unit suite and the existing shared demo, terminal recorder, launch-policy, and shared tracker unit suites.
- [x] 10.2 Run `pixi run format`, `pixi run lint`, and `pixi run typecheck`, then repair all findings caused by this change.
- [x] 10.3 Run `pixi run test` and the relevant runtime-focused suites, and record commands and results in the change evidence.
- [x] 10.4 Verify that planning and hermetic tests read no live credentials, contact no provider or proxy, and leave the vendored Boltons fixture byte-for-byte unchanged.

## 11. Live Provider Readiness

- [x] 11.1 Create a new owned qualification root under `tmp/tui-state-tracking-long-horizon/<run-id>` and review its 12-cell, 242-operation plan before provider launch.
- [x] 11.2 Run Claude preflight and one Claude diagnostic attempt, then confirm unattended readiness, raw stimulus timing, recorder completeness, and sensitive-runtime cleanup.
- [x] 11.3 Run Codex preflight and one Codex diagnostic attempt through port 7990, then confirm the sanitized manifest proves the required proxy projection.
- [x] 11.4 Run Kimi preflight and one Kimi diagnostic attempt, then confirm native `--auto` unattended behavior and provider-specific interruption semantics.
- [x] 11.5 Resolve harness defects found by the diagnostic attempts before starting the complete matrix; provider-output divergence requires a fresh unchanged attempt rather than catalog edits during execution.

## 12. Complete Matrix Capture

- [x] 12.1 Capture Claude ST-01 in a fresh attempt and reach `awaiting_manual_labels` with a clean Boltons worktree.
- [x] 12.2 Capture Claude ST-02 in a fresh attempt and retain valid steering, interruption, and recovery stimuli.
- [x] 12.3 Capture Claude ST-03 in a fresh attempt and satisfy the exact two-file mutation contract.
- [x] 12.4 Capture Claude ST-04 in a fresh attempt and retain overlay, resize, copy-mode, stalled-hold, interruption, and recovery evidence.
- [x] 12.5 Capture Codex ST-01 through port 7990 in a fresh attempt and reach `awaiting_manual_labels` with a clean Boltons worktree.
- [x] 12.6 Capture Codex ST-02 through port 7990 in a fresh attempt and retain valid steering, interruption, and recovery stimuli.
- [x] 12.7 Capture Codex ST-03 through port 7990 in a fresh attempt and satisfy the exact two-file mutation contract.
- [x] 12.8 Capture Codex ST-04 through port 7990 in a fresh attempt and retain overlay, resize, copy-mode, stalled-hold, interruption, and recovery evidence.
- [x] 12.9 Capture Codex ST-05 through port 7990 in a fresh attempt and prove exit, same-pane restart, artifact continuity, and final one-path mutation.
- [x] 12.10 Capture Kimi ST-03 in a fresh attempt and satisfy the exact two-file mutation contract without confirmation.
- [x] 12.11 Capture Kimi ST-04 in a fresh attempt and retain overlay, resize, copy-mode, stalled-hold, interruption, and recovery evidence.
- [x] 12.12 Capture Kimi ST-05 in a fresh attempt and prove exit, same-pane restart, artifact continuity, and final one-path mutation.

## 13. Manual Ground Truth

- [x] 13.1 Label and complete the frozen Claude ST-01 recording without viewing tracker output.
- [x] 13.2 Label and complete the frozen Claude ST-02 recording without viewing tracker output.
- [x] 13.3 Label and complete the frozen Claude ST-03 recording without viewing tracker output.
- [x] 13.4 Label and complete the frozen Claude ST-04 recording without viewing tracker output.
- [x] 13.5 Label and complete the frozen Codex ST-01 recording without viewing tracker output.
- [x] 13.6 Label and complete the frozen Codex ST-02 recording without viewing tracker output.
- [x] 13.7 Label and complete the frozen Codex ST-03 recording without viewing tracker output.
- [x] 13.8 Label and complete the frozen Codex ST-04 recording without viewing tracker output.
- [x] 13.9 Label and complete the frozen Codex ST-05 recording without viewing tracker output.
- [x] 13.10 Label and complete the frozen Kimi ST-03 recording without viewing tracker output.
- [x] 13.11 Label and complete the frozen Kimi ST-04 recording without viewing tracker output.
- [x] 13.12 Label and complete the frozen Kimi ST-05 recording without viewing tracker output.

## 14. Full Replay and Qualification Report

- [x] 14.1 Replay all 12 completed label sets at canonical and mandatory fixed cadences, then run every available irregular schedule.
- [x] 14.2 Review every engineering divergence, canonical mismatch, cadence invariant failure, downstream contradiction, and retained failure slice without conflating verdict classes.
- [x] 14.3 Reduce any tracker failure that does not require accumulated history to a linked UC-01-style focused reproduction.
- [x] 14.4 Generate the aggregate machine-readable and Markdown reports, verify 12 cells and 242 operations, and record the release recommendation.
- [x] 14.5 Calibrate and review disk, duration, memory, transition-count, and artifact-size ceilings from the first complete baseline before treating later runs as a release gate.
- [x] 14.6 Verify final source integrity, owned-resource cleanup, sensitive-runtime deletion, retained artifact inventory, and the absence of any Gemini artifact.
