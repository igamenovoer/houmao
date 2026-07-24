## Context

The latest 20 fps long-horizon corpus contains sustained false-ready intervals for Kimi Code 0.23.6 and Codex 0.144.1. Local upstream source checkouts explain the visible surfaces: Kimi's `QueuePaneComponent` is rendered only for retained messages while streaming or compacting, and Codex's `PendingInputPreview` holds pending steers, rejected steers, and queued messages while a turn is in progress.

The current detector profiles omit some of those current source-backed surfaces. The long-horizon raw readiness gate also declares a post-submit surface ready without first observing that the submitted turn started. Finally, the existing UC-03 report maps generated UC-02 public-state labels through the same mapper as tracker output, so it cannot serve as independent behavioral ground truth.

The implementation must preserve the public tracked-state schema and use the frozen recordings as deterministic regression evidence. The untracked `plan-uc-03-prompt-admission-test` artifacts remain a separate harness change.

## Goals / Non-Goals

**Goals:**

- Remove sustained false-ready intervals caused by omitted Codex and Kimi current-turn surfaces.
- Keep Codex retry and overlay recognition bounded to current source-backed UI structures.
- Prevent restart startup from inheriting ready state from a stale previous process surface.
- Prevent the capture harness from submitting the next operation before the current operation has visibly started and returned to ready.
- Make the replay comparison reproducible and explicit about legacy generated labels versus direct UC-03 labels.
- Demonstrate the improvement on canonical and reduced-cadence replay from the existing recordings.

**Non-Goals:**

- Changing public tracked-state field names or gateway APIs.
- Treating historical queue, retry, spinner, or selector text as current activity.
- Claiming full UC-03 end-to-end qualification from old long-horizon recordings that contain no gateway admission or mail-notifier behavior.
- Eliminating every one-frame disagreement at a sampled transition boundary.

## Decisions

### Queue and pending-input panes are current busy evidence

Kimi queue facts will be extracted from the bounded latest-turn region using the three source-backed queue hints. A current queue pane sets active evidence, `ready_posture=no`, and blocks success. Existing moon and braille spinner detection remains authoritative when visible.

Codex will recognize all three `PendingInputPreview` section headers. Those headers will be treated as non-response cells so they cannot stop the reverse scan before a live status row, and a current section will independently contribute active evidence when the status row is hidden.

This is preferred over widening arbitrary text windows because the upstream components give the retained-input text a precise semantic role. Historical matching text still does not count when a later assistant response or current-turn boundary proves it stale.

### Retry and selector recognition use bounded source shapes

Codex retry detection will match the source-backed reconnect status family rather than any occurrence of words such as `retry`. Blocking list selectors will be recognized by a current list-selection footer together with a bounded selector title or selection rows. The detector will not scan arbitrary transcript history for either signal.

### Restart readiness is generation-scoped

The existing runtime observer already makes readiness unavailable while the supported process is down, but its selected PID can move between wrappers and children during startup. The detector boundary therefore provides the stable generation delimiter: when a retained pane contains a newer shell launch command below old provider chrome, Codex and Kimi detector profiles ignore all prompt rows above that boundary. Ordinary detection resumes only after fresh provider chrome renders below the latest shell command. This prevents old screen content from becoming authoritative for a new process without treating a transient wrapper PID as a generation identity.

### Capture ready gates require a lifecycle edge

For a prompt-submitting operation, the long-horizon gate will not accept `ready` until it has observed provider-specific active evidence or another explicit post-submit progress edge. Kimi active evidence includes moon/braille activity and all queue hints. Codex includes a current running row and all pending-input sections. After the start edge, two stable ready polls remain required.

Startup and non-submit operations may use the existing unanchored ready gate because no just-submitted lifecycle must be observed.

### Replay labels and tracker mapping remain separate

Direct UC-03 labels will carry `label`, source interval, visible evidence, rubric digest, and review metadata. Tracker output alone is mapped into comparison labels. Diagnostic unavailability takes precedence over activity, draft, overlay, and ready classification. `busy_overlay` requires explicit overlay evidence; it is not inferred from every unknown posture.

Legacy generated labels remain usable as an exploratory trend line, but reports will name them `legacy_reference` and will not call them independent human ground truth. Full `ready_immediate` qualification still requires live behavioral admission evidence.

### Recorded replay is the implementation gate

Focused unit tests will use exact source-backed surface snippets and selected frozen samples. The canonical replay must remove the long sustained Kimi ST03 and Codex ST05 false-ready blocks. Reduced-cadence schedules at 10, 5, and 2 Hz must preserve busy-before-ready ordering. Residual disagreements are acceptable only when inspection shows a short transition boundary, legacy-label defect, or unsupported behavioral conclusion; every residual class must be counted and explained.

## Risks / Trade-offs

- **[Risk] Exact visible strings may change in later provider versions.** → Bind the rules to the maintained profile version, keep them in bounded structural regions, and add source-snapshot regression tests.
- **[Risk] Queue text can remain visible after a turn boundary.** → Require a current bounded queue section with no later assistant response and retain temporal settlement behavior.
- **[Risk] A process PID can change through a wrapper before the TUI renders.** → Use generation-scoped fresh-surface proof rather than PID presence alone.
- **[Risk] The legacy label corpus can still report correct tracker behavior as a mismatch.** → Separate legacy and direct-label verdicts and retain inspected residual explanations.
- **[Risk] Requiring a start edge can time out on extremely short prompts.** → Qualification stimuli already require observable active spans; report `stimulus_too_short` rather than sending the next prompt unsafely.

## Migration Plan

No persisted-state migration is required. Deploy detector, live-tracking, and qualification changes together, replay the frozen corpus, and then use the corrected capture gate for fresh runs. Rollback restores the previous detector and harness code; public API payloads remain compatible.

## Open Questions

- Full direct UC-03 labeling still belongs to the separate qualification-harness change; this fix accepts reviewer-approved direct intervals when present and names the old generated state labels as a legacy reference.
- Full direct UC-03 relabeling of all 11,202 old samples is optional for this prerequisite change; representative direct intervals plus the legacy trend comparison are sufficient to verify the detector fix, while the separate UC-03 harness change owns full qualification labels.
