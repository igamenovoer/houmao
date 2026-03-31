## Context

The repository already moved maintained path ownership from `.agentsys*` to `.houmao*`, but the live runtime identity and environment contract still carries the old namespace:

- canonical managed-agent names are normalized to `AGENTSYS-<name>`;
- tmux-backed discovery publishes `AGENTSYS_MANIFEST_PATH`, `AGENTSYS_AGENT_ID`, `AGENTSYS_AGENT_DEF_DIR`, and related gateway pointers;
- shared root overrides use `AGENTSYS_GLOBAL_*`, `AGENTSYS_LOCAL_JOBS_DIR`, and `AGENTSYS_JOB_DIR`;
- mailbox runtime bindings, mailbox examples, and request/result sentinels still use `AGENTSYS_*`;
- CAO/runtime override knobs such as no-proxy preservation and Claude/Codex parser version pins still use `AGENTSYS_*`;
- active docs, tests, and CLI help text encode those names as the supported current contract.

The earlier `.agentsys` path-retirement change explicitly left `AGENTSYS_*` env names and `AGENTSYS-*` canonical identities untouched so path cleanup could land independently. This change is the follow-up that finishes the naming transition on live supported surfaces.

Because the current namespace is baked into session discovery, mailbox addresses, registry publication, tests, and docs, the rename is cross-cutting and intentionally breaking.

## Goals / Non-Goals

**Goals:**

- Standardize the active runtime namespace on `HOUMAO-*` and `HOUMAO_*`.
- Rename canonical managed-agent names, session discovery vars, gateway vars, shared-root override vars, mailbox runtime bindings, and supported CAO/runtime override vars into the Houmao namespace.
- Remove the last maintained lowercase/internal `agentsys` strings where they are part of live behavior or active guidance.
- Update supported specs, tests, and reference docs so they describe only the new Houmao namespace.

**Non-Goals:**

- Rewriting archival OpenSpec history, resolved issue notes, or other clearly historical documents purely for terminology cleanup.
- Preserving dual read/write compatibility for the old `AGENTSYS-*` or `AGENTSYS_*` contract on active supported surfaces.
- Auto-migrating already-running tmux sessions, existing shared-registry records, or existing mailbox registrations in place.
- Changing `.houmao` filesystem ownership, project-overlay behavior, or other already-renamed path families beyond the small leftover metadata cleanup.

## Decisions

### Decision 1: Treat `HOUMAO-*` and `HOUMAO_*` as the only supported live namespace

The implementation will rename the live runtime namespace rather than layering aliases on top of it.

That means:

- canonical agent identities become `HOUMAO-<name>`;
- tmux-published runtime pointers become `HOUMAO_MANIFEST_PATH`, `HOUMAO_AGENT_ID`, `HOUMAO_AGENT_DEF_DIR`, and the corresponding `HOUMAO_GATEWAY_*` names;
- shared root overrides become `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, `HOUMAO_LOCAL_JOBS_DIR`, and `HOUMAO_JOB_DIR`;
- supported runtime mailbox bindings and sentinels move to `HOUMAO_MAILBOX_*`, `HOUMAO_MAIL_REQUEST`, and `HOUMAO_MAIL_RESULT_*`;
- supported runtime override knobs move to `HOUMAO_PRESERVE_NO_PROXY_ENV`, `HOUMAO_CAO_CLAUDE_CODE_VERSION`, and matching Houmao-named variants for the same family.

Rationale:

- The repository already allows breaking design cleanup in favor of a clearer active contract.
- Dual namespaces would prolong the very ambiguity this change is meant to remove.
- Tests, docs, and code are already wide enough that maintaining both spellings would add ongoing complexity.

Alternatives considered:

- Keep `AGENTSYS_*` as aliases indefinitely: rejected because it preserves a split live contract and forces future code to normalize both names everywhere.
- Rename only display examples but leave env vars untouched: rejected because that keeps the operator-facing and internal runtime contracts inconsistent.

### Decision 2: Do not preserve backward-compatible discovery for existing live sessions

Supported code paths will read and write only the renamed `HOUMAO_*` variables after this change. Existing tmux sessions or external scripts that still export `AGENTSYS_*` will need to relaunch or update.

Rationale:

- Session discovery is a core authority surface; dual-reading stale names would complicate validation and prolong mixed environments.
- The repository is under active unstable development and explicitly permits breaking runtime changes.
- A full rename is easier to reason about when every supported surface speaks one namespace.

Alternatives considered:

- Read both old and new env vars for one migration window: rejected because it would make session authority and test expectations ambiguous, especially when both names are present.
- Auto-copy `AGENTSYS_*` into `HOUMAO_*` at runtime: rejected because it masks stale callers and creates unclear precedence.

### Decision 3: Rename identity-bearing examples and mailbox addresses together with env vars

Examples, tests, and normative specs that currently use `AGENTSYS-alice`, `AGENTSYS-bob@agents.localhost`, or similar canonical examples will move to `HOUMAO-*` so operator-visible examples match the new runtime identity model.

This also updates any requirement text that derives `agent_id` hashing or lookup semantics from canonical agent names, since those examples and hashes change with the renamed prefix.

Rationale:

- Leaving example identities in the old namespace would keep the docs and scenarios inconsistent with the supported runtime.
- Registry and passive-server lookup behavior depends on canonical name normalization, so example identities are not just cosmetic.

Alternatives considered:

- Rename env vars but leave example addresses on `AGENTSYS-*`: rejected because mailbox and registry docs would continue to teach the wrong canonical identity.

### Decision 4: Retire remaining lowercase/internal `agentsys` leftovers instead of preserving them

The change will also clean up the last maintained lowercase or stray string leftovers that are part of live behavior or active guidance, including:

- stale contributor guidance still pointing at `.agentsys/agents`,
- internal signal names such as `agentsys-headless-turn-...`,
- reserved-prefix and warning messaging that still frames the live namespace as `AGENTSYS`.

Historical or archival materials stay out of scope.

Rationale:

- These leftovers are small but visible inconsistencies once the main namespace is renamed.
- They are cheap to remove while touching the same code and docs.

Alternatives considered:

- Leave internal lowercase strings alone because they are not user-facing APIs: rejected because the repo already identified them as the last maintained `agentsys` leaks.

### Decision 5: Update live specs and docs alongside code, not afterward

The rename will be specified and documented in the same change rather than as a later documentation pass. Active docs and spec requirements that still declare `AGENTSYS_*` stable will be updated to describe the new `HOUMAO_*` contract.

Rationale:

- This is a contract rename; specs and docs are part of the change itself.
- Leaving them for a follow-up would produce immediate contract drift.

Alternatives considered:

- Limit this change to code/tests and fix specs/docs later: rejected because the change would land with known documentation and requirement mismatches.

## Risks / Trade-offs

- [Risk] Existing tmux sessions, registry entries, or operator scripts that still use `AGENTSYS_*` will stop working with supported tooling. → Mitigation: treat the rename as explicitly breaking, require relaunch/re-registration, and update docs/help text to state that only `HOUMAO_*` is supported after the change.
- [Risk] The rename touches many modules and contract tests at once, creating broad churn. → Mitigation: centralize the rename around shared constant definitions and resolver helpers first, then refresh dependent tests and docs from those authoritative names.
- [Risk] Some supported specs currently encode `AGENTSYS_*` stability as a requirement, so partial updates would leave contradictory requirements. → Mitigation: include the relevant capability deltas in this same change and update the repo’s active requirement set atomically.
- [Risk] Mailbox identities and registry examples that derive hashes from canonical names will change expected fixture values. → Mitigation: call out those derived-value updates explicitly in implementation tasks and test refreshes.
- [Trade-off] The change optimizes for one clean namespace rather than a migration bridge. → Mitigation: accept the break now while the repository is still unstable instead of carrying dual naming debt forward.

## Migration Plan

1. Update the active OpenSpec requirements and docs so `HOUMAO-*` / `HOUMAO_*` are the only supported live names.
2. Rename shared constants and normalization helpers in the runtime, registry, mailbox, gateway, and CAO layers.
3. Update command help, current-session discovery flows, and runtime env publication to emit and consume only `HOUMAO_*`.
4. Refresh tests, fixture expectations, and supported docs/examples to use `HOUMAO-*` identities and `HOUMAO_*` env vars.
5. Retire the remaining maintained lowercase/internal `agentsys` strings and stale contributor metadata.

Rollback is straightforward but breaking in the opposite direction: restore the old constant set, revert the spec/doc updates, and relaunch sessions under the restored namespace.

## Open Questions

No blocking open questions remain for proposal-level work. The main intentional posture is already decided: this is a clean break to a single `HOUMAO` runtime namespace rather than a compatibility bridge.
