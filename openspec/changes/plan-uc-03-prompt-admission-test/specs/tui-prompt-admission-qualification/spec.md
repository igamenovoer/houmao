## ADDED Requirements

### Requirement: UC-03 qualification harness SHALL reuse existing long-horizon tmux recordings as development fixtures

The qualification harness SHALL be able to load existing tmux recordings from `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/` and replay their captured state through the current non-forced admission predicate. This replay mode is for harness development and simulator validation only; it does not replace live UC-03 qualification.

#### Scenario: Simulator replays a long-horizon recording and emits admission decisions
- **WHEN** a maintainer runs the admission-consumer simulator against an existing long-horizon recording
- **THEN** the simulator emits `would_admit`, `blockers`, and `decision_time` for each recorded sample
- **AND THEN** the output format matches the live admission trace so the same comparator can be used for both fixture and live runs

### Requirement: Admission-consumer simulator SHALL apply the current gateway non-forced admission predicate

The simulator SHALL evaluate the same predicate that the live gateway uses for `POST /v1/control/prompt` non-forced dispatch. It SHALL consider `turn.phase`, `surface.accepting_input`, `surface.editing_input`, `surface.ready_posture`, `stability.stable`, gateway execution idle state, durable queue depth, and parsed-surface evidence when available.

#### Scenario: Simulator refuses a sample that the live gateway would refuse
- **WHEN** a recorded sample shows `surface.ready_posture=no` and `turn.phase=active`
- **THEN** the simulator emits `would_admit=false`
- **AND THEN** `blockers` includes the public fields that caused the refusal

#### Scenario: Simulator admits a sample that the live gateway would admit
- **WHEN** a recorded sample shows `turn.phase=ready`, `surface.ready_posture=yes`, `surface.editing_input=no`, `surface.accepting_input=yes`, `stability.stable=true`, and idle gateway state
- **THEN** the simulator emits `would_admit=true`
- **AND THEN** `blockers` is empty

### Requirement: CAL-01 procedure SHALL calibrate provider-native busy-input behavior in a disposable session

The harness SHALL run CAL-01 once per maintained provider. It SHALL submit a long read-only prompt, wait for independently visible active evidence, submit a unique forced canary with `--force`, and classify the provider-native disposition as `queued_for_later`, `steered_into_current_turn`, `provider_rejected`, or `immediate_independent_turn`.

#### Scenario: CAL-01 produces a native-busy-input classification record
- **WHEN** CAL-01 runs for a maintained provider
- **THEN** the procedure creates `calibration/<provider>/native-busy-input.json`
- **AND THEN** the record contains the provider version, exact forced canary, active source samples, native behavior class, retention signatures, and cleanup proof
- **AND THEN** the disposable session is destroyed and never reused for qualification

### Requirement: AR-01 procedure SHALL qualify direct ready-or-refuse prompt control

The harness SHALL run AR-01 once per maintained provider using only non-forced gateway prompt control. It SHALL alternate ready, active, draft, and overlay surfaces and verify that the gateway returns `sent=true` only when independent native evidence is `ready_immediate` and returns `error_code=not_ready` for every busy surface.

#### Scenario: AR-01 refuses busy surfaces and admits ready surfaces
- **WHEN** AR-01 runs for a maintained provider
- **THEN** every operation expected to refuse returns non-zero with structured `error_code=not_ready` and leaves no provider input, durable gateway request, or retained canary text
- **AND THEN** every operation expected to admit returns `sent=true` and the exact canary becomes the next independent active turn within `native_active_deadline`

### Requirement: AR-02 procedure SHALL qualify mail-notification release across busy-to-ready

The harness SHALL run AR-02 once per maintained provider. It SHALL enable a one-second unread-only mail notifier, start a long active turn, post one operator-origin important message while busy, observe at least two `busy_skip` polls, and prove exactly one `enqueued` internal prompt after stable ready evidence, which begins immediately.

#### Scenario: AR-02 skips mail while busy and releases after ready
- **WHEN** AR-02 runs for a maintained provider
- **THEN** at least two notifier polls record `outcome=busy_skip` while the long turn is independently active
- **AND THEN** no `mail_notifier_prompt` is created while busy
- **AND THEN** within `notifier_release_deadline` after stable ready evidence, one audit row records `outcome=enqueued` and the notification prompt becomes the next active turn immediately

### Requirement: Independent labels SHALL remain blind to tracker and gateway output

The operator or maintainer SHALL label native recordings using only visible behavioral evidence. Labels SHALL use the values `ready_immediate`, `busy_active`, `busy_draft`, `busy_overlay`, and `indeterminate`. The label author SHALL NOT view tracker output, gateway decisions, or notifier audit rows before signing labels.

#### Scenario: Human labels are created without tracker influence
- **WHEN** a maintainer labels a UC-03 recording
- **THEN** the label file cites visible behavioral evidence per sample
- **AND THEN** the label file does not reference tracker fields, gateway payloads, or notifier outcomes

### Requirement: Verdict generation SHALL distinguish classification, admission, delivery, and scenario verdicts

The harness SHALL produce four separate verdicts per checkpoint and per run: `classification_verdict`, `admission_verdict`, `delivery_verdict`, and `scenario_verdict`. It SHALL report the first divergent source sample, the attempted outside prompt or mail event, the tracker blockers, the gateway decision, and the provider-visible consequence for every failure.

#### Scenario: A false-ready admission produces a safety failure record
- **WHEN** the harness detects that a non-forced prompt was admitted while independent native evidence was busy
- **THEN** the report records `false_ready_admission`
- **AND THEN** it preserves the complete provider queue or steering consequence and stops the qualification session

#### Scenario: A false-busy interval beyond the readiness deadline produces an availability failure record
- **WHEN** the gateway remains closed after stable `ready_immediate` ground truth exceeds `readiness_deadline`
- **THEN** the report records `false_busy_late_recovery` or `false_busy_stuck`
- **AND THEN** it preserves all reported blockers and extended evidence
