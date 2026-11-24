# Design

## Context

The [proposal](proposal.md) describes the failure in issue #95. In the manager, `resolve_managed_agent_target()` couples registry lookup to a terminal health probe and controller resume. The [libtmux refactor](../2026-11-24-unify-tmux-runtime-with-libtmux/design.md) now provides a canonical terminal binding, checked observations, and explicit binding repair. Keep those boundaries when choosing whether a manager operation needs terminal access.

## Goals / Non-Goals

**Goals**

- Choose the source of each answer after selecting the agent and its owner.
- Bound terminal observations and mutations to the selected runtime generation, socket, and surface.
- Keep storage, gateway attachment, and live prompt readiness independently observable.

**Non-Goals**

- New CLI command families, communication transports, or discovery services.
- A redesign of self authentication, gateway access policy, or passive-server indexing.

## Decisions

### Select the Agent Before Acquiring Runtime Authority

Keep the existing selector precedence for managed records, execution locators, explicit server selection, and communication-only imports. For a local registry match, selection yields the record, its identity, and the saved owner binding without opening the manifest or a controller. Mail discovery, saved turn reads, and state can also select inactive records. Expose the existing gateway terminal alias at the `agents single` group level for gateway commands. Resolve it against fresh local registry matches. Self keeps its independent caller verification.

Reuse `load_registry_mode_authority()` where a verified manifest supplies data. Check identity, generation, execution owner, mode, and native surface. Carry the verified payload through the read. A missing, inaccessible, or foreign-owner manifest can leave public contact available. A readable manifest that conflicts with the selected record fails the authoritative operation. Preserve self verification and existing gateway signer selection. [Manifest validation](../../../../src/houmao/agents/realm_controller/manifest.py) · [Self verification](../../../../src/houmao/agents/realm_controller/self_manifest.py)

A universal read-only controller still leaves record queries subject to the common terminal probe. Widening the fixture shim would also leave that dependency in place for other restricted command environments.

### Read Values From the Authority That Owns Them

| Operation | Evidence |
| --- | --- |
| Identity and contact | Stable agent ID, unique name, lifecycle, and redacted mailbox projection from the selected shared registry. |
| `mail resolve-live` | Verified owner manifest and existing mailbox binding checks. Use the current-instance record and existing endpoint verification when a live gateway is published. |
| `gateway status` | Authorized persisted gateway status and current-instance records. Confirm the active endpoint and generation for live status. |
| Saved headless turn reads | Verified owner manifest, confined artifact path, native provider identity, and persisted turn evidence. |
| Managed `state` and detailed inspection | Recorded identity and contact plus current mode-specific observation when available. |

Use the existing output envelopes. Scoped `mail resolve-live` can resolve a known stopped recipient with published contact. A visible contact record that agrees with an executor locator can also answer without requiring its delegated route. For published contact, return the redacted slots with source `registry_projection`, unverified availability, and no live gateway. For attached gateway reads, match the persisted current-instance descriptor and live endpoint to the verified agent ID, owner context, and runtime generation. Gateway status also checks the returned instance epoch and ID. An unreachable or superseded attached gateway yields an unavailable diagnostic. Retained turn reads confine both the turn directory and the files read beneath it to the verified runtime.

Ordinary outbound mail uses the sender's verified binding and the explicit channel. The mail authority verifies recipient registration during delivery. An attached or detached recipient gateway affects only live gateway operations. The messaging skill can find the address without a preliminary state query. Access refusals on private gateway and mail operations remain explicit.

### Let the Mode Determine Live Observation and Dispatch

Build manager state from the recorded identity and the best qualified observation for the selected mode. Use read-only reconstruction for native Web and service observation, saved execution artifacts for headless, and verified tracker state for TUI. Use the canonical checked primary observation when TUI needs a fresh read. Include source, freshness, and unavailability diagnostics in the managed state models. Report lease freshness as publication metadata. A completed headless turn and current admission availability have independent evidence.

For authorized direct prompts with a detached gateway, reopen existing owner control without republishing it. Retain the owner reservation, readiness checks, generation checks, and backend dispatch. TUI delivery validates and uses the recipient's exact socket and primary pane. Inspecting an unmanaged pane for join or verifying the caller's actual self session can still require tmux. [Owner prompt dispatch](../../../../src/houmao/srv_ctrl/commands/managed_agents.py) · [Execution socket scope](../../../../src/houmao/execution/tmux.py)

### Require Conclusive Evidence for Terminal Recovery

Make terminal checks distinguish presence, confirmed absence or surface degradation, and unavailable inspection. Preserve the underlying failure classification across subprocess and libtmux boundaries. Permission failures, timeouts, or a wrapper refusal carry an unavailable result. A failed pane query following a successful session check needs conclusive evidence before recovery.

Bind session cleanup and stale stop or relaunch to the target record's owner socket. Reuse the checked primary observation. Automatic recovery requires confirmed missing session or the recoverable missing-primary classification. Other primary failures retain their own diagnostic. Recheck generation and owner before mutation. Fresh active entries in registry cleanup require confirmed absence on the recorded socket for liveness-based removal. Lease expiry and explicitly stopped records retain their existing evidence rules. Report unavailable checks in cleanup output and preserve active records and artifacts after inconclusive inspection. [Session cleanup](../../../../src/houmao/srv_ctrl/commands/runtime_cleanup.py) · [Registry cleanup](../../../../src/houmao/agents/realm_controller/registry_storage.py)

## Risks / Trade-offs

- **Published data can lag runtime changes.** Report its source, check current manifest and gateway identities for live results, and validate actual mail registration at delivery.
- **Deferring controller acquisition exposes implicit dependencies.** Exercise normal CLI handlers with terminal access denied. Verify that a read neither resumes a writable controller nor refreshes registry publication.
- **A lost terminal check can look like a missing session.** Assert both outcomes separately and verify that only conclusive evidence enables lifecycle recovery.

## Migration Plan

Read the existing registry and manifest formats in place. Update CLI references and packaged skills to explain published contact, gateway availability, and owner-side direct prompts. Qualify the change with the fixture's existing peer restrictions and a separate test of authorized direct delivery.
