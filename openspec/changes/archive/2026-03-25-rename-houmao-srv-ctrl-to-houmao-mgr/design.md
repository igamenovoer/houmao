## Context

The current public pair CLI is installed and documented as `houmao-srv-ctrl`, but the live command tree is broader than server control: it owns pair-native managed-agent operations, the explicit `cao` compatibility namespace, local brain construction, and local registry maintenance. The repo already has a large live rename surface across packaging, help text, migration guidance, demos, tests, and multiple current OpenSpec specs.

This repository is under active unstable development, and the project guidance explicitly allows breaking changes when they clarify the supported product boundary. The internal Python package layout under `houmao.srv_ctrl` is already used by implementation code and demo helpers, so the public binary name and the internal module namespace can be treated as separate concerns.

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr` the sole supported public pair-management CLI name.
- Update the supported pair boundary to `houmao-server + houmao-mgr` across live specs, docs, demos, tests, and help text.
- Preserve the current command-family structure and behavior under the new binary name, including `cao`, `agents`, `brains`, `admin`, top-level `launch`, and top-level `install`.
- Fix stale live gateway wording so the renamed CLI consistently points operators to `agents gateway attach`.

**Non-Goals:**

- Renaming the internal Python package, module path, or import namespace away from `houmao.srv_ctrl`.
- Preserving `houmao-srv-ctrl` as a supported long-term public alias.
- Changing launch semantics, provider coverage, or the supported pair architecture beyond the public-name rename.

## Decisions

### Decision 1: Rename only the public binary and user-facing CLI identity in this change

The change will rename the installed script, Click program name, help text, docs, demos, and migration guidance from `houmao-srv-ctrl` to `houmao-mgr`, while leaving the internal implementation package under `houmao.srv_ctrl`.

This keeps the public contract clear without forcing a higher-risk import-path refactor through runtime, demo, and test code in the same change.

Alternatives considered:

- Rename both the public binary and the internal Python package now: rejected because it adds broad internal churn that is not required to fix the user-facing naming problem.
- Keep the current binary name and only adjust descriptions in docs: rejected because the misleading public command name is itself the problem.

### Decision 2: Treat the rename as an atomic breaking change with one supported public name

`houmao-mgr` will become the supported public name for the pair-management CLI, and repo-owned docs, tests, demos, and examples will move to that name in the same change. `houmao-srv-ctrl` will not remain part of the documented supported public surface for this change.

This matches the repository's unstable-development posture and avoids carrying a two-name contract through help output, tests, migration docs, and operator guidance.

Alternatives considered:

- Keep `houmao-srv-ctrl` as a documented deprecated alias: rejected because it preserves the ambiguous name in the supported surface and doubles the amount of contract and verification work.
- Keep an undocumented compatibility alias indefinitely: rejected because it creates hidden surface area without a clear support story.

### Decision 3: Keep the command tree and compatibility split unchanged under the new name

The rename is lexical, not behavioral. The supported pair contract remains:

- `houmao-server + houmao-mgr`
- `houmao-mgr launch`
- `houmao-mgr install`
- `houmao-mgr agents ...`
- `houmao-mgr brains build ...`
- `houmao-mgr admin cleanup-registry ...`
- `houmao-mgr cao ...`

This preserves the current pair-native and CAO-compatible split while clarifying that the public CLI is a management surface rather than a narrow server-control wrapper.

Alternatives considered:

- Use the rename to also restructure command families: rejected because that would turn a naming change into a behavior change.

### Decision 4: Update live OpenSpec requirements but keep existing capability ids

The current capability folder names such as `houmao-srv-ctrl-native-cli` and `houmao-srv-ctrl-cao-compat` will remain as capability ids for now, but their live requirement text will be updated to describe the public `houmao-mgr` binary.

This avoids unnecessary spec-taxonomy churn while still correcting the live user-facing contract.

Alternatives considered:

- Rename capability ids and spec folders to `houmao-mgr-*`: rejected because it would create extra archive and taxonomy churn without changing the actual product behavior.

## Risks / Trade-offs

- [External scripts or operator habits still call `houmao-srv-ctrl`] → Mitigation: update repo-owned migration guidance, demos, and tests atomically so the supported path is unambiguous.
- [Public name and internal module path differ (`houmao-mgr` vs `houmao.srv_ctrl`)] → Mitigation: document the internal module path as implementation detail only and keep all public docs focused on the installed binary.
- [A stale live reference survives the rename sweep] → Mitigation: use grep-based inventory across live code, docs, scripts, and current specs, and add or update tests around the public CLI identity.

## Migration Plan

1. Update OpenSpec proposal, design, and delta specs so the supported contract clearly names `houmao-mgr`.
2. Rename the package script entry and CLI help/prog-name wiring to `houmao-mgr`.
3. Sweep live repo-owned docs, demos, migration guides, and tests to replace supported public usage of `houmao-srv-ctrl`.
4. Verify the new public surface with help-output checks and live-reference sweeps, leaving archived change history untouched.

Rollback is a straightforward revert of the rename change before release. Because this is a breaking rename, partial rollout is not desirable.

## Open Questions

None for this change. If a temporary compatibility alias is later needed for external consumers, that should be handled as a separate explicit follow-up change rather than folded into the base rename.
