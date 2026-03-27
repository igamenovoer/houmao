# Runtime-Managed Agents Reference

This section explains the repo-owned runtime session model from two angles at once: how to use runtime-managed agents correctly, and how the runtime owns their state, targeting, and control surfaces.

If you are new to the subsystem, start with the operations page. If you need exact targeting or interface rules, jump to contracts. If you are debugging resume, persistence, or cleanup behavior, use the internals page.

## Mental Model

A runtime-managed agent session is the runtime's durable handle around one live backend session.

- The runtime starts or resumes a backend session and persists a session manifest.
- The same manifest-first envelope can also be created around an already-running tmux session through `houmao-mgr agents join`.
- The manifest and tmux-published pointers let later commands find the same logical session again.
- Operators can interact through more than one path: direct prompt turns, raw control input, mailbox-driven prompt turns, and optional gateway-routed queued requests.
- The optional gateway is a companion control plane for the same session, not a replacement for the runtime's core session model.

## Key Terms

- `runtime-managed session`: A session started or resumed through `houmao.agents.realm_controller`, with persisted runtime state and repo-owned control behavior.
- `session root`: The runtime-owned directory at `<runtime_root>/sessions/<backend>/<session-id>/`.
- `session manifest`: The schema-validated `manifest.json` written under the session root and used for resume or control.
- `direct control`: Runtime commands such as `send-prompt` or `send-keys` that act against the resumed backend session directly.
- `queued control`: Gateway-routed work that is accepted first and executed later through the sidecar queue.
- `runtime-owned state`: Artifacts the runtime persists and validates itself, such as session manifests, gateway attachability, and gateway status snapshots.

For the canonical filesystem map behind these terms, use [System Files Reference](../system-files/index.md) and [Agents And Runtime](../system-files/agents-and-runtime.md).

## Read By Goal

### Start here

- [Houmao Server Pair](../houmao_server_pair.md): supported operator workflow for `houmao-server + houmao-mgr`, including launch, join, gateway attach, and relaunch.
- [Session And Message Flows](operations/session-and-message-flows.md): Start, resume, stop, and choose between prompt turns, control input, mailbox, and gateway paths.
- [Troubleshooting Codex Approval Prompts (Legacy)](troubleshoot/codex-cao-approval-prompt-troubleshooting.md): Diagnose why a `cao_rest`-backed Codex prompt turn stops on an approval menu and verify the selected unattended launch-policy strategy.

### Contracts

- [Public Interfaces](contracts/public-interfaces.md): Session targeting, CLI surface intent, runtime-owned artifacts, and current implementation boundaries.

### Internals

- [State And Recovery](internals/state-and-recovery.md): Session roots, manifests, tmux-published pointers, cleanup behavior, and recovery boundaries.

## Related References

- [System Files Reference](../system-files/index.md): Canonical Houmao filesystem map for runtime homes, session roots, registry roots, and operator preparation.
- [Gateway Reference](../gateway/index.md): The optional sidecar control plane for gateway-capable sessions.
- [Mailbox Reference](../mailbox/index.md): Filesystem mailbox contracts and runtime-owned mailbox flows.
- [Realm Controller](../realm_controller.md): Broad overview plus backend-specific notes.
- [Realm Controller Send-Keys](../realm_controller_send_keys.md): Detailed raw control-input grammar and examples.

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/agent_identity.py`](../../../src/houmao/agents/realm_controller/agent_identity.py)
- [`src/houmao/agents/realm_controller/errors.py`](../../../src/houmao/agents/realm_controller/errors.py)
- [`tests/unit/agents/realm_controller/test_gateway_support.py`](../../../tests/unit/agents/realm_controller/test_gateway_support.py)
