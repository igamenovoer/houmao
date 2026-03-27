## Context

`houmao-mgr agents gateway` already exposes the live-gateway operator path for attach, detach, status, queued prompt submission, and queued interrupt submission. The underlying live gateway sidecar exposes two additional operator-facing controls that are not first-class in the CLI today:

- raw control input through `POST /v1/control/send-keys`
- mail-notifier configuration through `GET|PUT|DELETE /v1/mail-notifier`

The current CLI targeting model is also inconsistent across gateway operations. `agents gateway attach` already supports a current-session mode that resolves the target from tmux-published manifest-first metadata, but the other gateway commands require explicit selectors. For operators already inside the owning tmux session, that forces redundant target input even though Houmao already publishes `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, and `AGENTSYS_AGENT_DEF_DIR` for the same manifest-backed authority chain.

The pair surface is also asymmetric:

- `houmao-server` already exposes gateway mail-notifier routes.
- `houmao-server` does not yet expose a managed-agent route for raw gateway `send-keys`.
- `houmao-passive-server` proxies gateway status, queued requests, and mail routes, but not raw control input or mail-notifier routes.

## Goals / Non-Goals

**Goals:**

- Expose gateway raw control input as `houmao-mgr agents gateway send-keys`.
- Expose gateway mail-notifier control as `houmao-mgr agents gateway mail-notifier status|enable|disable`.
- Make these commands callable both outside tmux with explicit selectors and inside tmux through manifest-first current-session inference.
- Keep the live gateway sidecar as the source of truth for send-keys execution and notifier state.
- Keep pair behavior consistent across `houmao-server` and `houmao-passive-server`.

**Non-Goals:**

- Adding new queue request kinds for raw control input.
- Replacing the transport-neutral `houmao-mgr agents prompt` path with gateway send-keys.
- Adding CLI coverage for every gateway HTTP route in this change, such as TUI history or note-prompt.
- Treating live gateway host/port env vars as the authoritative target-resolution contract.

## Decisions

### Decision: Introduce one shared current-session target-resolution path for gateway commands

Gateway commands that operate on one managed agent should share a single resolution model:

1. if `--agent-id` or `--agent-name` is provided, resolve explicitly
2. else if `--current-session` is provided, require tmux and resolve from the current tmux session
3. else if no selector is provided and the command is running inside tmux, attempt current-session resolution implicitly
4. else fail and require an explicit selector

Current-session resolution should reuse the existing attach contract:

- derive the current tmux session name from `tmux display-message -p '#S'`
- prefer `AGENTSYS_MANIFEST_PATH`
- fall back to `AGENTSYS_AGENT_ID` plus shared-registry `runtime.manifest_path`
- require the resolved manifest to belong to the current tmux session
- for local authority, recover `agent_def_dir` from `AGENTSYS_AGENT_DEF_DIR` or registry metadata

Rationale:

- this keeps inside-tmux usage ergonomic without redefining managed-agent identity
- it reuses the manifest-first authority contract already used by gateway attach and relaunch
- it fails closed when metadata is stale instead of guessing from cwd, gateway env, or unrelated pair settings

Alternatives considered:

- Require explicit selectors everywhere. Rejected because it ignores manifest-backed discovery that the runtime already publishes specifically for same-session operations.
- Use live gateway host/port env vars as the primary selector. Rejected because they are ephemeral live bindings, not durable authority, and can be stale even when manifest authority is still valid.

### Decision: Keep the new operator surfaces under `agents gateway`

The new CLI commands should be:

- `houmao-mgr agents gateway send-keys`
- `houmao-mgr agents gateway mail-notifier status`
- `houmao-mgr agents gateway mail-notifier enable`
- `houmao-mgr agents gateway mail-notifier disable`

`send-keys` stays directly under `gateway` because it is one concrete live-gateway control action. Mail notifier uses a subgroup because it has a small lifecycle of read, enable, and disable operations.

Rationale:

- both features are live-gateway operations rather than transport-neutral managed-agent operations
- this keeps the CLI aligned with the gateway HTTP surface and existing `agents gateway` command family
- it avoids overloading `agents mail`, which is for foreground mailbox actions rather than background notifier control

Alternatives considered:

- Put notifier under `agents mail`. Rejected because notifier state belongs to the live gateway loop and is already modeled separately from mailbox follow-up operations.
- Add send-keys as `agents prompt --raw`. Rejected because raw control input is intentionally a different authority and must not blur into semantic prompt submission.

### Decision: Preserve raw send-keys as a dedicated non-queued control path

`send-keys` should continue to target the dedicated control-input route and payload shape:

- `POST /v1/control/send-keys`
- `GatewayControlInputRequestV1(sequence, escape_special_keys)`

The CLI should require `--sequence` explicitly and offer `--escape-special-keys` as a boolean switch that maps directly to the gateway model.

Rationale:

- the gateway already distinguishes semantic prompt submission from raw terminal mutation
- queueing send-keys as a normal request would incorrectly give raw control input prompt-like lifecycle semantics
- the runtime tmux-control-input contract already defines exact `<[key-name]>` parsing and literal-escape behavior

Alternatives considered:

- Introduce a new queued request kind for control input. Rejected because it changes gateway execution semantics and blurs the current separation between semantic and raw control surfaces.

### Decision: Extend pair APIs instead of requiring direct gateway listener access

For pair-managed operation:

- `houmao-server` should add `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- `houmao-server` should keep using its existing `GET|PUT|DELETE /houmao/agents/{agent_ref}/gateway/mail-notifier`
- `houmao-passive-server` should proxy both the new send-keys route and the existing notifier routes

CLI code should continue to talk to pair servers through pair clients rather than bypassing them to target the live gateway listener directly.

Rationale:

- this preserves the managed-agent API boundary
- it keeps operator workflows consistent between local, server, and passive-server modes
- it avoids forcing callers to know gateway host/port coordinates

Alternatives considered:

- Support notifier through `houmao-server` but leave passive-server unsupported. Rejected because the CLI already treats passive server as a supported pair authority for managed-agent operations, and inconsistent gateway subcommands would be surprising.
- Have the CLI discover host/port and call the live gateway directly in pair mode. Rejected because it bypasses the pair-owned managed-agent API surface.

### Decision: Require a live attached gateway for both new command families

Neither new command should fabricate a local fallback when no live gateway exists.

- `send-keys` should fail explicitly and direct the operator to attach the gateway
- mail-notifier commands should fail explicitly when no live gateway exists or when notifier support is unavailable for that session

Rationale:

- both features are explicitly gateway-owned controls
- silent fallback to local runtime prompt or mailbox paths would change behavior and state authority

Alternatives considered:

- Make `send-keys` fall back to direct runtime tmux injection. Rejected because the user is asking for gateway control, and the gateway route produces different audit and availability behavior.

## Risks / Trade-offs

- [Implicit current-session inference inside tmux may target the wrong session] → Require manifest-first resolution and verify that the resolved manifest belongs to the current tmux session before acting.
- [Pair API expansion adds more route and client parity work] → Keep the design narrow: one new send-keys route on the pair APIs, and reuse existing notifier models and client types.
- [Operators may confuse semantic prompt submission and raw control input] → Keep separate command names and help text, and preserve explicit `--sequence` semantics for `send-keys`.
- [Passive-server support increases test matrix size] → Reuse the existing passive proxy pattern and add route-contract tests for the new endpoints rather than inventing a separate passive behavior model.

## Migration Plan

This is an additive CLI and API expansion with no persisted data migration.

Rollout sequence:

1. add pair-server and passive-server proxy routes
2. add CLI commands and shared current-session resolution
3. update docs and help text to describe inside-tmux implicit targeting and outside-tmux explicit targeting
4. add regression coverage for local, pair, and passive resolution and failure cases

Rollback is straightforward: remove the new commands and proxy routes. Existing gateway attach, status, prompt, interrupt, and mail flows remain unchanged.

## Open Questions

None.
