## 1. Refresh Model and Adapter Contracts

- [x] 1.1 Add deterministic GPT-5.6 Sol, Terra, Luna, and alias reasoning ladders to the Codex model-mapping policy, including off rejection and saturation provenance.
- [x] 1.2 Add unit tests for every GPT-5.6 level, alias resolution, Luna's shorter ladder, zero rejection, and above-range saturation using the current bundled Codex catalog as evidence.
- [x] 1.3 Implement Kimi config-backed effort discovery from the selected model alias, including effective overrides, always-thinking/off handling, native thinking projection, and secret-free provenance.
- [x] 1.4 Implement explicit Kimi env-model reasoning rejection without inventing a ladder, while preserving native effort env configuration when no normalized override is requested.
- [x] 1.5 Add Kimi model-mapping tests for ordered efforts, saturation, permitted off, always-thinking rejection, missing metadata, and env-model behavior.
- [x] 1.6 Refresh the starter Kimi adapter environment allowlist, remove obsolete thinking variables, and update adapter projection tests and snapshots.

## 2. Replace the Kimi 0.11 Launch Contract

- [x] 2.1 Replace the Kimi launch-policy entries with version-scoped Kimi 0.23.x headless and raw-launch unattended strategies and current source/live-probe evidence.
- [x] 2.2 Update the Kimi headless provider hook so prompt placement, session selection, stream JSON, skills, and prompt-mode-incompatible permission flags match Kimi 0.23.x.
- [x] 2.3 Update the Kimi TUI provider hook to canonicalize permission inputs, suppress the legacy migration picker, and append one strategy-owned native `--auto` argument for fresh, latest-resume, and exact-resume launches.
- [x] 2.4 Remove the post-readiness `/auto on` refresh path, its bootstrap ordering, and tests that treat resume plus `--auto` as a conflict.
- [x] 2.5 Add launch-policy and relaunch tests proving Kimi 0.23.x resolves, older/out-of-range versions fail explicitly, unattended resume keeps `--auto`, and `as_is` preserves native approval behavior.
- [x] 2.6 Run targeted live Kimi 0.23.x TUI and headless smoke probes with an isolated copy of local credentials, verify prompt-free readiness, and retain redacted command and posture evidence.

## 3. Normalize Current Headless Protocol Events

- [x] 3.1 Add Codex `collab_tool_call` fixtures and normalize started, updated, completed, failed, and partially populated collaboration items through the canonical action lifecycle.
- [x] 3.2 Update plain, JSON, and fancy rendering tests so Codex delegation appears consistently in live and replayed concise/detail output.
- [x] 3.3 Add Kimi `turn.step.retrying` fixtures and normalize attempt, delay, status, and error fields as canonical progress or diagnostic data.
- [x] 3.4 Verify raw Codex and Kimi stdout/stderr artifacts remain unchanged while recognized current events no longer degrade to passthrough.

## 4. Bound TUI Profile Selection

- [x] 4.1 Add an optional exclusive maximum version to detector registrations and update selection to require the observed version inside a maintained interval.
- [x] 4.2 Bound the Codex 0.116.x and Kimi 0.11.x registrations to their evidence-backed families and make unvalidated gaps/newer releases select app-specific fallback profiles.
- [x] 4.3 Add registry unit tests for exact matches, bounded compatible patches, version gaps, newer versions, fallback provenance, and explicit experimental overrides.

## 5. Capture and Implement the Codex 0.144.x Profile

- [x] 5.1 Resolve and record the Codex 0.144.x unattended posture, source commit, bundled GPT-5.6 capabilities, effective launch command, isolated home, and empty intervention allowlist.
- [x] 5.2 Capture unattended Codex 0.144.x native TUI sessions at about 20 fps covering ready, draft, normal active/tool activity, interruption, ready return, and GPT-5.6 delegated-agent activity.
- [x] 5.3 Manually label the Codex high-rate timelines without consulting tracker output and record structural, style, temporal, and bounded semantic evidence for each state range.
- [x] 5.4 Derive 10, 5, and 2 Hz plus deterministic jittered/gapped Codex streams with source-sample traceability and define their semantic transition constraints.
- [x] 5.5 Implement the Codex 0.144.x detector profile from source and labeled evidence, including current collaboration activity and sparse-capture settlement behavior.
- [x] 5.6 Pass strict high-rate and semantic sparse replay validation before registering Codex 0.144.x as maintained.

## 6. Capture and Implement the Kimi 0.23.x Profile

- [x] 6.1 Update the Kimi testing design assumptions to native `--auto`, resolve and record the Kimi 0.23.x unattended posture, and verify prompt-free readiness before capture.
- [x] 6.2 Capture at least five development and three held-out unattended Kimi 0.23.x sessions at about 20 fps, with each counted session spanning multiple state transitions.
- [x] 6.3 Cover current Kimi ready, draft, response, tool, todo/background, retry, interruption, completion, ready-return, and footer-thinking surfaces; treat any avoidable confirmation as a failed capture.
- [x] 6.4 Manually label development and held-out high-rate Kimi timelines without tracker output and document any unavoidable hard-coded intervention with source evidence and no available bypass.
- [x] 6.5 Derive 10, 5, and 2 Hz plus deterministic jittered/gapped Kimi streams with source-sample traceability and semantic transition constraints.
- [x] 6.6 Implement the Kimi 0.23.x detector profile using only development evidence, then pass strict high-rate and semantic sparse validation on both development and untouched held-out sessions.
- [x] 6.7 Register Kimi 0.23.x as maintained only after the recorded validation gate passes.

## 7. Run Complex and Long-Horizon TUI Qualification

- [ ] 7.1 Execute the unattended state-coverage and multi-step transition cases in `context/features/2026-07-11-tui-state-tracking-test-plan`, excluding unreliable network/LLM API failures and treating confirmation states as forbidden live outcomes.
- [ ] 7.2 Execute the five specified long-horizon procedures with at least 20 recorded operator operations in each session against the refreshed current profiles.
- [ ] 7.3 Validate all five stress recordings at canonical 20 fps and at regular, jittered, bursty, and gapped lower cadences; retain downstream-consumer traces and semantic verdicts.
- [x] 7.4 Update the test-plan coverage ledger and assumptions so the documented maintained versions, strategy ids, commands, and no-confirmation posture match the implemented contracts.

## 8. Update Documentation and System Skills

- [x] 8.1 Update launch-policy, backend, session-lifecycle, role-injection, TUI detector, terminal-record, and troubleshooting references for Codex 0.144.x and Kimi 0.23.x.
- [x] 8.2 Update overview, quickstart, easy-specialist, agent-definition, and system-skills guidance with current GPT-5.6 ladders, Kimi effort discovery, and native unattended behavior.
- [x] 8.3 Update relevant packaged system skills and their reference pages so they no longer teach Kimi 0.11 behavior, resume conflicts, `/auto on`, obsolete environment variables, or a four-level GPT-5.6 ladder.
- [x] 8.4 Run repository-wide stale-contract searches across code, tests, docs, context, OpenSpec specs, and `src/assets`, retaining historical version statements only when clearly labeled as historical evidence.

## 9. Verify the Complete Change

- [x] 9.1 Run targeted model-mapping, launch-policy, headless-output, registry, detector, recorder, and replay unit/integration tests through Pixi.
- [x] 9.2 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `pixi run test-runtime`, and resolve regressions caused by the breaking contract refresh.
- [x] 9.3 Run OpenSpec validation for `refresh-codex-kimi-integrations` and confirm every modified capability and implementation task is coherent with the final behavior.
- [x] 9.4 Record final installed CLI versions, source commits, live unattended smoke results, corpus/replay verdicts, and any evidence-backed unavoidable intervention in the change verification notes.
