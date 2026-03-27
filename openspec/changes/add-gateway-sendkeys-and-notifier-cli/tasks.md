## 1. Native CLI surface

- [ ] 1.1 Extract a shared `agents gateway` target resolver that supports explicit selectors plus manifest-first current-session discovery inside tmux.
- [ ] 1.2 Add `houmao-mgr agents gateway send-keys` with `--sequence` and `--escape-special-keys`, using the shared gateway target resolver.
- [ ] 1.3 Add `houmao-mgr agents gateway mail-notifier status|enable|disable`, including `--interval-seconds` validation for enable.
- [ ] 1.4 Extend the supported gateway commands to fail clearly when no selector is available outside tmux or when current-session discovery metadata is stale or missing.

## 2. Pair and proxy APIs

- [ ] 2.1 Add `houmao-server` managed-agent gateway raw control-input support at `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`, including client and service bindings.
- [ ] 2.2 Add `houmao-passive-server` proxy support for `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`.
- [ ] 2.3 Add `houmao-passive-server` proxy support for `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`, including passive client bindings.

## 3. Verification and docs

- [ ] 3.1 Add native CLI tests for explicit selector and same-session tmux targeting for gateway send-keys and mail-notifier commands.
- [ ] 3.2 Add `houmao-server` and `houmao-passive-server` API contract tests for gateway send-keys and notifier proxy behavior, including no-gateway and ambiguity failures.
- [ ] 3.3 Update repo-owned CLI and gateway docs to describe the new commands and the inside-tmux versus outside-tmux targeting rules.
