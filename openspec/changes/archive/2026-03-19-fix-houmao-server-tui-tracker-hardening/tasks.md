## 1. Registration Safety

- [x] 1.1 Add server-owned validation and containment checks for registration storage keys before any registration write or delete
- [x] 1.2 Update `HoumaoRegisterLaunchRequest` and related registration helpers so registration-derived identity can carry optional tmux window metadata

## 2. Tracker Lifecycle Hardening

- [x] 2.1 Harden the supervisor reconcile loop so unexpected exceptions are recorded or logged and do not permanently stop background tracking
- [x] 2.2 Harden per-session polling so unexpected worker-cycle failures surface explicit live-state errors and do not permanently kill a still-live worker
- [x] 2.3 Add a runtime eviction path that removes stale worker bindings, trackers, and terminal aliases when a session leaves live authority

## 3. Registration-Derived Pane Identity

- [x] 3.1 Enrich registration-seeded tracker creation with tmux window metadata from the request or manifest before the first polling cycle
- [x] 3.2 Ensure initial pane resolution uses the preserved registration-derived identity instead of falling back blindly to the active pane

## 4. Verification

- [x] 4.1 Add unit tests for invalid registration identifiers and root-contained cleanup behavior
- [x] 4.2 Add unit tests proving supervisor and worker loops remain operational after unexpected runtime exceptions
- [x] 4.3 Add unit tests proving tmux loss or registry removal evicts stale aliases and trackers from live-state lookup
- [x] 4.4 Add unit tests covering registration-to-window propagation and first-cycle pane selection fidelity
