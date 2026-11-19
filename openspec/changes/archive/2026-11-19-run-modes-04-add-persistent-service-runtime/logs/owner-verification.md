# Persistent Owner Verification

The runtime starts a service owner in the recorded tmux server. The owner publishes a private socket descriptor after the provider initializes its native session. Every attach checks the descriptor's generation and incarnation, the socket inode, the owning account, and the owner's process birth identity. Linux kernel peer credentials associate each request with its caller process. The public state carries the native session and service incarnation. Socket and process authority stay in the private descriptor.

The owner stores one request at a time. It checks the same owner reservation used by the manager and gateway again before native input. Each request record distinguishes reservation, native write, confirmed handoff, and terminal outcome. The record can stay active independently of its response socket. Provider loss after native write yields uncertainty and blocks new prompts. Interruption selects the active request identity before issuing native cancellation, and a stale request cannot cancel a replacement.

Stop closes the owned provider and reaps detached Linux descendants that the supervisor adopted. If the control socket becomes unavailable, explicit stop can still use the saved process birth identity to target the exact owner and native process. An explicit relaunch starts a new service incarnation and can resume the same recorded native conversation. A lost owner withdraws readiness and marks its active request uncertain, even when a previous request completed.

## Verification

Six deterministic owner tests passed. They cover revocation before native write, provider loss after handoff, settlement after caller response loss, duplicate refusal, exact cancellation, a lost owner with active work, and a replaced socket. The live Qwen fixture submitted two completed prompts from independent manager processes without a gateway. The private descriptor retained one native PID, birth identity, session, and service incarnation. The fixture then stopped the verified owner on its private tmux server.

```bash
env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/agents/realm_controller/{test_service_owner,test_owner_admission,test_plugin_dispatch_control,test_dsh_headless_worker}.py
```

All 32 focused tests passed. Ruff and strict mypy passed for the owner, runtime client, and dispatch control modules.
