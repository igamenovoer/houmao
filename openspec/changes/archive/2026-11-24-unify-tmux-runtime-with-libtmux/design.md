# Design

## Context

See [the proposal](proposal.md) for motivation and [the spec delta](specs/tmux-integration-runtime/spec.md) for the behavior contract.

`houmao.execution.tmux` already binds a socket for the duration of an operation. `backends/tmux_runtime.py` supplies a second layer that mixes command execution, pane selection, launch policy, and provider environment publication. The compatibility controller and recorder execute some of the same terminal operations separately. Managed controllers can also restore window and pane IDs independently from three manifest sections. Health and control currently disagree on whether a launched pane must have index zero.

## Goals / Non-Goals

**Goals**

- Bind lookup, observation, action, and cleanup to one explicit owner socket during an operation.
- Use one pane record and one primary-selection policy for managed capture, health, input, and lifecycle actions.
- Let generic terminal callers use the same execution layer with their own surface and output contracts.

**Non-Goals**

- Record-first manager discovery and recovery policy in `prefer-record-backed-agent-operations`.
- A redesign of provider state, gateway routing, mail delivery, or fixture socket authorization.
- Migration of archival snapshots and invocations whose purpose is to test native tmux interoperability.

## Decisions

### Share Scoped Terminal Operations

Put the libtmux adapter in `houmao.execution` alongside the existing tmux scope. Keep the bound socket, executable selection, live object hydration, result checks, and native exceptions there. An operation scoped to a saved owner socket always selects it explicitly. Fresh launch, join, and operator tools capture their selector at entry. Honor the executable on the caller's `PATH`, including fixture shims. Keep nested and concurrent scopes independent of process-global `TMUX` and `TMUX_PANE`.

Use ordinary, short-lived libtmux `Server`, `Session`, `Window`, and `Pane` objects in the adapter. Some libtmux context managers destroy the referenced objects on exit. Houmao's scope controls routing, and explicit owner lifecycle operations control destruction. Return one immutable pane record containing the session identity, window and pane IDs and indexes, and observed liveness and metadata. Use one checked session-wide observation when an operation needs pane selection. Validate membership in the exact session on the bound socket before accepting a server-local ID. Capture a new view after a topology change or when committing a repair requires it.

Keep window-zero selection, role naming, join policy, and launch environment reconciliation in the realm controller. The adapter executes terminal primitives such as capture, option changes, and environment writes and works for the recorder and compatibility controller as well. Per-backend libtmux objects would scatter targeting and error handling across providers. A global object cache would also require invalidation across tmux server and pane replacement.

### Check the Result Before Interpreting It

Verify behavior against the locked libtmux release and the `extern/orphan/libtmux` source reference. Use the typed methods when they preserve the required result. Use socket-bound or object-bound command dispatch when a typed method drops status or lacks a required field or flag. Examples include exact session enumeration, checked environment publication, scoped client queries, and the exact window and pane receipt for a gateway window. Account for defaults such as implicit Enter in `Pane.send_keys()` and preserve the distinction between masking inherited environment values and removing session overrides.

Expose confirmed absence separately from unavailable or invalid observations and failed mutations. Preserve the exit status and safe diagnostic context even when tmux prints nothing. The pinned release can turn a failed `has_session` into `False`, suppress a failed environment setter, and change process-global `TMUX` in `Server.new_session()`. These methods cannot establish the checked results or child environment this runtime needs. A command failure provides no basis to switch targets or replay a mutation. A live observation can identify a dead or ambiguous surface without treating it as a socket failure.

Keep native process execution behind named operations. The initial exceptions are sanitized server or session startup, prompt-buffer input over stdin, deadline-bounded waits, exact stdout when the caller requires bytes or whitespace that libtmux discards, and inherited-stdio or PTY handoff for a delegated child process. Keep the standard interactive manager attach on its existing libtmux-backed path. A recorder can use the adapter to resolve its terminal and build the native attach invocation passed to its PTY driver. Document the required process feature and cover its observable contract for each retained exception. A generic subprocess runner available to all callers would let status handling and socket selection diverge again.

### Persist One Managed Terminal Binding

Use `SessionManifestTmuxSectionV1` as the durable source of the owner socket, session name, primary role and window name, and window and pane IDs. Restore those coordinates together. Hold one corresponding binding in the managed runtime and project it into the existing manifest and registry shapes. Preserve provider-native conversation state, joined relaunch intent, and gateway auxiliary identity in their existing models. A gateway window created with an exact handle receipt continues to be owned by its gateway instance record.

Use a shared primary selector for health and control. A valid saved pane in window zero wins even when focus moves. An owned launch under one-based pane defaults can have a valid nonzero primary pane index. Preserve the stricter adopted-pane identity required by the join contract, including the saved window name and pane-zero rule where applicable. Remove per-field fallback across manifest sections. Choose explicit owner-side join or lifecycle setup for records with missing socket authority before attempting live operations.

### Make Repair an Explicit Owner Action

Resolve observations from the saved binding and the checked live view. Return a valid handle, a confirmed degraded state with any unique replacement candidate, or an observation failure. Read-only callers can report the live evidence without changing the controller's binding or publishing anything. Terminal mutations that need the primary pane use the checked handle. An owner-authorized control or lifecycle operation can request repair after confirmed absence or staleness and a unique actionable match under the same primary-surface rules.

Before repair, recheck the exact live membership. Under the manifest lock, compare the current owner, execution generation, and entire prior binding against the repair request. Merge the window and pane together into the current manifest and derive its projections there. Update the controller from the committed result and publish any affected registry coordinates from the current binding through the existing generation fence. A conflict requires fresh resolution. This avoids writing a stale controller snapshot over concurrent provider, mailbox, or gateway changes. A read that persists a replacement would make inspection depend on write authority and can overwrite a newer handle within the same generation.

## Risks / Trade-offs

- **The live pane can change after verification.** Target the checked exact ID on the bound socket and report any action failure. Avoid automatic fallback after a partial prompt or lifecycle mutation.
- **Moving to typed methods can change terminal behavior.** Exercise literal text, named keys, explicit Enter, bracketed paste, buffer cleanup, normalized versus exact capture output, and session environment masking in focused tests.
- **Diagnostics can expose command inputs or captured text.** Keep prompt text out of argv and filesystem staging. Protect published values and terminal capture content from libtmux debug output and sanitized failure messages. Test a failed mutation with secret-shaped input.
- **A shim can refuse a socket without stderr.** Check exit status and preserve failure evidence for the later discovery change. Keep the fixture's owned-socket boundary in effect.

## Migration Plan

Start with TUI prompt submission, including readiness, pane resolution, buffer paste, and Enter. Exercise the path on two isolated sockets and with the gateway detached. Move manifest readers and writers to the same binding during this slice so the new adapter serves the runtime entry point. Then move Headless, Service, Web, gateway lifecycle, compatibility, recorder, and maintained fixture and tooling callers. Remove duplicate execution and target-resolution paths after their callers migrate.

Keep the current manifest and registry envelopes through this refactor. Existing records that carry the canonical tmux binding can resume with it, and owner-authorized operations can repair missing or stale handles on a known socket. Existing rollout and code rollback can use the same serialized shapes. Apply `prefer-record-backed-agent-operations` after this refactor so its manager policy can consume the shared operations and their failure distinctions.
