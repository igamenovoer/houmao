## Context

The CAO integration in this repository has partially caught up with upstream, but the remaining mismatches now live in a smaller set of places than when this change was first proposed.

At the typed boundary, `houmao.cao.models` still treats CAO terminal providers as a closed enum and `houmao.cao.__init__` still re-exports that enum as part of the public CAO package surface, even though synced upstream CAO now exposes a larger and evolving provider set, including cross-provider profile routing and `kimi_cli`. In contrast, the launch path in `src/houmao/agents/realm_controller/backends/cao_rest.py` already maps tools to provider ids with plain strings.

At the parser/runtime boundary, shadow-parser support is still expressed indirectly in two places: `launch_plan.py` owns the per-tool default parsing mode, while `cao_rest.py` separately hard-codes the tools that actually have a shadow parser stack. That duplication is now the main contract gap behind the change’s `shadow_only` language.

At the operator/documentation layer, the repository is no longer uniformly stale. `docs/reference/realm_controller.md`, `docs/reference/cao_interactive_demo.md`, and the main interactive demo tutorial already describe much of the newer contract correctly. The clearly stale surfaces are now the launcher and troubleshooting guidance around `home_dir` / workdir containment plus a few demo/help strings that still sound normative.

This change should therefore focus on the remaining source-of-truth gaps: the public typed provider boundary, the explicit shadow-parser-support contract, and the launcher/home/workdir guidance that still contradicts current upstream behavior.

## Goals / Non-Goals

**Goals:**
- Make CAO terminal provider parsing forward-compatible with upstream provider additions and stop exporting a closed provider enum as the response-model contract.
- Keep runtime launch-time provider support explicit and fail-fast for unsupported tools.
- Clarify that CAO launcher `home_dir` owns CAO state/profile-store, not an extra repo-owned workdir containment rule.
- Keep `cao_only` as the generic CAO-native execution path and make `shadow_only` explicitly parser-scoped.
- Define one explicit runtime-owned shadow-parser-support helper/set used by both parsing-mode validation and backend parser-stack selection.
- Update only the still-stale launcher, troubleshooting, and demo/help surfaces so current defaults are described as repo-owned workflow choices, not CAO requirements.

**Non-Goals:**
- Adding new runtime-supported CAO-backed tools such as Gemini, Kimi, Q CLI, or Kiro CLI in this change.
- Replacing runtime-generated CAO profiles with checked-in static upstream profiles.
- Removing the interactive demo's default worktree provisioning.
- Redesigning shadow parser internals or changing Codex/Claude parser behavior.
- Re-sweeping docs that are already aligned with the newer contract unless a small wording touch is needed nearby.

## Decisions

### 1. Treat CAO response `provider` values as open strings

**Choice:** Parse terminal `provider` as a non-empty string, keep `status` as a validated enum, and remove `CaoProvider` as the public response-model contract for this field.

Rationale:
- Upstream provider identifiers are growing faster than our repo-owned type boundary needs to care.
- Most local call sites do not need exhaustive provider branching after parsing a terminal payload.
- The launch path already uses plain string mapping, so keeping a public closed enum only preserves churn at the parsing boundary.
- This keeps syncs from failing on harmless upstream provider additions and removes one misleading public type surface.

Alternatives considered:
- *Keep extending the enum whenever upstream adds a provider* — rejected because it creates churn and avoidable sync breakage.
- *Keep `CaoProvider` as a non-model utility export* — rejected because it preserves a stale curated vocabulary without helping the runtime launch path.
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

**Choice:** Treat the resolved workdir as a launch input that the runtime passes through to CAO without adding a repo-owned rule that it must live under launcher home, tool home, or user home, and capture that clarification in the launcher capability/spec as well as the runtime-facing docs.

Rationale:
- Upstream CAO now owns workdir validation for this concern.
- Our local launcher code already only validates that `home_dir` exists and is writable for CAO state.
- The remaining stale wording is now concentrated in launcher/troubleshooting surfaces and the launcher spec itself, so the change should update those sources-of-truth directly instead of only touching runtime wording.

Alternatives considered:
- *Preserve the old docs/default framing because the demo still uses nested paths* — rejected because it misstates the actual contract.
- *Drop launcher-home/profile-store alignment entirely* — rejected because CAO state and runtime-generated profile lookup still depend on that alignment.
- *Keep launcher docs/spec out of scope and update runtime docs only* — rejected because that would leave the strongest source-of-truth contradiction untouched.

### 4. Keep `shadow_only` intentionally parser-scoped through one explicit capability helper

**Choice:** Document and validate `shadow_only` as a mode that only applies when the runtime has a shadow parser family for the selected CAO-backed tool, and introduce one explicit repo-owned helper/set for that capability that is shared by parsing-mode validation and backend parser-stack selection. `cao_only` remains the generic CAO-native path.

Rationale:
- Our shadow parser stack is intentionally tool-specific today.
- Upstream provider growth should not force us to pretend parser support is generic when it is not.
- The current repo already duplicates this knowledge between parsing-mode defaults and backend parser-stack construction, so naming one shared capability contract removes ambiguity instead of adding abstraction.
- This creates a clean expansion path for future CAO-backed tools: launch via `cao_only` first, add `shadow_only` later only when justified.

Alternatives considered:
- *Treat every CAO-backed tool as shadow-capable by default* — rejected because the runtime has no generic shadow parser contract today.
- *Reuse the default parsing-mode mapping as the capability gate* — rejected because default selection and mode support are conceptually different and already live in different places in code.
- *Keep the parser limitation implicit in code only* — rejected because it leaves future support boundaries unclear.

### 5. Keep demo defaults, but change their explanation

**Choice:** Preserve the interactive demo's current launcher-home and worktree defaults, but describe them as demo-owned isolation/reproducibility defaults rather than CAO requirements, and scope doc cleanup to the demo/help surfaces that still imply the older containment story.

Rationale:
- The worktree still gives the demo a real repo context inside a fresh per-run workspace.
- Several demo overview/tutorial surfaces are already aligned, so the remaining work should be precise instead of broad.
- Changing the explanation removes confusion without forcing a demo redesign in the same change.

Alternatives considered:
- *Remove the worktree and use the workspace root directly* — rejected because the demo would lose the checked-out repo context it currently relies on.
- *Leave docs untouched because behavior is unchanged* — rejected because the current docs actively encode a stale upstream assumption.

## Risks / Trade-offs

- [Risk] Open provider strings may hide upstream contract drift if CAO changes more than just the provider vocabulary. -> Mitigation: keep strict typing for status, output mode, and other fields we actively rely on.
- [Risk] Removing `CaoProvider` from the public export surface is a small API break for any internal importers or tests. -> Mitigation: this repo currently prioritizes clarity over backward compatibility, and the change will update the known importer/test surfaces explicitly.
- [Risk] Operators may misread the docs cleanup as "any new CAO provider is now fully supported." -> Mitigation: keep launch-time mapping explicit in code, specs, and docs.
- [Risk] Clarifying that workdir may live outside launcher home could encourage setups where CAO state and repo paths are separated in confusing ways. -> Mitigation: keep launcher-home/profile-store alignment guidance explicit and preserve demo defaults.
- [Risk] Future contributors may still widen shadow parsing accidentally when adding a provider mapping. -> Mitigation: capture the parser-scoped `shadow_only` rule in the runtime spec and implement one explicit shared shadow-parser-support helper/set plus corresponding validation/tests.
- [Risk] Adding the launcher capability/spec to this change increases the OpenSpec surface slightly. -> Mitigation: the extra scope is documentation/spec alignment only and removes a direct contradiction that would otherwise remain after implementation.

## Migration Plan

1. Update the CAO REST boundary models/exports/tests so terminal provider ids parse as open strings while terminal status remains validated.
2. Tighten the runtime CAO contract around explicit launch-time provider mapping and one explicit shadow-parser-support helper/set.
3. Refresh launcher, troubleshooting, and remaining demo/help surfaces to remove the stale "workdir must be under home" guidance and explain current demo defaults correctly.
4. Update the launcher delta spec alongside the runtime/client delta specs so OpenSpec’s source of truth matches the intended docs/code changes.
5. Run CAO unit/runtime tests and doc-oriented demo checks affected by the boundary changes.

Rollback strategy:
- Restore the previous closed provider enum/export and related tests.
- Restore previous docs/spec wording if the upstream workdir contract proves incompatible in practice.
- Leave runtime launch-time provider support unchanged either way, so rollback stays local to boundary typing and documentation.

## Open Questions

- Should the interactive demo later expose a clearer split between `--launcher-home-dir` and `--workdir` in the operator UX now that the old containment rule is gone?
