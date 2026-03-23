## Context

The `gateway-mail-wakeup-demo-pack` remains the repository's runnable walkthrough for gateway-owned unread-mail wake-up behavior. Current gateway reference docs still point readers at this pack when they need to inspect notifier audit history and queue-backed wake-up evidence.

What has changed around it is the repository's fixture direction. Narrow mailbox and runtime-contract demos now prefer copied dummy-project workdirs plus lightweight `mailbox-demo` blueprints, while repo worktrees and heavyweight `gpu-kernel-coder` roles are reserved for repository-scale engineering flows. The gateway wake-up pack has not been refreshed to that new default shape yet.

The pack also has weaker automated protection than nearby mailbox flows. It has solid unit coverage for parameter parsing, audit summarization, and report sanitization, but it lacks stronger regression checks around fixture provisioning and the pack's start and auto orchestration boundaries.

## Goals / Non-Goals

**Goals:**

- Keep the gateway wake-up pack as the repository's dedicated runnable walkthrough for gateway notifier behavior.
- Refresh the pack so its default started agent uses a copied dummy-project workdir and the lightweight `mailbox-demo` blueprint family.
- Preserve the current one-agent plus external-injector mental model, unread-set semantics, and gateway-owned verification artifacts.
- Make the pack's documentation and expected-report contract teach the new default fixture shape explicitly.
- Strengthen automated regression coverage for the pack's tracked defaults, provisioning behavior, and report contract.

**Non-Goals:**

- Replacing the gateway wake-up pack with the mailbox roundtrip tutorial pack.
- Changing gateway notifier semantics, public gateway HTTP routes, or unread-set batching behavior.
- Adding a new public runtime CLI command for gateway wake-up demos.
- Preserving compatibility with old demo output directories that were provisioned as repository git worktrees.

## Decisions

### Decision 1: Keep the pack separate and gateway-specific

This change does not fold gateway wake-up behavior into the mailbox roundtrip tutorial. The gateway wake-up pack still exists to answer a different question: whether a live gateway notices unread mail, records notifier decisions durably, and wakes a mailbox-enabled session through gateway-owned control surfaces.

That separation is still important because the mailbox roundtrip tutorial now explicitly excludes gateway transport from its automatic correctness boundary.

Alternatives considered:

- Merge gateway wake-up behavior into the mailbox roundtrip tutorial. Rejected because it would blur the line between direct runtime mailbox correctness and gateway-owned wake-up behavior.
- Deprecate the pack and point readers only at gateway reference docs. Rejected because the repository still needs a runnable demonstration and verification surface for notifier audit behavior.

### Decision 2: Rebase the default fixture shape onto copied dummy-project plus `mailbox-demo`

The pack will adopt the same default fixture direction already used by the mailbox roundtrip tutorial pack:

- copy a tracked source-only dummy-project fixture into `<demo-output-dir>/project`,
- initialize that copied tree as a fresh standalone git-backed workdir, and
- start the managed session with the lightweight `mailbox-demo` blueprint family instead of the heavyweight `gpu-kernel-coder` family.

This keeps the demo narrower, cheaper, and more deterministic while preserving the fact that the gateway still operates against a real mailbox-enabled runtime session.

Alternatives considered:

- Keep the repository worktree and only switch the blueprint. Rejected because the real drift is the full fixture model, not just the role name.
- Keep the heavyweight defaults because the wake-up task writes one file. Rejected because that task is still a narrow mailbox/runtime-contract action rather than a repository-scale engineering workflow.

### Decision 3: Reuse the dummy-project provisioning pattern, but keep the implementation pack-local

The gateway pack should follow the same provisioning semantics already proven in the mailbox roundtrip pack: source-only fixture copy, fresh git initialization, and explicit metadata that marks the copied project as demo-managed.

The implementation may borrow the pattern closely, but this change does not require a new shared helper extraction. Pack-local helper logic remains acceptable as long as the semantics match the repository's dummy-project rules.

Alternatives considered:

- Extract a shared cross-pack demo helper module first. Rejected because it broadens the change and is not necessary to fix the drift.
- Reimplement a looser one-off copy flow with no managed marker. Rejected because rerun and stale-directory handling become harder to reason about.

### Decision 4: Treat existing repo-worktree demo roots as disposable and fail clearly

Old demo output roots that already contain a repository worktree are not worth preserving. If the selected `project/` path already exists and is not a pack-managed copied dummy-project repo, the refreshed pack should fail explicitly rather than silently reusing or mutating it.

Maintainers can rerun the demo with a fresh output dir or delete the old demo root. This is acceptable because demo output directories are disposable runtime artifacts, not durable user data.

Alternatives considered:

- Auto-migrate old worktrees into copied dummy-project repos in place. Rejected because the output roots are disposable and migration would add complexity with little value.
- Silently delete any preexisting `project/` directory. Rejected because destructive cleanup against unrelated directories is unsafe.

### Decision 5: Strengthen regression coverage with deterministic helper-level automation rather than a required real-CLI lane

This change will strengthen regression coverage around the demo pack's tracked defaults, provisioning shape, and report contract through deterministic automated tests. The preferred boundary is helper-level testing with controlled runners, monkeypatched command execution, or demo-owned artifact fixtures rather than a mandatory real Claude/Codex live lane.

That gives the repository better protection against drift without turning the default test suite into an environment-dependent smoke harness.

Alternatives considered:

- Add only README and parameter updates with no new tests. Rejected because the current weakness is partly the lack of automated protection.
- Add a required live end-to-end real-agent lane. Rejected because that would be expensive, environment-sensitive, and outside the bounded refresh this change is trying to deliver.

## Risks / Trade-offs

- [Risk] The gateway wake-up pack could diverge subtly from the mailbox roundtrip pack's dummy-project semantics. → Mitigation: mirror the existing provisioning rules closely and test the managed-project detection and reprovision behavior explicitly.
- [Risk] Maintainers with old demo roots may see new explicit failures. → Mitigation: document that old worktree-based demo roots are disposable and should be removed or replaced with a fresh output dir.
- [Risk] Deterministic tests may still miss some live CAO or gateway integration failures. → Mitigation: keep the regression scope honest in docs and focus the automated lane on fixture/defaults drift plus report-contract correctness.

## Migration Plan

No persistent user-data migration is required.

After the change lands:

1. New runs of `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh` provision copied dummy-project workdirs by default.
2. Existing demo output directories that still contain repository worktrees may fail explicit validation.
3. Maintainers recover by deleting the old demo output directory or choosing a fresh `--demo-output-dir`.

Rollback is straightforward: restore the previous parameter defaults and project-provisioning logic if the fixture refresh proves problematic.

## Open Questions

None at this time.
