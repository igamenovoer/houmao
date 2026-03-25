## Context

Runtime-managed unattended launch is intentionally fail-closed. Before the provider starts, launch-plan composition detects the real tool version, selects a compatible launch-policy strategy for the selected backend surface, and applies that strategy against the resolved runtime home and workdir.

For Claude, that model is currently undermined by integration drift in two places. First, `src/houmao/agents/launch_policy/registry/claude.yaml` only declares one unattended strategy window (`2.1.81 <= version < 2.1.82`), so a newer installed Claude Code build such as `2.1.83` fails both `raw_launch` and `claude_headless` startup before provider execution. The current `{min_inclusive,max_exclusive}` shape also encourages narrow hand-maintained windows instead of clearer dependency-style supported-version declarations. Second, `build_launch_plan()` passes only the resolved runtime env payload into `apply_launch_policy()`, so the documented `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` process override is invisible on runtime-managed launch unless it is redundantly projected into the selected env file.

The recent local interactive launch work made this easier to see, but the underlying issue is shared across runtime-managed Claude launch surfaces. The fix therefore needs to repair strategy coverage, runtime override plumbing, operator diagnostics, and coverage guardrails together.

## Goals / Non-Goals

**Goals:**

- Restore maintained Claude unattended launch on validated provider versions without weakening fail-closed startup behavior.
- Make supported-version declarations readable and maintainable as dependency-style version ranges.
- Make `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` work on runtime-managed launch exactly as the runtime spec promises.
- Improve `houmao-mgr agents launch` errors so operators can tell the difference between backend selection succeeding and provider startup being blocked by missing unattended strategy support.
- Add regression and drift coverage so maintained Claude unattended launch paths fail fast in CI or local validation when registry data falls behind reality.

**Non-Goals:**

- Introducing automatic fallback from unattended launch to interactive/operator-confirmed launch.
- Adding implicit nearest-lower or latest-known strategy fallback when no declared supported range matches the detected executable version.
- Adding new override modes that pretend the executable is a different version; the existing strategy-id override remains the explicit escape hatch in this change.
- Building a generic auto-updating provider compatibility service or network-fetched version registry.
- Reworking the broader launch-policy architecture shared by Codex, Claude, and future tools.
- Guaranteeing support for every newly released Claude version without explicit validation.

## Decisions

### 1. Express strategy support as dependency-style supported-version declarations

The fix will keep the launch-policy registry as the source of truth for unattended compatibility, but strategy entries will declare supported tool versions with one dependency-style specifier string (for example `>=2.1.81,<2.2`) rather than only separate min/max boundary fields. Strategy resolution will continue to use the actual detected executable version and will choose exactly one strategy whose declared supported-version range contains that version for the requested backend and prompt mode.

For the immediate blocker, we will widen or add Claude strategy coverage only for versions whose runtime-state assumptions have been validated. If Claude `2.1.83` still uses the same owned paths and startup suppressions as `2.1.81`, the supported-version declaration may be widened; otherwise a new explicit strategy entry should be added.

This keeps compatibility readable for operators and maintainers without weakening fail-closed behavior. The registry already models backend surfaces, owned paths, and evidence, so clearer supported-version declarations improve maintenance while preserving the requirement that the detected version must actually match a declared supported range.

**Alternatives considered:**

- Keep the current `{min_inclusive,max_exclusive}` fields only. Rejected because they are less readable, invite overly narrow hand-managed windows, and make policy intent harder to compare across strategies.
- Add implicit nearest-lower or latest-known fallback. Rejected because those semantics silently weaken fail-closed behavior and blur the line between validated compatibility and operator override.
- Bypass strategy selection for local interactive launch only. Rejected because the issue affects both `raw_launch` and `claude_headless`, and the current shared-policy architecture is correct.

### 2. Keep default matching strict and use override by explicit strategy id

Default unattended resolution will remain strict: if the detected executable version does not satisfy any declared supported-version range for the requested backend and prompt mode, startup fails before provider launch.

This change keeps `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` as the explicit operator escape hatch for controlled experiments instead of adding version spoofing, nearest-lower matching, or “use latest anyway” semantics. That keeps the runtime contract easy to reason about: normal launch uses detected version plus declared supported ranges; explicit override pins one known strategy id.

**Alternatives considered:**

- Force-select a strategy by pretending the executable reports a different version. Rejected for this change because it obscures what was actually validated and overlaps with explicit strategy-id pinning.
- Add “use latest known strategy” semantics. Rejected because “latest” is not the same as “compatible” and would turn hard compatibility failures into hidden policy guesses.

### 3. Resolve transient strategy override from the launch caller environment

Runtime-managed launch-plan composition will treat `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` as control input from the caller environment, not as normal provider runtime env. The override key should be merged into the env passed to launch-policy resolution even when it is absent from the selected credential-env allowlist, while remaining excluded from the final provider env unless some other mechanism already projects it there.

This matches the documented contract and keeps controlled experiments lightweight. It also avoids coupling debug overrides to credential-profile env files or leaking override-only control variables into persisted launch manifests.

**Alternatives considered:**

- Require the override env var to be present in the selected env contract allowlist. Rejected because it contradicts the current runtime spec and makes temporary experiments depend on repo-managed credential projections.
- Persist the chosen override into the built brain manifest. Rejected because overrides are intentionally transient and should not mutate recipe/build intent.

### 4. Surface policy compatibility failures explicitly at the local launch boundary

`houmao-mgr agents launch` will continue failing before provider startup when unattended policy cannot be satisfied, but the surfaced error should clearly state that:

- launch mode/backend selection succeeded,
- the detected Claude version lacked compatible unattended support for that backend surface, and
- provider startup did not begin.

This keeps the operator-facing contract honest without weakening the runtime’s fail-closed stance. The diagnostic should carry the requested policy mode, detected version, and resolved backend surface so users can tell whether the fix is registry coverage, override selection, or a different runtime bug.

**Alternatives considered:**

- Preserve the raw lower-level exception text only. Rejected because it obscures where launch stopped and makes the problem look like a generic backend failure.
- Auto-downgrade to interactive startup with prompts. Rejected because recipes explicitly request unattended posture and callers should not silently get a different trust/approval model.

### 5. Add both deterministic and operational drift guardrails

The change will add deterministic tests around supported-version declaration parsing, Claude strategy selection, runtime-managed override visibility, and local launch diagnostics. It will also add one maintained coverage path for version drift on the Claude unattended workflow used by local managed launch. That guardrail may be an installed-version validation when Claude is present, or a maintained fixture assertion that explicitly pins the supported version/backend assumption used by the repository’s unattended Claude path.

Using both layers keeps the suite reliable while still detecting the class of failure that triggered this issue.

**Alternatives considered:**

- Unit tests only. Rejected because structural tests alone already missed provider-version drift.
- Live installed-version checks only. Rejected because they can be unavailable or noisy in some environments and need deterministic backup coverage.

## Risks / Trade-offs

- **Declared supported ranges can still lag future Claude releases** → Keep ranges narrow unless evidence shows a broader window is safe, and make unsupported-version diagnostics precise.
- **Dependency-style version syntax could be implemented inconsistently with operator expectations** → Support a clearly documented subset that covers the maintained use cases and test parser behavior thoroughly.
- **Environment-specific drift checks may be flaky when Claude is unavailable** → Keep deterministic unit/integration coverage mandatory and make installed-tool validation conditional or clearly scoped.
- **Richer diagnostics may expose more launch-policy detail to operators** → Limit output to policy mode, backend surface, detected version, and provider-start status; do not include secrets or raw env dumps.

## Migration Plan

1. Define the dependency-style supported-version declaration format and migrate launch-policy strategy parsing to it.
2. Validate whether the existing Claude unattended strategy assumptions still hold for the target supported version window.
3. Update the Claude launch-policy registry to cover the validated version/backend surfaces with the new declaration format.
4. Repair runtime-managed override env handling in launch-plan composition.
5. Improve local `houmao-mgr agents launch` error mapping for launch-policy compatibility failures.
6. Add deterministic regression tests and the maintained drift guardrail.

Rollback is straightforward: narrow or remove the new Claude strategy coverage if validation proves wrong, while preserving the override-plumbing and diagnostics fixes because they repair already-documented behavior.

## Open Questions

- What exact dependency-style version-specifier subset should launch-policy strategy declarations support in the first iteration?
- Should the immediate Claude fix widen the existing `claude-unattended-2.1.81` support declaration or introduce a new strategy id for the validated newer version window?
- Which maintained drift guardrail is the best long-term fit here: an installed-Claude validation path, a pinned fixture/version assertion, or both?
