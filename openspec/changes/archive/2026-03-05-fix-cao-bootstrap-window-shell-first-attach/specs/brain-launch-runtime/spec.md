## ADDED Requirements

### Requirement: CAO session startup fixes "shell-first attach" and prunes the bootstrap window when safe
For CAO-backed session startup (`backend=cao_rest`), when the runtime pre-creates
one bootstrap tmux window for env setup and CAO subsequently creates the real
agent terminal window, the runtime SHALL (best-effort) make the CAO terminal
window the session's current tmux window and SHALL prune the bootstrap window
when it can be safely identified as distinct from the CAO terminal window.

The runtime SHALL record the bootstrap tmux `window_id` immediately after
session creation and SHALL use `window_id` targeting (not index assumptions) for
window selection and pruning.

The runtime SHALL resolve the CAO terminal window id from `terminal.name` using
bounded retry (to tolerate transient tmux visibility races). If the CAO window
cannot be resolved within the bound, startup still succeeds and the runtime
emits a warning diagnostic.

The runtime SHOULD use the `create_terminal(...)` response `terminal.name` as
the CAO tmux window name (no extra `GET /terminals/{id}` is required solely to
obtain the name).

#### Scenario: Successful CAO startup leaves only the agent terminal window (and first attach lands on it)
- **WHEN** a developer starts a CAO-backed session and terminal creation succeeds
- **AND WHEN** the recorded bootstrap window differs from the resolved CAO terminal window
- **THEN** the runtime selects the CAO terminal window as the session's current window
- **AND THEN** the runtime removes the recorded bootstrap window from that tmux session
- **AND THEN** the tmux session remains active with the CAO terminal window

### Requirement: Bootstrap-window pruning is targeted and non-fatal
Bootstrap-window pruning for CAO-backed startup SHALL be best-effort.
The runtime SHALL target only the recorded bootstrap window and SHALL NOT
terminate the resolved CAO terminal window.

#### Scenario: Startup does not fail when bootstrap-window pruning fails
- **WHEN** CAO terminal creation succeeds but bootstrap-window pruning returns an error
- **THEN** `start-session` still succeeds and returns the selected agent identity
- **AND THEN** the runtime selects the CAO terminal window as the session's current window (best-effort)
- **AND THEN** the runtime emits a warning diagnostic describing the prune failure

#### Scenario: Startup warns when CAO terminal window cannot be resolved within the bound
- **WHEN** CAO terminal creation succeeds but the runtime cannot resolve `terminal.name` to a tmux `window_id` within the bounded retry policy
- **THEN** `start-session` still succeeds
- **AND THEN** the runtime emits a warning diagnostic describing the resolution failure

#### Scenario: Runtime skips prune when bootstrap and terminal window are the same
- **WHEN** the recorded bootstrap window resolves to the same tmux window as the CAO terminal
- **THEN** the runtime skips bootstrap-window deletion
- **AND THEN** the CAO terminal remains active for subsequent prompt/stop operations
