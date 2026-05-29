## Context

Issue 61 asks for durable local registration of a Houmao agent that is already running under a different Houmao installation or host. The local operator should be able to discover and message that agent through the remote `houmao-passive-server`, but the local `houmao-mgr` must not claim lifecycle ownership.

Current `houmao-mgr agents` code already has a useful pair-authority path: `ManagedAgentTarget(mode="server")` uses a `PairAuthorityClientProtocol` for state, prompt, interrupt, gateway, mail, and headless-turn routes. However, explicit `--port` targeting is still local-loopback-only, and the shared registry model is local lifecycle-oriented: `ManagedAgentRegistryRecordV3` requires manifest and terminal metadata and is validated as local runtime authority. Reusing that record shape for remote imports would require fake local paths and would blur lifecycle ownership.

The registry root is a discovery zone, not runtime storage. This change should add remote discovery metadata while preserving that boundary.

## Goals / Non-Goals

**Goals:**
- Let an operator register a reachable remote Houmao passive-server agent under a durable local name.
- Route communication-safe commands through the stored remote `api_base_url` and `remote_agent_ref`.
- Keep external records free of local manifest, session root, tmux, or relaunch authority requirements.
- Make lifecycle ownership explicit so local lifecycle commands fail clearly for external agents.
- Reuse the maintained passive-server pair API rather than defining a new remote protocol.
- Document secure exposure guidance and the behavioral difference between local lifecycle records and external communication-only records.

**Non-Goals:**
- Starting, stopping, relaunching, cleaning up, attaching, or detaching the remote agent from the importing host.
- Replacing remote passive-server authentication or transport security. The first implementation assumes the URL is reachable on a trusted channel such as SSH forwarding, VPN, Tailscale, or a secured reverse proxy.
- Supporting standalone `houmao-server` as a maintained remote authority.
- Mirroring remote runtime artifacts, mailbox storage, manifests, tmux state, or gateway process ownership into the local registry.

## Decisions

### Store external records in a separate registry collection

Use a new registry path:

```text
<registry-root>/
  live_agents/<agent-id>/record.json
  external_agents/<external-agent-id>/record.json
```

`live_agents/` remains the strict local lifecycle collection backed by `ManagedAgentRegistryRecordV3`. `external_agents/` stores communication-only locator records with a new schema, for example:

```yaml
schema_version: 1
kind: external_communication_only
local_name: remote-james
external_agent_id: external-...
generation_id: ...
pair_api_base_url: http://remote-host:9891
remote_agent_ref: james
gateway_expected: true
lifecycle_owner: remote
created_at_utc: ...
updated_at_utc: ...
verified_at_utc: ...
cached_identity:
  tracked_agent_id: james
  transport: headless
  tool: codex
```

Rationale: a separate collection avoids optionalizing local lifecycle invariants just to support a different ownership model. It also keeps cleanup behavior simple: local stale-tmux cleanup applies to `live_agents/`; external records are durable imports and are removed only by explicit external unregister/remove operations.

Alternative considered: add `kind = external` to `ManagedAgentRegistryRecordV3`. That would make every local runtime field conditional and would weaken a model whose purpose is to preserve local lifecycle state.

### Verify on register and cache remote identity

`houmao-mgr agents external register` should connect to the supplied `--api-base-url`, verify that `/health` reports the maintained passive-server authority, resolve `--agent-ref` via the remote managed-agent identity route, and cache that identity in the external record.

Rationale: existing list and renderer surfaces expect a transport-neutral identity with `tool` and `transport`. Verification also catches wrong URLs, unsupported authorities, and misspelled remote agent refs at import time.

Alternative considered: allow unverified imports. That is useful for pre-staging, but it would require synthetic identities and more ambiguous list/state behavior. It can be added later behind an explicit `--skip-verify` if needed.

### Add a distinct external target mode

Extend `ManagedAgentTarget` with enough metadata to distinguish external communication-only targets from ordinary pair-server fallback targets:

```text
mode = "external"
client = PairAuthorityClientProtocol for pair_api_base_url
agent_ref = remote_agent_ref
external_record = ExternalManagedAgentRegistryRecordV1
```

Existing pair-safe operations should branch on a helper such as `_target_uses_pair_api(target)` rather than checking only `mode == "server"`. External targets can reuse the same remote client methods for state, prompt, interrupt, gateway prompt/status, and pair-backed mail calls.

Rationale: `mode="server"` currently means an explicit or fallback pair authority, and some commands delegate lifecycle operations to that server. External targets need pair transport but different capability gates, so a distinct mode keeps the ownership boundary visible.

Alternative considered: use `mode="server"` with a flag on `record`. That would make it too easy for stop, relaunch, gateway attach, or raw control-input commands to accidentally delegate lifecycle/control operations to the remote owner.

### Resolve external records after local lifecycle records

Resolution should preserve the local-first behavior:

1. Explicit `--port` continues to bypass registry discovery and target local loopback by port.
2. Local lifecycle records in `live_agents/` are resolved first by `--agent-id` or `--agent-name`.
3. External records in `external_agents/` are resolved by local `external_agent_id` or `local_name`.
4. If no registry record matches, default pair fallback remains unchanged.

Registration must reject local-name or local-id collisions with existing local lifecycle records and existing external records unless the collision is an external record being deliberately replaced. A local lifecycle record must not be replaced by external registration.

Rationale: local records represent stronger lifecycle authority and should not be shadowed by imported aliases. Explicit `--port` remains the compatibility escape hatch.

### Gate commands by capability, not just transport

External targets support:

| Command family | Behavior |
| --- | --- |
| `agents list` | Include cached external records by default without polling the remote host |
| `agents state` | Query remote state through stored `pair_api_base_url` and `remote_agent_ref` |
| `agents prompt` | Submit remote managed-agent prompt request |
| `agents interrupt` | Submit remote interrupt request |
| `agents gateway status` | Query remote gateway status |
| `agents gateway prompt` | Submit remote gateway prompt control |
| `agents gateway interrupt` | Submit remote gateway interrupt when exposed by the remote pair API |
| `agents mail ...` | Use remote pair-backed mail routes when the remote authority supports them |

External targets reject:

| Command family | Reason |
| --- | --- |
| `agents stop`, `agents relaunch`, local cleanup | Lifecycle is owned by the remote Houmao authority |
| `agents gateway attach`, `agents gateway detach` | Gateway process ownership is remote |
| `agents gateway send-keys` | Raw control-input is outside the communication-only contract |
| current-session and target-tmux-session selectors | These are local tmux discovery surfaces |

Errors should mention the local name, remote base URL, remote ref, and the supported local operations.

### Keep list fast and state live

`agents list` should read external records and render cached identity/verification metadata without contacting every remote endpoint. `agents external verify` and `agents state` perform live remote calls and should report connection failures without deleting the record.

Rationale: operators may register multiple remote teams, and list should remain a local inventory command. Live health belongs in explicit verification or state commands.

### Add minimal identity annotations for clear output

The list/state renderer should be able to identify external communication-only rows. Prefer adding optional identity metadata such as `management_kind = "external_communication_only"` or `lifecycle_owner = "remote"` while leaving remote `transport` and `tool` as reported by the remote authority.

Rationale: overloading `transport` with `external` would lose the useful remote transport value (`tui` or `headless`) and ripple through existing transport assumptions.

## Risks / Trade-offs

- Remote URL exposure can be unsafe if a passive-server is bound publicly without authentication -> Document trusted-channel expectations and avoid storing credentials in this change.
- Cached identity may become stale if the remote agent is renamed or replaced -> Provide `agents external verify` to refresh cached identity and surface mismatch diagnostics.
- Local and external names can collide -> Fail registration and resolution closed; require explicit disambiguation or external replacement only for an existing external record.
- External list entries can appear even when the remote host is down -> Treat list as local inventory and reserve live checks for `state` and `external verify`.
- Pair-backed mail support depends on the remote authority and mailbox configuration -> Route when supported and preserve existing remote error payloads when unsupported.

## Migration Plan

1. Add the external registry model, schema, storage helpers, and path helper for `external_agents/`.
2. Add `houmao-mgr agents external` registration, verification, listing, inspection, and removal commands.
3. Extend target resolution to produce `mode="external"` for external records after local lifecycle lookup and before default pair fallback.
4. Update pair-safe command helpers and reject lifecycle/raw-control commands for external targets.
5. Update list/state renderers and documentation so external communication-only status is visible.
6. Add tests using temporary registry roots and fake or local passive-server clients.

Rollback is straightforward because this change adds a separate registry collection. Removing external records under `external_agents/` restores previous behavior without touching local lifecycle records.
