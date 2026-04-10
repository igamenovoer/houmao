## Context

The repository already decided that `tests/fixtures/agents/` is not one coherent maintained contract. The completed `split-agent-fixtures-by-contract` change separated that overloaded tree into:

- `tests/fixtures/plain-agent-def/` for plain filesystem-backed `--agent-def-dir` workflows,
- `tests/fixtures/auth-bundles/` for local-only credential bundles, and
- project-aware or demo-owned generated trees for maintained project-backed flows.

What remains is transitional residue. The deprecated `tests/fixtures/agents/` path still exists as a redirect stub, some current main specs still cite it as if it were canonical, and several archived entrypoints still default to it. That keeps the repository in an ambiguous half-state: the code and docs say the split already happened, but the tree layout still advertises a deprecated compatibility anchor.

This follow-up change finishes that migration by removing the deprecated path itself and by making the remaining maintained and archived surfaces explicit about the replacement contract.

## Goals / Non-Goals

**Goals:**
- Remove `tests/fixtures/agents/` from the maintained repository tree rather than keeping it as a redirect or migration crutch.
- Update maintained requirements, examples, and guidance so they point directly at the owning fixture lane.
- Prevent archived entrypoints from failing obscurely after the path removal by making them fail fast with clear guidance when they still depend on the deprecated fixture root.
- Keep the change self-contained even where it overlaps with the already-completed split-fixture change.

**Non-Goals:**
- Preserve compatibility for local automation that still targets `tests/fixtures/agents/`.
- Retarget every archival README, expected report, or historical OpenSpec artifact to new paths.
- Reintroduce a symlink or alias that keeps the deprecated path working under a different implementation.
- Invent a new generic fixture abstraction beyond the existing `plain-agent-def`, `auth-bundles`, and owned generated-tree contracts.

## Decisions

### Decision: Remove the deprecated path entirely instead of keeping a redirect stub

The repository will stop tracking `tests/fixtures/agents/` altogether. Maintained docs and specs will no longer mention it as a redirect, migration aid, or compatibility path.

Rationale:
- A redirect stub still looks like a supported repository surface and keeps reintroducing the exact ambiguity the split change was meant to remove.
- The replacement lanes already exist and are clearer when referenced directly.

Alternatives considered:
- Keep the redirect README indefinitely: rejected because it preserves a pseudo-supported path and encourages new references.
- Replace the directory with a symlink: rejected because it hides which lane actually owns a given workflow.

### Decision: Maintained references must point to the owning lane, not to a shared alias

Each maintained surface will reference the contract it actually depends on:

- plain direct-dir examples use `tests/fixtures/plain-agent-def/` or a copied temp root derived from it,
- local credential examples use `tests/fixtures/auth-bundles/`,
- maintained demos use demo-owned tracked `inputs/agents/` trees plus run-local materialization,
- project-aware flows use owned overlay-local state.

Rationale:
- Removal only stays durable if maintained references stop using a broad “fixture root” shorthand.
- The owning-lane reference makes the workflow contract obvious to maintainers and tests.

Alternatives considered:
- Introduce one new replacement alias such as `tests/fixtures/current-agents/`: rejected because it recreates the same overloaded indirection under a different name.
- Rewrite maintained requirements to use only generic `/tmp/agents` examples: rejected because some repository-owned flows do rely on concrete maintained fixture lanes.

### Decision: Archived entrypoints that still depend on the removed path will fail fast rather than being retargeted wholesale

Archived scripts or modules that still assume `tests/fixtures/agents/` exists will not be updated into maintained workflows. Instead, they should refuse to run early with a message that they are archived and depend on a removed fixture-root contract, while pointing operators at maintained surfaces.

Rationale:
- Bulk-retargeting archival packs would spend effort preserving workflows the repository already classifies as historical.
- Once the deprecated path is removed, silent late failures would be confusing; fail-fast behavior is the cleaner archival posture.

Alternatives considered:
- Rewrite every archived pack to the new fixture lanes: rejected because that would turn a cleanup change into a broad legacy-migration project.
- Leave archived entrypoints untouched and let them fail with missing-path errors: rejected because the resulting failures would look accidental rather than intentional.

### Decision: Historical archive content may keep historical path strings, but maintained live artifacts must not

Archived OpenSpec change artifacts, review notes, and historical expected-report snapshots may continue to mention `tests/fixtures/agents/` as part of the historical record. The maintained repository tree, live specs, maintained docs, and runnable maintained surfaces must not.

Rationale:
- Historical artifacts are evidence, not maintained guidance.
- Rewriting archive content would add churn without improving the current contract.

Alternatives considered:
- Globally rewrite every historical reference: rejected because it risks corrupting historical context while offering little runtime value.

## Risks / Trade-offs

- [Risk] Local scripts or operator habits that still use `tests/fixtures/agents/` will break immediately. → Mitigation: update maintained docs to point at the replacement lanes and make archived entrypoints fail with explicit migration guidance.
- [Risk] Overlap with the earlier split-fixture change may duplicate some delta-spec content. → Mitigation: keep this follow-up self-contained and explicit that it finishes the migration by removing the transitional path itself.
- [Risk] Archived entrypoints outside the guard scope may still fail with raw missing-path errors. → Mitigation: audit legacy entrypoints that still default to the deprecated path and cover the runnable ones with fail-fast guards.
- [Risk] The current worktree may still contain ignored host-local auth material under the deprecated path. → Mitigation: treat that data as unsupported local residue and move any needed bundles to `tests/fixtures/auth-bundles/` before removal.

## Migration Plan

1. Update maintained requirements and guidance so all live references use `plain-agent-def`, `auth-bundles`, or owned generated trees directly.
2. Add or tighten archived-demo guards for runnable legacy entrypoints that still assume the deprecated fixture root exists.
3. Remove the tracked `tests/fixtures/agents/` directory and its redirect README from the repository tree.
4. Run focused tests or checks covering maintained path-resolution helpers plus archived-entrypoint fail-fast behavior.
5. Leave historical archive artifacts untouched unless a specific archived runnable surface needs a clearer guard message.

## Open Questions

- Do any archived non-mailbox demo entrypoints still warrant a clearer targeted migration hint than “use a maintained demo surface,” or is a general archived-demo failure message sufficient?
