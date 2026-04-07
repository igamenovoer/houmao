## Context

`houmao-mgr project easy instance launch` is the maintained opinionated path for launching a reusable project-local specialist, but today it stops at "managed agent is running" and leaves gateway attachment as a separate operator step. That is mechanically valid, but it is the wrong default for the common Houmao workflow because mailbox operations, explicit prompt routing, notifier-driven wakeups, and gateway-backed inspection all become available only after a second command.

The lower layers already implement the core runtime behavior this change needs. `start_runtime_session(...)` supports launch-time gateway auto-attach, partial-success behavior when auto-attach fails after session startup, and system-assigned listener ports when the requested port is `0` or otherwise omitted. The missing piece is the easy CLI contract: the easy surface does not currently request auto-attach, does not expose an opt-out, and does not make "automatic port by default" an explicit easy-launch policy.

This change is intentionally about the easy launch surface, not about redefining the runtime gateway model. The runtime should remain the authority for how attach happens, while the easy CLI becomes opinionated about when attach is requested and what defaults are passed into that runtime behavior.

## Goals / Non-Goals

**Goals:**
- Make gateway attachment the default behavior of `houmao-mgr project easy instance launch`.
- Make the default easy-launch gateway listener loopback-bound and system-assigned-port based.
- Allow operators to opt out with `--no-gateway`.
- Allow operators to request a fixed port for a specific easy launch with `--gateway-port`.
- Surface the resolved gateway endpoint, or a degraded-success gateway attach error, directly in easy launch results.
- Preserve the existing behavior that a session remains running when gateway auto-attach fails after launch.

**Non-Goals:**
- Persisting gateway auto-attach as part of specialist metadata or stored launch config.
- Adding a new durable gateway section to easy specialist records.
- Changing the runtime's general gateway precedence model for non-easy launch surfaces.
- Changing pair-managed headless launch APIs or allowing gateway fields in `houmao-server` headless launch requests.
- Expanding this change to expose `--gateway-host` on the easy surface.

## Decisions

### Decision: Keep gateway auto-attach as an easy-launch policy, not a specialist property

The stored specialist remains a reusable definition of prompt, tool, setup, auth, and durable launch posture. Gateway auto-attach belongs to the act of materializing a live instance, not to the durable specialist record.

That separation avoids turning a specialist into a singleton-shaped runtime template. A persisted gateway port is especially problematic because two instances launched from the same specialist would immediately contend for the same listener unless the operator remembered to override it every time.

Alternative considered:
- Persist `gateway.auto_attach` or a fixed gateway listener under specialist metadata or preset `extra`.
  Rejected because it mixes reusable template state with per-instance runtime control, and fixed listener defaults are a poor fit for repeated launches from one specialist.

### Decision: The easy surface will force its own default gateway listener request

When `project easy instance launch` auto-attaches a gateway and the operator did not opt out, the command should pass explicit launch-time gateway defaults of:

- `gateway_host = 127.0.0.1`
- `gateway_port = 0`

Passing explicit values is important. It makes "loopback + automatic port" a real easy-surface policy rather than an incidental runtime fallback that can be changed by unrelated caller env vars or dormant preset gateway defaults.

When the operator supplies `--gateway-port <port>`, the easy surface should replace the default `0` with that explicit port while still keeping loopback host unless a later change deliberately broadens that contract.

Alternative considered:
- Rely on the runtime's normal host/port precedence by passing `gateway_auto_attach=True` and no explicit listener overrides.
  Rejected because that would allow easy-launch defaults to vary based on caller environment or low-level preset internals, which is the opposite of the intended opinionated easy path.

### Decision: `--no-gateway` is the only easy-surface opt-out in this change

The command should behave as follows:

- no gateway flags: attach gateway by default
- `--no-gateway`: skip launch-time gateway attach entirely
- `--gateway-port <port>`: attach gateway on that requested port

`--no-gateway` and `--gateway-port` should be mutually exclusive. A launch cannot both skip gateway attachment and request a gateway port.

Alternative considered:
- Keep gateway attachment implicit and add a positive `--gateway` or `--attach-gateway` flag.
  Rejected because the request is specifically to make gateway the default path.

### Decision: Easy launch reuses runtime partial-success semantics

If the managed session starts but gateway auto-attach fails, the easy launch should not tear the session down. It should:

- emit the normal launch completion payload,
- include the gateway attach error alongside the manifest/session identity needed for retry,
- and exit with a degraded-success status consistent with the lower-level runtime start surface.

This keeps the easy surface aligned with the runtime contract and avoids inventing a second interpretation of "launch succeeded but gateway did not."

Alternative considered:
- Convert gateway auto-attach failure into a hard easy-launch failure that hides the running session.
  Rejected because it would make recovery worse and contradict the runtime's existing partial-success model.

### Decision: Implementation stays in the easy CLI and delegated local launch seam

The required code changes should remain narrow:

- `project easy instance launch` accepts `--no-gateway` and `--gateway-port`
- the command passes gateway launch intent into `launch_managed_agent_locally(...)`
- the local launch helper forwards that intent into `start_runtime_session(...)`
- launch completion rendering adds resolved gateway fields and gateway auto-attach errors when present

This keeps the runtime semantics centralized where they already exist and avoids pushing easy-specific policy down into lower-level gateway code.

Alternative considered:
- Add a post-launch `agents gateway attach` call inside the easy command instead of using launch-time auto-attach.
  Rejected because it duplicates runtime-owned attach orchestration and loses the existing launch-time partial-success contract.

## Risks / Trade-offs

- [Easy launch becomes more opinionated] → Mitigation: keep `--no-gateway` as an explicit escape hatch.
- [Scripts that assumed no gateway sidecar after easy launch will observe new gateway artifacts and status fields] → Mitigation: document the new default and preserve opt-out behavior.
- [Automatic gateway attach can still fail because of local bind or startup issues] → Mitigation: preserve the running session, expose the exact error, and keep manual retry available through managed-agent gateway commands.
- [Fixed-port requests can create collisions across repeated launches] → Mitigation: keep system-assigned port as the default and reserve fixed ports for explicit operator intent only.
- [Not exposing `--gateway-host` on easy launch limits advanced network topologies] → Mitigation: treat this as an intentional v1 constraint; advanced host binding remains available through lower-level runtime/gateway surfaces.

## Migration Plan

No stored data migration is required. Existing specialists remain valid because this change affects launch-time defaults, not specialist schema.

Rollout consists of:

1. Update easy launch CLI parsing and delegated launch plumbing.
2. Update easy launch output so resolved gateway state and degraded-success errors are visible.
3. Update CLI and easy-specialist docs to describe the new default and `--no-gateway` escape hatch.
4. Add regression coverage for default attach, explicit port override, opt-out, and degraded-success behavior.

Rollback is straightforward: remove the easy-surface auto-attach default and the new flags while leaving runtime gateway support untouched.

## Open Questions

None for this change. The host-binding question is intentionally deferred; the easy surface stays loopback-only in this proposal.
