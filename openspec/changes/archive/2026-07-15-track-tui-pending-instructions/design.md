## Context

The shared tracker currently publishes three prompt-surface observables (`accepting_input`, `editing_input`, and `ready_posture`) plus a turn phase. Codex and Kimi detectors already notice provider-native queued input as active evidence, but that fact is flattened into `turn.phase=active`. Claude does not yet expose an equivalent signal. Downstream callers therefore see the same state for “busy with no submitted follow-up” and “busy with a submitted follow-up already retained by the CLI.”

Direct gateway prompt control has one `force` boolean. Without force it requires a stable prompt-ready posture; with force it bypasses readiness. That binary interface cannot express “submit while busy only if no provider-native prompt is already pending.” The UC05 recordings and their 1/2/3-pending extensions provide high-rate pane evidence for Claude Code, Codex CLI, and Kimi Code, but their labels were generated from capture patterns and require human audit before they become qualification ground truth. The Claude recording metadata also disagrees with the version visible in the pane header and must be corrected or explicitly explained.

This is a breaking, cross-cutting change. There is no compatibility requirement for old gateway prompt payloads, result shapes, CLI flags, or replay-label schemas. TUI support covers Claude Code, Codex CLI, and Kimi Code only; Gemini CLI remains out of scope.

## Goals / Non-Goals

**Goals:**

- Publish whether the visible provider TUI holds at least one submitted prompt behind the active turn.
- Preserve the distinction among ready input, user-authored draft input, provider-native pending input, and gateway-durable queued work.
- Let direct prompt callers choose among ready-only submission, submission when no provider-native prompt is pending, and unconditional TUI submission.
- Make the admission decision deterministic from one latest tracked snapshot while accepting normal observation-to-repaint races.
- Detect Claude pending input from stable bounded structure and rendering semantics rather than exact suggestion wording.
- Qualify provider detectors under high-rate, low-rate, and irregular replay and verify gateway behavior from both replay-driven and live evidence.

**Non-Goals:**

- Counting pending prompts in the public runtime state. Pending count remains auxiliary dataset and diagnostic evidence.
- Serializing prompt submissions across callers, reserving a pending slot, or guaranteeing compare-and-submit atomicity.
- Treating Houmao prompt-submission notes or gateway request records as proof that the provider TUI currently displays pending input.
- Changing the durable `POST /v1/requests` queue contract.
- Allowing overlapping native-headless executions or inventing pending-input semantics for headless tools.
- Supporting Gemini CLI or simulating provider/network failures that the existing test plan excludes.

## Decisions

### Add an orthogonal tristate surface observable

The canonical tracked surface gains:

```text
surface.pending_input = yes | no | unknown
```

`yes` means the current visible TUI contains decisive provider-native evidence that at least one already-submitted instruction is waiting behind the active turn. `no` means the captured surface is complete enough to make a negative decision and contains no such evidence. `unknown` means the provider/profile is unsupported for this fact or the capture is cropped, transitioning, or structurally ambiguous.

The field is independent of `surface.editing_input`: editing describes text still in the current composer, while pending describes text already submitted to the provider CLI. It is also independent of the gateway durable queue. The reducer does not infer pending input from `turn.phase`, active reasons, explicit prompt notes, or recent Houmao dispatches.

The field flows through normalized detector signals, temporal hints when needed, current snapshots, transitions, bounded history, compact and detailed API responses, terminal-record timelines, labels, replay output, comparisons, review overlays, and operator-facing state rendering. It participates in the operator-visible state/stability signature so `no → yes` and `yes → no` produce observable transitions even while `turn.phase` stays `active`.

**Rationale:** Pending input changes whether a later prompt should be admitted, but it does not replace any current readiness or lifecycle state. An orthogonal tristate keeps compound states representable:

| Turn posture | Pending input | Meaning |
| --- | --- | --- |
| `ready` | `no` | A new prompt should be processed immediately. |
| `active` | `no` | Busy, with no visible provider-native follow-up. |
| `active` | `yes` | Busy, with at least one visible provider-native follow-up. |
| any | `unknown` | The pending fact is not safe to use for conditional admission. |

**Alternative considered:** Add `queued` to `turn.phase`. Rejected because queue presence and turn lifecycle are independent facts and a phase expansion would still fail to represent compound states cleanly.

**Alternative considered:** Publish a queue count. Rejected as a required runtime contract because providers cap, collapse, wrap, or hide multiple queued prompts differently. Count remains useful qualification metadata, while admission needs only presence.

### Keep provider detection profile-owned and conservative

Each selected provider profile emits `pending_input` with evidence scoped to the current live surface.

- Codex uses the existing bounded queued-follow-up/pending-input structure, promoted from an internal active reason into the normalized tristate signal. Exact queued prompt text is irrelevant.
- Kimi uses its current queue-visible structure and queued-message evidence, likewise promoted into the normalized signal.
- Claude locates the bottom composer region and its separator frame, applies the existing profile-owned semantic classifier to distinguish empty/draft/ghost-suggestion content, and then inspects the bounded region immediately above that composer. It reports `yes` only for an indented, non-empty Claude user-input cell in the queued-preview position with no intervening assistant response, tool block, or current activity cell. When required boundaries are absent or cropped, it reports `unknown`.

Claude prompt-area suggestion wording is never positive or negative queue evidence. A pure ghost suggestion is classified by rendering/style semantics owned by the selected version profile. The suggestion may change wording, disappear, or be localized without changing the queue result. The queued preview cell, not text such as “Press up to edit queued messages,” establishes pending input.

Claude tests include arbitrary and localized ghost wording, a queued row with no suggestion, a ghost suggestion with no queued row, transcript prose containing queue-like words, a historical user cell separated by output, wrapped queued content, resizes, and cropped frames. Unknown style or incomplete structure degrades to `unknown`, not a confident `no`.

**Rationale:** Provider-native queue surfaces drift independently. Profile ownership keeps those details out of the shared reducer, while structural bounds prevent stale transcript text from creating false positives.

**Alternative considered:** Match exact provider sentences. Rejected because suggestion and status wording changes across provider versions and locales; the current Claude prompt classifier already demonstrates a style-aware boundary.

### Replace force with one explicit admission-policy enum

The direct prompt-control request schema advances to version 2 and replaces `force` with:

```text
admission_policy = ready_only | if_no_pending | always
```

The default is `ready_only`. The success and structured-refusal payloads replace `forced` with `admission_policy`. Gateway events and errors record the selected policy and the observed pending/readiness facts used by the decision. Old schema-version-1 payloads and payloads containing `force` fail validation; no alias or translation layer remains.

The maintained CLI exposes:

```text
--admission-policy ready-only|if-no-pending|always
```

and removes `--force`. Hyphenated CLI values map directly to underscore-form API enum values.

For TUI-backed direct prompt control, the decision table is:

| Policy | Existing stable prompt-ready contract | `surface.pending_input` | Decision |
| --- | --- | --- | --- |
| `ready_only` | satisfied | `no` | dispatch |
| `ready_only` | not satisfied | any | refuse `not_ready` |
| `ready_only` | satisfied | `yes` or `unknown` | refuse pending conflict/uncertainty |
| `if_no_pending` | ignored | `no` | dispatch, even while busy |
| `if_no_pending` | ignored | `yes` | refuse `pending_input` |
| `if_no_pending` | ignored | `unknown` | refuse `pending_input_unknown` |
| `always` | ignored | any | dispatch |

All policies still enforce structural gateway availability, attachment, reconciliation, target compatibility, payload validity, and adapter support. `if_no_pending` and `always` are TUI-only. Headless targets accept `ready_only` and reject the other policies because headless execution has no provider-native visible queue and must not overlap active work. TUI `chat_session.mode=new` also requires `ready_only`, since reset-then-send is a readiness-dependent multi-step workflow rather than queue injection.

The `if_no_pending` policy intentionally ignores other surface facts, including busy and editing posture. Its narrow contract is “dispatch when the latest observation decisively shows no provider-native submitted prompt.” Callers that want all readiness safeguards use `ready_only`; callers that want no observation safeguard use `always`.

**Rationale:** One enum makes the three caller intents explicit and avoids invalid combinations of two booleans. Removing force is acceptable because this release has no compatibility obligation.

**Alternative considered:** Keep `force` and add `force_if_no_pending`. Rejected because both flags could be supplied together and every API/CLI consumer would need precedence rules.

### Make admission observational, not atomic

Each request evaluates the latest gateway-owned tracked snapshot and dispatches according to its selected policy. The implementation does not reserve the observed no-pending state and does not hold a new cross-request lock until the CLI repaints.

Two concurrent or closely spaced `if_no_pending` calls can both observe `pending_input=no` and both dispatch. The provider CLI may queue both. After a later capture publishes `pending_input=yes`, subsequent `if_no_pending` calls back off; `always` calls still dispatch. This behavior is part of the contract, not a race defect.

**Rationale:** The feature controls later behavior from observable provider state. It does not need exactly-one admission during the repaint interval, and provider-native queueing remains the final submission sink.

**Alternative considered:** Add a gateway reservation or submission mutex. Rejected because it would create a Houmao shadow queue state, complicate recovery, and contradict the intended observational semantics.

### Keep TUI observation authoritative after Houmao dispatch

`note_prompt_submission()` continues to arm explicit-input/turn provenance after semantic prompt dispatch, but it does not set or predict `surface.pending_input`. A busy `if_no_pending` or `always` dispatch therefore remains `pending_input=no` until the selected provider profile sees decisive queued structure in a later pane capture.

The same rule applies to gateway durable requests, reminder delivery, mail notifier activity, and raw send-keys. None of those internal records become public pending-input truth.

**Rationale:** A dispatch can fail to render, be consumed immediately, or be transformed by the CLI. Only the visible provider surface answers whether a provider-native prompt is currently pending.

### Qualify with audited recordings, cadence variation, and live policy runs

Qualification uses the UC05 datasets referenced by the feature plan, including the 1/2/3-pending extensions. Before scoring, a maintainer audits the label boundaries in rendered review videos, records corrections, and resolves the Claude version-provenance mismatch. Pattern-generated labels are calibration aids, not the final oracle.

Detector validation has four layers:

1. Provider unit fixtures cover decisive positive, decisive negative, boundary, wrapped, resized, cropped, and stale-transcript cases. Claude receives the wording/style negatives listed above.
2. Canonical replay runs the frozen 20 Hz pane snapshots and compares `surface.pending_input` sample by sample with audited labels.
3. Cadence stress derives deterministic 10 Hz, 5 Hz, and 2 Hz streams plus seeded jitter, frame-drop, and burst variants. Comparisons use the labels for the retained samples. A slower stream may skip a short transition, but any sampled decisive queued span must remain meaningful: no false `no` while complete positive structure is visible, no queue-like oscillation caused only by cadence, and transition drift bounded by one retained sample interval.
4. Multi-count recordings verify that the binary field stays `yes` for one, two, and three visible pending prompts and returns to `no` after the last queued preview is consumed. Provider caps or tainted runs are reported rather than silently treated as full coverage.

Admission validation uses table-driven unit tests over all policy/readiness/pending combinations and a replay-driven fake adapter that advances through recorded busy-no-pending, busy-pending, consumed, and ready snapshots while counting actual submissions. It explicitly verifies that two submissions before repaint may both succeed, that later `if_no_pending` backs off once replay reaches `yes`, and that `always` still dispatches.

Live unattended qualification runs once per supported provider through the real gateway and `houmao-mgr` path. It records tmux and gateway evidence under a fresh `tmp/<subdir>`, produces review video and a timestamped report, and verifies the policy sequence against the live CLI. Codex runs inherit the configured test proxy from the environment (currently port 7990); the port is not hard-coded into product code or generic launch guidance. No Gemini run is included.

**Rationale:** Existing recordings can prove detector and replay behavior, but they were driven through direct tmux input and cannot alone prove gateway admission or CLI forwarding. The live layer closes that gap.

## Risks / Trade-offs

- **[Risk]** A provider changes queue layout or styling. **Mitigation:** Keep detectors version-profile-owned, use bounded structural evidence, return `unknown` for unrecognized structure, and retain replay fixtures per observed version family.
- **[Risk]** Pattern-generated labels share assumptions with the capture patterns and create circular validation. **Mitigation:** Human-audit the videos and persist corrections before using labels as the acceptance oracle.
- **[Risk]** Low-cadence replay skips a short pending transition. **Mitigation:** Score retained decisive samples and bounded transition drift instead of requiring an unobserved transition to be reconstructed.
- **[Risk]** `if_no_pending` dispatches twice before the TUI repaints. **Mitigation:** Document this as accepted observational behavior and test it explicitly; later calls react to the next observed `yes` state.
- **[Risk]** A cropped pane produces a false negative and admits a prompt. **Mitigation:** Require complete provider-specific structure for `no`; ambiguous captures become `unknown`, which blocks both conditional policies.
- **[Trade-off]** Adding one public field changes snapshots, transitions, fixtures, and response schemas broadly. **Acceptance:** The field is needed by downstream admission and is safer than encoding queue state in notes or provider-specific reasons.

## Migration Plan

1. Expand shared detector, temporal-hint, snapshot, transition, public surface, history, recording, and replay models with required `pending_input` fields; update all constructors and fixtures in one breaking pass.
2. Implement and unit-test the Codex, Kimi, and structural/style-aware Claude signals, then thread them through reducer and stability semantics.
3. Update passive-server observation and managed-agent projections, terminal-record labels/replay/comparison, renderers, and review videos.
4. Replace gateway prompt-control schema version 1 with version 2, implement the admission decision table, update proxy/client layers, and replace `--force` with `--admission-policy` throughout `houmao-mgr`.
5. Update documentation and the packaged messaging skill, then update all in-repository callers and tests. Do not retain compatibility parsing or deprecated flags.
6. Audit and replay the recorded datasets, run cadence variants, execute the unattended live provider matrix, and save qualification reports and artifact pointers.

Rollback requires reverting the runtime, API, CLI, docs, and tests together because the public schemas change atomically. Existing raw pane recordings remain usable, but old request payloads and old label files are not supported without updating them to the new contract.

## Open Questions

None. Pending count remains diagnostic-only, admission is explicitly observational, and Claude matching is defined by bounded structure plus profile-owned rendering semantics.
