## 1. Runtime Mailbox Eligibility

- [ ] 1.1 Remove the joined-session mailbox-registration guard that rejects local joined tmux sessions solely because `agent_launch_authority.posture_kind` is `unavailable`.
- [ ] 1.2 Reuse the existing tmux live-mailbox refresh path for joined-session mailbox register and unregister flows so durable mailbox state and tmux live projection stay coherent.
- [ ] 1.3 Update runtime activation-state computation so joined tmux sessions report `active` after successful live mailbox projection refresh instead of `unsupported_joined_session`.

## 2. Managed-Agent And Gateway Behavior

- [ ] 2.1 Update local managed-agent mailbox status and mail-command readiness checks so joined tmux sessions with refreshed live mailbox projection are treated as mailbox-active.
- [ ] 2.2 Update gateway mail-notifier support and enablement logic so joined tmux sessions do not require relaunch posture once durable mailbox capability and live mailbox actionability are both present.
- [ ] 2.3 Update the top-level `houmao-mgr` wrapper so expected mailbox-management and gateway mail-notifier failures render as clean CLI errors without Python tracebacks.
- [ ] 2.4 Keep joined-session relaunch behavior unchanged and ensure mailbox activation does not create implicit relaunch authority.

## 3. Verification And Documentation

- [ ] 3.1 Add unit coverage for joined-session mailbox register and unregister flows, including activation-state reporting and status/readiness behavior.
- [ ] 3.2 Add gateway notifier regression coverage for joined tmux sessions that are mailbox-actionable despite unavailable relaunch posture.
- [ ] 3.3 Add CLI regression coverage that expected mailbox-management and mail-notifier failures exit non-zero without emitting Python tracebacks.
- [ ] 3.4 Update mailbox workflow docs to state explicitly that joined tmux sessions can late-register mailbox support without relaunch when Houmao can refresh live tmux mailbox bindings safely.
- [ ] 3.5 Verify the full operator flow against a real joined TUI session: `agents mailbox register`, `agents mail status`, and `agents gateway mail-notifier status|enable`, including clean failure rendering where applicable.
