## Context

`gateway-mail-wakeup-demo-pack` currently provisions a copied dummy project correctly, but its orchestration still assumes the older CAO-owned control plane. The helper starts or reuses CAO through the launcher, launches the session with `backend=cao_rest`, waits for idleness through CAO terminal status, and records CAO-shaped lifecycle evidence in the report.

That no longer matches the repository's preferred operating model. The documented pair flow is now `houmao-server` plus managed-agent routes, with post-launch gateway attach as the supported lifecycle boundary. The pack also predates the newer mailbox-demo reliability pattern that mirrors runtime mailbox skill documents into the copied project workdir so unattended Codex turns are not dependent on runtime-home hidden skill paths.

This change needs to update the pack without changing its teaching contract. It should remain a narrow, single-agent gateway wake-up walkthrough rooted in a copied dummy project, managed mailbox delivery, durable gateway audit evidence, and one demo-owned output artifact.

## Goals / Non-Goals

**Goals:**

- Move the pack from demo-owned CAO launcher management to demo-owned `houmao-server` lifecycle management.
- Launch the tracked session through the supported pair-backed runtime backend `houmao_server_rest`.
- Keep the pack single-agent and preserve the existing automatic/manual walkthrough shape.
- Make post-launch gateway attach, notifier control, inspection, and stop behavior align with server-backed managed-agent authority.
- Replace CAO-specific lifecycle evidence in the report and README with server-backed lifecycle and managed-agent evidence.
- Stage runtime mailbox skill documents into the copied dummy-project workdir before launch so the wake-up turn remains reliable under current mailbox-demo conventions.

**Non-Goals:**

- Rebuild this pack as a headless managed-agent demo like `mail-ping-pong-gateway-demo-pack`.
- Expand the pack into a multi-agent conversation workflow.
- Change the mail delivery boundary from the managed delivery script to direct database mutation or a different transport.
- Redesign the golden-report philosophy around exact poll-by-poll sequencing.

## Decisions

### Decision: Keep the pack single-agent and helper-driven instead of rewriting it as a new demo module

The teaching contract is still valid: one mailbox-enabled session, one wake-up message, one notifier audit trail, one output file. The problem is the control plane drift, not the scenario.

Keeping the existing pack shape minimizes churn in docs and operator workflow. The shell wrapper plus pack-local helper can still own the demo cleanly after the migration.

Alternatives considered:

- Rebuild the pack on the newer module-backed demo architecture.
  Rejected because that would add structural churn without changing the underlying walkthrough.
- Replace the pack with the newer ping-pong demo.
  Rejected because the ping-pong demo teaches a different contract and is intentionally broader.

### Decision: Use demo-owned `houmao-server`, but keep session launch on `realm_controller start-session`

The pack should start a demo-owned `houmao-server` under the selected output root and then launch the live mailbox-enabled session with `backend=houmao_server_rest` against that server.

This keeps the narrow runtime-owned launch path that the pack already uses for copied dummy projects, blueprints, and mailbox overrides, while moving the underlying control plane onto the supported pair model.

Alternatives considered:

- Keep the CAO launcher and `backend=cao_rest`.
  Rejected because that preserves the exact drift this change is meant to remove.
- Launch through a headless server route such as `POST /houmao/agents/headless/launches`.
  Rejected because the pack is not a headless demo and should keep demonstrating one live tmux-backed mailbox-enabled session.
- Launch through `houmao-mgr launch`.
  Rejected because the current helper already has the narrower runtime inputs it needs, while a CLI-shaped pair launch would add extra wrapper complexity without improving the scenario.

### Decision: Switch post-launch control to server-backed managed-agent routes

Once the `houmao_server_rest` session is live and registered, the pack should treat the server as the operational authority for:

- gateway attach,
- mail-notifier enable or disable,
- managed-agent stop,
- any readiness or identity lookups needed to target the same live session across manual follow-up commands.

The pack can still inspect gateway-owned durable artifacts directly for verification, but control operations should stop going through the CAO launcher model or pack-local CAO assumptions.

Alternatives considered:

- Keep direct runtime `attach-gateway`, direct gateway HTTP notifier control, and runtime `stop-session`.
  Rejected because the repo now documents the managed-agent routes as the supported surface, and this pack should validate that supported path.

### Decision: Replace CAO idle detection with server-first readiness checks plus gateway fallback

The automatic workflow still needs to wait until the session looks idle before mail injection. Under the migrated control plane, the pack should check server-backed session readiness first and use gateway status as the fallback when the richer server signal is temporarily unavailable.

This preserves the pack's current operator intent while removing its CAO-terminal dependency.

Alternatives considered:

- Keep CAO terminal polling.
  Rejected because it ties the pack to the retired CAO-owned lifecycle.
- Depend only on gateway status.
  Rejected because the gateway is attached later and its status alone is weaker during the early launch phase.

### Decision: Stage mailbox skill documents into the copied project workdir

Newer mailbox demos already mirror runtime mailbox skills into the provisioned project under `skills/mailbox/...` plus the hidden compatibility mirror. This pack should adopt the same pattern when it provisions `<demo-output-dir>/project`.

That makes the wake-up turn less sensitive to runtime-home hidden skill paths and matches the current repo guidance for Codex-friendly mailbox skill discovery.

Alternatives considered:

- Keep relying only on the built runtime home's hidden mailbox skill paths.
  Rejected because newer demos have already proven that project-local mailbox skill staging is the safer default for unattended turns.

### Decision: Keep the outcome-summary golden report style, but replace CAO artifacts with server artifacts

The pack should continue sanitizing raw notifier rows into stable outcome-summary assertions and keep exact poll ordering out of the golden comparison. That philosophy is still correct.

What changes is the lifecycle evidence around it: the report should record server startup metadata, pair-backed session launch metadata, managed-agent targeting evidence, and server-backed control results instead of CAO launcher and CAO terminal artifacts.

Alternatives considered:

- Preserve the old report shape and simply relabel fields.
  Rejected because that would keep CAO-specific concepts in a pack that no longer uses CAO as its control plane.
- Tighten the report to exact gateway poll ordering.
  Rejected because that would make the pack more brittle for no real user value.

## Risks / Trade-offs

- [Server-backed attach depends on managed-agent registration becoming visible after runtime launch] → Persist enough launch identity in demo state to resolve the same managed agent deterministically, and fail clearly when registration does not become available in time.
- [Switching control surfaces can break the current golden report and tests all at once] → Update the report schema, expected snapshot, and unit doubles together as one migration rather than trying to preserve CAO-shaped fields.
- [Project-local mailbox skill staging adds another provisioning step that can drift from other demos] → Reuse the same helper pattern already established in newer mailbox demos instead of inventing a pack-specific variant.
- [Old demo roots or stale state files may not be reusable after the migration] → Treat this as a clean break in pack-owned lifecycle artifacts and fail clearly when stale directories or incompatible state are detected.

## Migration Plan

1. Replace demo-owned CAO launcher setup with demo-owned `houmao-server` startup and shutdown under the pack output root.
2. Update tracked parameters, helper parsing, and start flow so the session launches with `backend=houmao_server_rest`.
3. Add project-local mailbox skill staging during copied dummy-project provisioning.
4. Switch attach, notifier, idle-wait, inspect, and stop logic to the server-backed managed-agent control model, while keeping gateway-owned durable artifact inspection for verification.
5. Revise the report schema, sanitized snapshot, and README to teach the new server-backed lifecycle.
6. Update unit coverage so it detects drift back to CAO-owned defaults or missing project-local mailbox skill staging.

Rollback strategy:

- revert the pack helper, tracked inputs, README, and tests together to the pre-migration CAO-backed variant if the server-backed pack proves unreliable;
- do not attempt to preserve mixed CAO/server compatibility in one pack, because that would create an unclear teaching contract.

## Open Questions

- Which exact server-backed state route should be the primary idle/readiness signal for this pack: managed-agent summary state, managed-agent detail state, or terminal state projected through the pair-backed session identity?
- Should the migrated pack keep its current helper-only structure, or is this a good moment to move it onto the newer shared demo module pattern if the implementation starts duplicating server lifecycle code heavily?
