## 1. Gateway Selector Surface

- [x] 1.1 Add `--target-tmux-session <tmux-session-name>` to the single-target `houmao-mgr agents gateway ...` commands that already support explicit selectors.
- [x] 1.2 Rename the gateway command family's explicit pair-authority override from `--port` to `--pair-port`, and update help text and errors so the flag is not confused with gateway listener port overrides.
- [x] 1.3 Enforce selector exclusivity across `--agent-id`, `--agent-name`, `--target-tmux-session`, and `--current-session`, and preserve the existing rule that omitted selectors inside tmux mean current-session targeting.
- [x] 1.4 Reject `--pair-port` when the command targets `--target-tmux-session` or `--current-session`, while keeping `--pair-port` valid for explicit `--agent-id` and `--agent-name` targeting.

## 2. Tmux-Session Resolution

- [x] 2.1 Add a local resolution helper that targets an explicit tmux session by name, prefers that session's `HOUMAO_MANIFEST_PATH`, and validates the resolved manifest against the addressed tmux session.
- [x] 2.2 Add shared-registry fallback for tmux-session targeting by exact `terminal.session_name`, including explicit failure behavior for stale, missing, or ambiguous matches.
- [x] 2.3 Route tmux-session-targeted gateway operations through the existing pair-managed attach path or local resumed-controller path after local resolution, without changing existing `--agent-id` and `--agent-name` behavior.

## 3. Documentation And Coverage

- [x] 3.1 Update the CLI reference pages for `houmao-mgr agents gateway` and the top-level targeting guidance to document `--target-tmux-session`, selector exclusivity, `--pair-port`, and the pair-authority versus gateway-listener port distinction.
- [x] 3.2 Update the gateway operational docs to explain when to use `--target-tmux-session` versus `--current-session`, how manifest-first plus shared-registry fallback works, and what `--pair-port` refers to.
- [x] 3.3 Add unit coverage for selector parsing, tmux-session resolution, registry fallback, the `--pair-port` rename, and `--pair-port` rejection with `--target-tmux-session`.
- [x] 3.4 Add integration or workflow coverage for outside-tmux gateway attach using `--target-tmux-session` on representative local and pair-managed sessions, then run OpenSpec validation for the change.
