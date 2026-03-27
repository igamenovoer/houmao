## Context

`houmao-mgr` currently offers two different mailbox seams:

- shared mailbox storage lifecycle under the filesystem mailbox libraries in `src/houmao/mailbox/`
- runtime-owned mailbox usage on already mailbox-enabled sessions through `houmao-mgr agents mail ...`

What is missing is the operator seam between them. Today a session must already carry `launch_plan.mailbox` before runtime-owned mail commands will work, and that binding is normally established during startup. That is awkward for local serverless workflows because mailbox root setup is an operational concern, not a launch-policy concern.

The codebase already has three reusable building blocks:

- filesystem mailbox bootstrap and lifecycle helpers such as `bootstrap_filesystem_mailbox()`, `register_mailbox()`, `deregister_mailbox()`, and `repair_mailbox_index()`
- persisted manifest mutation and live launch-plan refresh through `RuntimeSessionController.persist_manifest()` and `refresh_mailbox_bindings()`
- local managed-agent resolution through registry-first discovery in `houmao-mgr`

Mailbox skill documents are already projected into built homes regardless of whether a live mailbox binding exists, so late registration does not require a second skill-projection system.

## Goals / Non-Goals

**Goals:**
- Let operators create and manage a filesystem mailbox root with `houmao-mgr` and no `houmao-server`.
- Let operators register or unregister mailbox support on an already launched or joined local managed agent.
- Persist late mailbox registration into the session manifest and shared-registry mailbox summary so later local `agents mail ...` commands reuse it.
- Define explicit activation outcomes for late registration across local headless, local interactive, and joined-session runtime postures.
- Use `register/unregister` terminology that matches filesystem mailbox lifecycle semantics instead of introducing parallel `connect/disconnect` vocabulary.

**Non-Goals:**
- Adding a late mailbox registration API to `houmao-server` or passive-server in this change.
- Introducing a new sessionless `houmao-mgr mailbox send|check|reply` workflow.
- Generalizing the v1 CLI to non-filesystem mailbox transports such as Stalwart.
- Removing existing low-level runtime mailbox flags from legacy runtime-local CLIs in the same change.
- Making already-running joined or interactive TUI processes pick up new mailbox env vars without relaunch.

## Decisions

### Decision: Split root administration from per-session registration

The change adds two distinct CLI families:

- `houmao-mgr mailbox ...` for local filesystem mailbox root administration
- `houmao-mgr agents mailbox ...` for per-session late mailbox registration

This matches the existing architecture. Root operations act on shared mailbox state; agent operations act on one runtime session plus its manifest and registry record.

Alternative considered:
- Put everything under `houmao-mgr agents mailbox ...`
  Rejected because root initialization, inspection, and repair are mailbox-admin tasks that do not require an agent target.

### Decision: Use `register/unregister`, not `connect/disconnect`

`agents mailbox register` will mean:

1. resolve or bootstrap the filesystem mailbox root,
2. ensure the target address has an active shared mailbox registration using safe registration semantics by default,
3. attach the resolved mailbox binding to the live managed session,
4. persist the binding into the session manifest and registry-visible mailbox summary.

`agents mailbox unregister` will mean:

1. remove the live session mailbox binding,
2. deregister the underlying shared mailbox registration using defined lifecycle semantics, defaulting to `deactivate`,
3. persist the unbound session state into the manifest and registry.

This naming matches operator expectation and the filesystem mailbox lifecycle spec.

Alternative considered:
- `connect/disconnect` for session-only binding, leaving shared registration untouched
  Rejected because it creates two parallel operator concepts for the same address lifecycle and makes `unregister`-style mailbox cleanup harder to discover.

### Decision: Introduce an explicit late-registration activation state model

Late mailbox mutation is not equally immediate for every runtime posture.

- Local headless sessions become `active` immediately because each controlled turn rebuilds subprocess env from the launch plan.
- Long-lived local interactive sessions become `pending_relaunch` after register or unregister because the already-running provider process will not reliably adopt or drop mailbox env mid-flight.
- Joined sessions whose relaunch posture is unavailable are rejected up front as `unsupported_joined_session`.

The CLI should surface this explicitly in command results and in `agents mailbox status`.

Alternative considered:
- Treat all successful registrations as immediately active
  Rejected because local interactive TUI processes are launched once and keep their original env until respawn.

### Decision: Reuse runtime launch-plan refresh mechanics instead of editing manifests ad hoc

The runtime already has a supported pattern for mutating mailbox-related launch state:

- update the in-memory launch plan,
- propagate it through `update_launch_plan()` on the backend session,
- persist the updated session manifest,
- refresh shared-registry publication.

The new late-registration path should generalize that pattern into first-class register and unregister operations rather than writing JSON into manifests directly from CLI code.

Alternative considered:
- Implement mailbox register/unregister entirely in `houmao-mgr` by editing manifest files
  Rejected because it bypasses controller invariants, backend refresh hooks, and registry refresh logic.

### Decision: Scope v1 late registration to local filesystem mailboxes only

The user goal is manual mailbox-root creation and serverless use. That maps directly to the filesystem transport. Stalwart late registration would need endpoint validation, secret materialization, and different operational semantics, while server-backed late registration would require a new server API.

Alternative considered:
- Add transport-generic late registration now
  Rejected because the implementation and operator contract would be materially different for filesystem versus Stalwart.

## Risks / Trade-offs

- [Interactive sessions require relaunch after mailbox register or unregister] → Surface `pending_relaunch` clearly, block misleading immediate-mail claims, and document the relaunch step.
- [Operators may confuse top-level mailbox registration with agent mailbox registration] → Keep `houmao-mgr mailbox ...` focused on root and address administration, and keep `houmao-mgr agents mailbox ...` focused on one managed session.
- [Unregister semantics can remove shared registration that an operator expected to keep] → Default `agents mailbox unregister` to `deactivate`, not `purge`, and require an explicit destructive mode for purge.
- [Late registration on joined sessions without relaunch posture could create persisted state that cannot be activated] → Reject those cases before mutating shared mailbox or manifest state.
- [CLI surface overlap with existing `agents mail ...`] → Keep `agents mailbox ...` limited to registration lifecycle and keep `agents mail ...` as the only runtime-owned mailbox-use surface.

## Migration Plan

1. Add the new OpenSpec-backed CLI contracts and tests for `houmao-mgr mailbox ...` and `houmao-mgr agents mailbox ...`.
2. Implement runtime-controller mailbox register and unregister helpers that persist manifest and registry updates.
3. Wire the new CLI families to filesystem mailbox bootstrap and lifecycle helpers plus local managed-agent resolution.
4. Update docs so local mailbox guidance points operators to late registration instead of launch-time mailbox flags on `houmao-mgr`.
5. Keep existing runtime-local legacy mailbox launch flags intact for now, but treat them as lower-level compatibility surfaces rather than the preferred `houmao-mgr` workflow.

Rollback is low risk because the change is additive at the CLI level. If reverted, previously created filesystem mailbox roots and mailbox registrations remain within the existing filesystem mailbox lifecycle contract.

## Open Questions

- Should `houmao-mgr mailbox register` expose only `in_root` registrations in v1, or also expose explicit symlink-backed registrations for private mailbox directories?
- Should `agents mailbox unregister` offer a `--mode purge` flag on day one, or keep only default `deactivate` until operator demand appears?
