## Context

The CAO integration in this repository sits at two different layers that have drifted apart from upstream reality.

At the typed boundary, `houmao.cao.models` still treats CAO terminal providers as a closed enum even though synced upstream CAO now exposes a larger and evolving provider set, including cross-provider profile routing and `kimi_cli`. That means simple upstream additions can break typed parsing even when the rest of our runtime only cares about terminal status, output, and a small explicit launch mapping.

At the operator/documentation layer, the repository still describes CAO as if launch working directories must live under the CAO home tree. Upstream removed that restriction. Our launcher/runtime code no longer enforces that old rule locally, but docs and demo framing still imply that the nested launcher-home/worktree layout is a CAO requirement rather than a repo-owned default for isolation and reproducibility.

This change keeps the runtime's supported CAO launch surface intentionally narrow while removing the brittle parts that now create unnecessary sync friction.

## Goals / Non-Goals

**Goals:**
- Make CAO terminal provider parsing forward-compatible with upstream provider additions.
- Keep runtime launch-time provider support explicit and fail-fast for unsupported tools.
- Clarify that CAO launcher home owns CAO state/profile-store, not an extra repo-owned workdir containment rule.
- Keep `cao_only` as the generic CAO-native execution path and make `shadow_only` explicitly parser-scoped.
- Update demo/operator docs so current defaults are described as repo-owned workflow choices, not CAO requirements.

**Non-Goals:**
- Adding new runtime-supported CAO-backed tools such as Gemini, Kimi, Q CLI, or Kiro CLI in this change.
- Replacing runtime-generated CAO profiles with checked-in static upstream profiles.
- Removing the interactive demo's default worktree provisioning.
- Redesigning shadow parser internals or changing Codex/Claude parser behavior.

## Decisions

### 1. Treat CAO response `provider` values as open strings

**Choice:** Parse terminal `provider` as a non-empty string, while keeping `status` as a validated enum.

Rationale:
- Upstream provider identifiers are growing faster than our repo-owned type boundary needs to care.
- Most local call sites do not need exhaustive provider branching after parsing a terminal payload.
- This keeps syncs from failing on harmless upstream provider additions.

Alternatives considered:
- *Keep extending the enum whenever upstream adds a provider* — rejected because it creates churn and avoidable sync breakage.
- *Make the entire terminal response loosely typed* — rejected because terminal status and output mode still benefit from strict validation.

### 2. Keep launch-time tool-to-provider mapping explicit

**Choice:** Continue using an explicit runtime-owned mapping from supported tools to CAO provider identifiers, and continue to fail fast for unsupported CAO-backed tool launches.

Rationale:
- Parsing an observed provider string is not the same thing as supporting that tool end to end.
- The runtime still has tool-specific bootstrap and parser behavior for Codex and Claude.
- This preserves a clear operator contract: forward-compatible reads, intentionally limited writes/launches.

Alternatives considered:
- *Infer support from any provider id returned by CAO* — rejected because it would silently widen runtime support without matching bootstrap/parser coverage.
- *Derive provider from upstream profile metadata alone* — rejected because the runtime still starts from repo-owned tool manifests and launch plans.

### 3. Make workdir pass-through explicit and move the old containment story into history

**Choice:** Treat the resolved workdir as a launch input that the runtime passes through to CAO without adding a repo-owned rule that it must live under launcher home, tool home, or user home.

Rationale:
- Upstream CAO now owns workdir validation for this concern.
- Our local launcher code already only validates that `home_dir` exists and is writable for CAO state.
- This simplifies docs and reduces false troubleshooting advice.

Alternatives considered:
- *Preserve the old docs/default framing because the demo still uses nested paths* — rejected because it misstates the actual contract.
- *Drop launcher-home/profile-store alignment entirely* — rejected because CAO state and runtime-generated profile lookup still depend on that alignment.

### 4. Keep `shadow_only` intentionally parser-scoped

**Choice:** Document and validate `shadow_only` as a mode that only applies when the runtime has a shadow parser family for the selected CAO-backed tool. `cao_only` remains the generic CAO-native path.

Rationale:
- Our shadow parser stack is intentionally tool-specific today.
- Upstream provider growth should not force us to pretend parser support is generic when it is not.
- This creates a clean expansion path for future CAO-backed tools: launch via `cao_only` first, add `shadow_only` later only when justified.

Alternatives considered:
- *Treat every CAO-backed tool as shadow-capable by default* — rejected because the runtime has no generic shadow parser contract today.
- *Keep the parser limitation implicit in code only* — rejected because it leaves future support boundaries unclear.

### 5. Keep demo defaults, but change their explanation

**Choice:** Preserve the interactive demo's current launcher-home and worktree defaults, but describe them as demo-owned isolation/reproducibility defaults rather than CAO requirements.

Rationale:
- The worktree still gives the demo a real repo context inside a fresh per-run workspace.
- Changing the explanation removes confusion without forcing a demo redesign in the same change.

Alternatives considered:
- *Remove the worktree and use the workspace root directly* — rejected because the demo would lose the checked-out repo context it currently relies on.
- *Leave docs untouched because behavior is unchanged* — rejected because the current docs actively encode a stale upstream assumption.

## Risks / Trade-offs

- [Risk] Open provider strings may hide upstream contract drift if CAO changes more than just the provider vocabulary. -> Mitigation: keep strict typing for status, output mode, and other fields we actively rely on.
- [Risk] Operators may misread the docs cleanup as "any new CAO provider is now fully supported." -> Mitigation: keep launch-time mapping explicit in code, specs, and docs.
- [Risk] Clarifying that workdir may live outside launcher home could encourage setups where CAO state and repo paths are separated in confusing ways. -> Mitigation: keep launcher-home/profile-store alignment guidance explicit and preserve demo defaults.
- [Risk] Future contributors may still widen shadow parsing accidentally when adding a provider mapping. -> Mitigation: capture the parser-scoped `shadow_only` rule in the runtime spec and corresponding launch-time validation/tests.

## Migration Plan

1. Update the CAO REST boundary models/tests so terminal provider ids parse as open strings while terminal status remains validated.
2. Tighten the runtime CAO contract around explicit launch-time provider mapping and parser-scoped `shadow_only`.
3. Refresh launcher, troubleshooting, and demo docs to remove the stale "workdir must be under home" guidance and explain current demo defaults correctly.
4. Run CAO unit/runtime tests and doc-oriented demo checks affected by the boundary changes.

Rollback strategy:
- Restore the previous closed provider enum and related tests.
- Restore previous docs wording if the upstream workdir contract proves incompatible in practice.
- Leave runtime launch-time provider support unchanged either way, so rollback stays local to boundary typing and documentation.

## Open Questions

- Should a follow-up change add a small helper type or predicate for "tool has shadow parser support" so future CAO provider additions cannot accidentally bypass validation?
- Should the interactive demo later expose a clearer split between `--launcher-home-dir` and `--workdir` in the operator UX now that the old containment rule is gone?
