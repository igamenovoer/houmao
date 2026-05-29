## Why

Operators need to communicate with Houmao agents that are already running under a different Houmao installation or host. Today `houmao-mgr agents ... --port` only targets `127.0.0.1:<port>`, and the shared registry shape assumes local runtime authority, so remote gateway-enabled agents require ad hoc tunnels and cannot be kept as durable communication-only targets.

## What Changes

- Add first-class external communication-only managed-agent registration under `houmao-mgr agents external`.
- Store durable external-agent discovery metadata without requiring local manifest paths, tmux sessions, runtime roots, or lifecycle authority.
- Extend managed-agent target resolution so external records can be selected by local name/id and routed through their stored remote passive-server base URL and remote agent reference.
- Allow communication-safe commands against external agents: list, state, prompt, interrupt, gateway status, gateway prompt, and pair-backed mail operations where the remote authority supports them.
- Reject local lifecycle and raw local-control commands for external agents with explicit guidance that lifecycle is owned by the remote Houmao authority.
- Document secure exposure expectations for remote passive-server URLs and the distinction between local lifecycle-managed agents and external communication-only records.

## Capabilities

### New Capabilities
- `houmao-mgr-external-agents`: durable registration, verification, resolution, command routing, and lifecycle gating for communication-only external Houmao agents.

### Modified Capabilities
- `houmao-mgr-registry-discovery`: external communication-only records participate in registry-backed discovery without changing the local lifecycle record contract.
- `houmao-owned-dir-layout`: the shared registry root may contain external-agent discovery metadata while remaining discovery-only rather than runtime-owned storage.
- `docs-cli-reference`: CLI reference coverage must include the new `houmao-mgr agents external` command family and external-agent command support boundaries.
- `registry-reference-docs`: registry reference documentation must describe external communication-only records alongside local lifecycle records.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/agents/gateway.py`, `src/houmao/srv_ctrl/commands/agents/mail.py`, and shared target helpers in `src/houmao/srv_ctrl/commands/managed_agents.py`.
- Affected registry code: `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, packaged registry schemas, and registry cleanup/read helpers.
- Affected client behavior: reuse existing `PairAuthorityClientProtocol` and `require_supported_houmao_pair(base_url=...)` with persisted non-localhost base URLs.
- Affected renderers/docs/tests: agent list/state renderers, CLI docs, registry reference docs, unit tests for external record storage and routing, and integration-style tests with a temporary passive-server base URL or fake pair client.
