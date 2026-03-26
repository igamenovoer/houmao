## Context

Steps 1–6 of the greenfield migration path already established the passive server's discovery, gateway proxy, TUI observation, request/headless, lifecycle, and pair-client compatibility contracts. What remains before Step 8 retirement is not another runtime feature set; it is proof that `houmao-server` and `houmao-passive-server` can observe and coordinate the same shared-registry world with acceptable parity.

The repository already has one canonical old-server-only validation surface in `scripts/demo/houmao-server-agent-api-demo-pack/`, plus Step 6 passive-server client compatibility that can normalize both authorities into shared managed-agent views. Step 7 needs a separate workflow that starts both authorities simultaneously, provisions the right mix of interactive and headless agents, compares outcomes, and preserves evidence that can justify switching the default server later.

## Goals / Non-Goals

**Goals:**

- Provide one canonical Step 7 validation workflow under `scripts/demo/` for running the old server and passive server in parallel.
- Exercise the exact migration checks called out in the greenfield design: shared discovery, managed state parity, passive-server gateway forwarding, passive-server-launched headless visibility from the old server, and cross-authority stop propagation.
- Preserve machine-readable evidence and raw HTTP snapshots so parity gaps are reviewable and reproducible.
- Keep the validation workflow isolated from the repository checkout by using a pack-owned output root, copied workdirs, and explicit runtime roots.
- Reuse the existing pair-authority compatibility layer where it helps produce comparable managed-agent views.

**Non-Goals:**

- Re-specifying passive-server runtime endpoints already covered by Steps 1–6.
- Making the passive server the default authority in this change.
- Requiring byte-for-byte identical raw JSON across both authorities; Step 7 only needs documented parity on normalized managed behavior.
- Covering old `houmao-server`-only CAO routes or any functionality already declared out of scope for the passive server.
- Fixing every runtime bug discovered by the validator inside this same change. Only minimal blocker fixes needed to keep the canonical validator runnable should co-land here.

## Decisions

### Decision: create a standalone Step 7 demo pack instead of extending the old-server-only API pack

The implementation will add a new demo pack at `scripts/demo/passive-server-parallel-validation-demo-pack/`.

That pack will own:

- the stepwise operator wrapper,
- the unattended/autotest entrypoint,
- pack-local inputs and agent selectors,
- evidence sanitization and report verification helpers, and
- the run-state schema that records both authority base URLs plus launched agent identities.

This keeps Step 7's dual-authority migration proof separate from the older single-authority direct API validator.

**Alternatives considered**

- Extend `scripts/demo/houmao-server-agent-api-demo-pack/`: rejected because that pack's contract is old-server-centric and would become harder to understand if it also had to own passive-server comparison logic and dual-authority lifecycle.
- Rely on manual notes or ad hoc shell scripts: rejected because Step 7 needs reproducible evidence, not one-off experiments.

### Decision: run both authorities in one isolated shared-registry topology with separate server roots

The validator will start one old `houmao-server` and one `houmao-passive-server` against the same pack-owned shared runtime and registry roots while keeping authority-owned logs, PID files, and server-instance metadata separate.

The run root will preserve enough structure to debug both sides independently, for example:

- one shared runtime/registry area used by locally launched agents and by the passive server's discovery loop,
- one old-server area,
- one passive-server area,
- one evidence/control area for reports, HTTP snapshots, and persisted run state.

The two authorities must listen on distinct configurable ports. Defaults can match the migration note (`9889` for old server, `9891` for passive server), but the pack must allow overrides so maintainers can avoid local conflicts.

**Alternatives considered**

- Let each authority use a different runtime root: rejected because Step 7 is specifically about both servers observing the same shared-registry world.
- Use ambient user-managed server instances: rejected because evidence becomes non-reproducible and cleanup/debugging become ambiguous.

### Decision: provision shared interactive validation agents locally, but provision the Step 7 headless lane through the passive server

The validator will prove two different authority relationships:

1. Shared interactive agents launched through the local managed-agent path (`houmao-mgr agents launch` or the same underlying runtime/controller path) must appear on both authorities, because neither server owns their admission.
2. Headless agents launched through `POST /houmao/agents/headless/launches` on the passive server must become visible through the old server, because the shared registry is the cross-authority source of truth.

This split mirrors the migration design directly and prevents the validator from accidentally proving only a server-local happy path.

**Alternatives considered**

- Launch all agents through the old server: rejected because it would not prove passive-server-owned headless publication.
- Launch all agents through the passive server: rejected because it would not prove that `houmao-mgr`-launched shared agents are equally visible from both authorities.

### Decision: compare normalized managed-agent views for pass/fail, while preserving raw authority snapshots

The pass/fail comparison layer will normalize each authority's public agent views into the existing managed-agent model family already used by pair-aware clients. The validator will compare a documented stable subset of fields such as identity, transport, gateway presence, current managed state, and recent-history semantics.

Raw HTTP responses from both authorities will still be preserved under the run output for debugging. They are evidence, but not the sole comparison mechanism, because Step 6 intentionally left the passive server with both observation-native routes and compatibility-projection routes.

**Alternatives considered**

- Diff raw JSON payloads directly: rejected because the authorities do not have identical route maps or identical authority-owned metadata.
- Compare only CLI text output: rejected because it is harder to sanitize, snapshot, and debug.

### Decision: expose one phase-based stepwise wrapper and one stricter unattended harness over the same evidence schema

The pack will expose a human-driven stepwise wrapper (for example `run_demo.sh`) and a stricter unattended runner (for example `autotest/run_autotest.sh`) that use the same phase model and write to the same report/evidence schema.

The validation phases are:

1. start both authorities and provision the shared interactive lane,
2. inspect shared discovery plus managed state parity,
3. exercise passive-server gateway proxy behavior,
4. launch a passive-server-managed headless lane and verify old-server visibility,
5. stop a shared agent through the passive server and verify disappearance on both authorities,
6. verify and sanitize the final report.

This keeps debugging and automation aligned instead of creating separate one-off scripts for each surface.

**Alternatives considered**

- One monolithic auto-only script: rejected because Step 7 investigation benefits from re-runnable intermediate phases.
- Separate unrelated stepwise and auto implementations: rejected because they would drift and produce inconsistent evidence.

## Risks / Trade-offs

- **[Live state parity is inherently noisy]** → Mitigation: compare documented normalized managed fields, allow bounded polling windows for state convergence, and preserve raw snapshots for debugging when parity fails.
- **[Credential, executable, or port prerequisites can make the validator flaky]** → Mitigation: run explicit preflight checks before starting either authority or provisioning any live agent.
- **[A validation-focused change can surface unrelated runtime bugs]** → Mitigation: keep the Step 7 change scoped to the validator and only co-land the smallest blocker fixes needed to keep the canonical workflow runnable; file follow-up changes for broader runtime issues.
- **[Two live authorities increase cleanup complexity]** → Mitigation: keep all run artifacts under one pack-owned output root, record all spawned PID/session identifiers, and preserve evidence on failure instead of attempting opaque best-effort cleanup.

## Migration Plan

1. Create the new demo-pack scaffold, run-state format, and report helpers.
2. Implement dual-authority preflight and startup against one shared runtime/registry root with distinct ports and preserved logs.
3. Implement the shared interactive lane phase plus discovery/state parity comparison.
4. Implement the passive-server gateway proxy phase using the shared interactive lane.
5. Implement the passive-server headless launch phase and old-server visibility checks.
6. Implement the passive-server stop phase, final report verification, and operator/autotest docs.
7. Run the validator against the Step 6 passive server and use the captured report as the Step 7 readiness artifact for deciding whether Step 8 can begin.

Rollback is straightforward because this change is additive. Maintainers can keep using the old server and the existing old-server-only validator if the new Step 7 pack exposes parity gaps that must be fixed first.

## Open Questions

None. The main remaining uncertainty is implementation effort, not architecture or scope.
