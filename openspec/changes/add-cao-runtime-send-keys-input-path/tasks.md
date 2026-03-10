## 1. Runtime surface

- [ ] 1.1 Add a dedicated `send_input_ex()` runtime control-input surface that is separate from `send_prompt` turn semantics, reusing `SessionControlResult` with `action="control_input"` and initial backend-specific `isinstance` dispatch for the CAO-only release.
- [ ] 1.2 Add a `send-keys` CLI command with required `--agent-identity` and `--sequence`, the global `--escape-special-keys` flag, the usual optional `--agent-def-dir`, and a single JSON control-action result output while keeping `send-prompt` unchanged.

## 2. Sequence parsing and tmux delivery

- [ ] 2.1 Implement the mixed-sequence parser for literal text plus exact `<[key-name]>` tokens, including strict case-sensitive token handling and global escape mode.
- [ ] 2.2 Add tmux delivery helpers that send literal text segments with `tmux send-keys -l` and send special-key tokens with tmux key names in-order, without implicit trailing `Enter`.
- [ ] 2.3 Return explicit errors for invalid exact key tokens, preserve non-matching marker-like substrings as literal text, and guarantee support for at least `Enter`, `Escape`, `Up`, `Down`, `Left`, `Right`, `Tab`, `BSpace`, `C-c`, `C-d`, and `C-z`.

## 3. CAO backend integration

- [ ] 3.1 Extend CAO session state and manifest persistence with optional `tmux_window_name` metadata for manifest-driven tmux target resolution, keeping older manifests usable through live fallback and avoiding any schema-version bump.
- [ ] 3.2 Wire the CAO runtime backend `send_input_ex()` path to resolve tmux targets from persisted session state plus CAO terminal metadata and deliver raw control-input sequences.
- [ ] 3.3 Reject unsupported non-CAO backends and unresolved tmux targets with explicit control-input errors.

## 4. Verification and docs

- [ ] 4.1 Add unit and integration coverage for mixed sequences, escape mode, no-auto-enter behavior, invalid exact tokens, manifest-driven target resolution, and non-CAO rejection.
- [ ] 4.2 Update runtime operator/developer docs to explain when to use `send-prompt` versus the new raw control-input command.
- [ ] 4.3 Update the CAO interrupt/demo flow to replace only the direct escape-key tmux injection with the runtime-owned control-input path, leaving the existing CAO/shadow-parser observation flow intact.
