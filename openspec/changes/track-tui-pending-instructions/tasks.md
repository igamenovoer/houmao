## 1. Expand the Shared Pending-Input State Contract

- [x] 1.1 Add required `pending_input: Tristate` fields to normalized detector signals, temporal hints where applicable, tracker snapshots, transitions, timelines, and public surface models.
- [x] 1.2 Thread pending input through tracker session initialization, snapshot reduction, state serialization/deserialization, transition construction, and bounded history without deriving it from turn phase or prompt notes.
- [x] 1.3 Include pending input in the operator-visible state and stability signatures so a `no → yes` or `yes → no` change emits a transition while the turn remains active.
- [x] 1.4 Update unsupported/fallback profiles and every shared-state constructor or fixture to provide an explicit conservative pending-input value; do not add a compatibility default that hides missing call sites.
- [x] 1.5 Add shared tracker unit tests for busy-no-pending, busy-pending, last-pending-consumed, ambiguous/unknown, and prompt-note-without-visible-queue behavior.

## 2. Implement Provider Pending-Input Detectors

- [x] 2.1 Promote Codex queued-follow-up and pending-input structural evidence into the normalized pending-input tristate while preserving existing active reasons as diagnostics.
- [x] 2.2 Add Codex tests for no queue, one queue item, multiple queue items, queue consumption, wrapping/resizing, stale transcript matches, and incomplete captures.
- [x] 2.3 Promote Kimi queue-visible and queued-message structural evidence into the normalized pending-input tristate without matching arbitrary historical transcript prose.
- [x] 2.4 Add Kimi tests for no queue, one/two/three queued prompts, queue consumption, provider caps, wrapping/resizing, stale evidence, and incomplete captures.
- [x] 2.5 Implement a Claude profile-owned pending-input behavior that locates the bottom framed composer, reuses semantic prompt rendering classification, and recognizes the bounded indented queued-preview user cell above it.
- [x] 2.6 Make Claude return `unknown` when composer or queued-preview bounds are cropped or ambiguous and ensure intervening assistant, tool, or activity cells invalidate a candidate queued-preview row.
- [x] 2.7 Add Claude positive tests for queued previews with arbitrary/localized ghost suggestion text, no suggestion text, multiple queued prompts, wrapped content, and resized panes.
- [x] 2.8 Add Claude negative tests for ghost suggestion alone, queue-like transcript prose, historical user cells separated by output, ordinary draft content, exact old suggestion wording without a queued row, and unrecognized style.
- [x] 2.9 Verify provider profile selection carries pending-input behavior across the maintained Claude, Codex, and Kimi version families without adding Gemini support.

## 3. Project Pending Input Through Maintained State Surfaces

- [x] 3.1 Add pending input to canonical terminal current-state, transition, and history response models and all gateway-owned tracking projections.
- [x] 3.2 Add pending input to passive-server compact TUI state, detailed TUI state, managed-agent TUI detail, and history responses without consulting parsed sidecar or submission records.
- [x] 3.3 Update HTTP clients, CLI state/history/watch renderers, JSON examples, and response-contract tests to expose pending input independently from readiness and editing.
- [x] 3.4 Add projection tests proving that a pending-only change is retained in history and that proxying or noting a prompt does not synthesize a pending value.

## 4. Extend Terminal Recording, Labels, Replay, and Review

- [x] 4.1 Add `surface_pending_input` to terminal-record timeline rows, persisted tracker observations, replay analysis output, and comparison field sets.
- [x] 4.2 Extend `terminal_record add-label` and label parsing/expansion to accept required pending-input expectations for samples and ranges.
- [x] 4.3 Update replay validation to report expected and actual pending-input mismatches by stable sample id and contiguous sample range.
- [x] 4.4 Update terminal-record and shared-tracking review videos or textual review panels to show pending input separately from readiness, editing, and turn phase.
- [x] 4.5 Implement deterministic 10 Hz, 5 Hz, and 2 Hz derivation plus seeded jitter, drop, and burst replay variants without modifying the frozen 20 Hz source stream.
- [x] 4.6 Add replay-tool tests for reproducible cadence selection, retained-sample label mapping, skipped unobserved transitions, bounded drift reporting, and absence of cadence-only yes/no oscillation.
- [x] 4.7 Update strict shared-TUI recorded validation and existing fixture labels to include the new public field in the breaking schema.

## 5. Replace Gateway Force Models With Admission Policy

- [x] 5.1 Define the shared `ready_only | if_no_pending | always` admission-policy type and advance the strict direct prompt-control request schema to version 2.
- [x] 5.2 Remove `force` from direct prompt request models and remove `forced` from success and structured-error models; add the selected `admission_policy` to both result shapes.
- [x] 5.3 Add model tests for the default policy, every valid explicit policy, rejected schema version 1, rejected extra `force`, and serialized result/error payloads.
- [x] 5.4 Update gateway event and diagnostic payloads to record the selected policy plus the tracked readiness and pending facts used for conditional decisions.

## 6. Implement Observational Gateway Admission

- [x] 6.1 Refactor direct prompt control to enforce gateway attachment, availability, reconciliation, selector, execution-override, and adapter compatibility checks before policy evaluation for every request.
- [x] 6.2 Implement `ready_only` for TUI targets using the existing stable prompt-ready checks plus the requirement that pending input is decisively `no`.
- [x] 6.3 Implement `if_no_pending` for TUI targets so it ignores readiness/editing/busy posture, dispatches only for `no`, and returns distinct `pending_input` and `pending_input_unknown` refusals.
- [x] 6.4 Implement `always` for compatible attached TUI targets so it bypasses tracked readiness and pending checks but not structural gateway failures.
- [x] 6.5 Reject `if_no_pending` and `always` for native headless targets, preserve headless overlap protection, and reject non-ready-only policies for TUI `chat_session.mode=new`.
- [x] 6.6 Preserve explicit-input turn provenance after dispatch while verifying that gateway dispatch, reminder/notifier state, durable requests, and raw send-keys never set pending input directly.
- [x] 6.7 Add a table-driven unit suite covering every TUI policy against ready/busy, editing, `yes|no|unknown` pending state, stable/unstable posture, parsed-surface sidecars, and structural gateway failures.
- [x] 6.8 Add a replay-driven fake-adapter test in which two pre-repaint `if_no_pending` calls may both submit, a later observed `yes` blocks conditional submission, and `always` still submits.
- [x] 6.9 Confirm the implementation adds no pending-slot reservation, shadow-queue state, or lock held across provider repaint.

## 7. Update Proxy, Client, and `houmao-mgr` Interfaces

- [x] 7.1 Update direct gateway clients and runtime/controller helpers to accept admission policy and consume the new result/error shapes.
- [x] 7.2 Update passive-server managed-agent gateway prompt models and proxy routes to validate schema version 2 and forward policy and refusal payloads unchanged.
- [x] 7.3 Replace gateway prompt `--force` with `--admission-policy ready-only|if-no-pending|always` on maintained `agents single` and `agents self` command paths.
- [x] 7.4 Map hyphenated CLI values to underscore API enums and update plain, fancy, and JSON renderers to report admission policy instead of a forced boolean.
- [x] 7.5 Update every in-repository gateway prompt caller, demo, test double, fixture, and API example to the breaking request/result contract; leave no prompt-control force shim.
- [x] 7.6 Add CLI and proxy tests for each policy, default behavior, structured pending refusals, TUI/headless validation, removed `--force`, and strict rejection of old HTTP payloads.

## 8. Update Documentation and Packaged Guidance

- [x] 8.1 Update the scoped `houmao-mgr` CLI reference with current policy syntax, the decision table, conservative unknown handling, TUI-only non-default scope, and observational concurrency.
- [x] 8.2 Update gateway contract, operations, and internals references to distinguish provider pending input, composer drafts, gateway-durable work, and explicit prompt notes.
- [x] 8.3 Remove current `--force` prompt-control examples and forced-boolean response descriptions from maintained docs without retaining deprecation or compatibility guidance.
- [x] 8.4 Update the packaged `houmao-agent-messaging` skill and routed prompt/gateway guidance to map caller intent to ready-only, if-no-pending, or always.
- [x] 8.5 Update system-skill and documentation tests so installed assets teach the new policy and never direct agents to the removed gateway prompt force flag.

## 9. Audit and Replay the Recorded Pending Datasets

- [x] 9.1 Inventory the UC05 Claude, Codex, and Kimi frozen recordings plus the 1/2/3-pending extensions and record source paths, hashes, tool versions, capture cadence, and taint/cap status.
- [x] 9.2 Resolve the Claude metadata-versus-pane-header version discrepancy and record which version profile applies before scoring the run.
- [x] 9.3 Render or reuse pane-plus-label review videos and manually audit busy-no-pending, pending onset, pending span, last-pending consumption, and ready-return boundaries for each provider.
- [x] 9.4 Persist audited pending-input labels and evidence notes separately from analyzer-generated capture patterns so the latter are not the sole oracle.
- [x] 9.5 Run strict canonical 20 Hz replay for Claude, Codex, and Kimi and save field/sample-range mismatch output.
- [x] 9.6 Run deterministic 10 Hz, 5 Hz, 2 Hz, jitter, drop, and burst variants and verify retained decisive surfaces, bounded transition drift, and meaningful behavior when transitions are skipped.
- [x] 9.7 Run the one/two/three-pending matrix, report provider queue caps or tainted runs explicitly, and verify the public field remains binary.
- [x] 9.8 Save a timestamped replay qualification report with artifact and video paths under `context/features/2026-07-11-tui-state-tracking-test-plan/test-reports/`.

## 10. Run Live Unattended Admission Qualification

- [x] 10.1 Define a live UC06 policy sequence that captures ready/no-pending, busy/no-pending, busy/pending, pending-consumed, and ready-return checkpoints and exercises all three admission policies.
- [x] 10.2 Launch Claude, Codex, and Kimi through the maintained development launch-agent workflow in unattended mode, store temporary projects and all output under fresh `tmp/<subdir>` roots, and record every tmux testing session.
- [x] 10.3 For Codex, inherit and verify the configured proxy environment used by the test run (currently port 7990) without hard-coding that port into product code or generic skill guidance.
- [x] 10.4 For each provider, verify ready-only refusal while busy, if-no-pending dispatch while busy/no-pending, later if-no-pending refusal after tracked `yes`, and always dispatch while pending.
- [x] 10.5 Include a closely spaced pre-repaint submission step that permits both calls to succeed, then verify later behavior changes only after the tracker observes pending input.
- [x] 10.6 Render review videos that align pane frames, tracked pending/readiness state, gateway decisions, and CLI results for the live runs.
- [x] 10.7 Save one timestamped live qualification report under the feature test-report directory with provider versions, credentials/proxy posture without secrets, commands, recordings, videos, mismatches, and pass/fail conclusions; do not run Gemini.

## 11. Verify the Breaking Change

- [x] 11.1 Run focused shared-tracker, provider-profile, terminal-record, gateway-service, passive-server, client, CLI, docs, and system-skill unit suites through Pixi.
- [x] 11.2 Run `pixi run format`, `pixi run lint`, and `pixi run typecheck`, fixing all pending-field and admission-policy propagation gaps.
- [x] 11.3 Run `pixi run test` and the relevant runtime/integration suites, recording any externally unavailable live tests separately from deterministic failures.
- [x] 11.4 Search maintained source, tests, docs, and packaged skills for obsolete direct prompt-control `force`/`forced` usage and remove every compatibility remnant without touching unrelated force concepts.
- [x] 11.5 Run `openspec validate track-tui-pending-instructions --strict` and reconcile the final implementation, tests, docs, and reports with every delta requirement.
