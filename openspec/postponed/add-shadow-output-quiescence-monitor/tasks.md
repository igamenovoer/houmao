## 1. Shadow Timing Policy

- [ ] 1.1 Extend shadow-mode runtime configuration/loading to support `ready_quiet_window_seconds` and `completion_quiet_window_seconds` alongside the existing stalled policy fields.
- [ ] 1.2 Surface the effective shadow timing policy values in `shadow_only` diagnostics and error/report payload shaping.
- [ ] 1.3 Add configuration validation tests for positive quiet-window values, defaults, and backwards-compatible behavior when the new fields are unset.

## 2. Observation And Quiescence Engine

- [ ] 2.1 Introduce internal shadow observation/change-signal models that carry parsed snapshot data plus transport/projection fingerprints.
- [ ] 2.2 Extract lifecycle reduction logic from `cao_rest.py` into a reducer-oriented shadow monitor component that can consume observation events and timer events.
- [ ] 2.3 Implement RxPY-based quiescence/unknown timing composition with injectable schedulers so countdowns restart on fresh tmux output changes.

## 3. CAO Shadow Lifecycle Integration

- [ ] 3.1 Update shadow readiness monitoring to require both `accepts_input` and a satisfied readiness quiet window before submitting terminal input.
- [ ] 3.2 Update shadow completion monitoring to require post-submit progress evidence plus a satisfied completion quiet window before marking the turn complete.
- [ ] 3.3 Update stalled handling so unknown-with-churn resets the stalled countdown, while stable unknown still enters `stalled` according to policy.

## 4. Verification And Documentation

- [ ] 4.1 Add runtime unit tests for readiness settling, completion quiet-window restart behavior, and unknown-with-churn vs stable-unknown stalled behavior.
- [ ] 4.2 Add reactive-timing tests using `reactivex.testing.TestScheduler` or equivalent deterministic scheduler coverage for the new observation pipeline.
- [ ] 4.3 Update shadow parsing/runtime lifecycle docs and reference docs to describe quiescence as a runtime-owned concept and document the new timing policy fields.
