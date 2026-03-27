## Context

The current pair has two different launch models:

- native headless launch resolves native agent-definition inputs from the effective agent-definition root, builds a brain home, composes a launch plan, and starts a managed headless agent through `POST /houmao/agents/headless/launches`
- session-backed TUI launch treats `--agents` as a preinstalled compatibility profile name and reaches `POST /cao/sessions` only after a separate `install` step has populated the server-owned compatibility profile store

That split is the reason the public `install` workflow exists. It is not a native Houmao concept; it is a preload step for one compatibility-preserving transport.

This also leaves the session-backed launch path under-modeled relative to native Houmao launch. The current compatibility profile carries a role-like prompt and some provider-specific fields, but it is not the native brain source of truth for tool config, credentials, skills, or mailbox-related launch inputs. Meanwhile, brain-only launch is a supported Houmao idea, but the current native raw launch contract and launch-plan composition still assume a non-empty role package.

There is already useful precedent for runtime-generated compatibility artifacts in `agents/realm_controller/backends/cao_rest.py`, which renders a temporary CAO profile from role data instead of requiring a preinstalled profile as the operator-facing primitive.

## Goals / Non-Goals

**Goals:**

- Remove public `houmao-mgr install` and `houmao-mgr cao install` from the supported pair workflow.
- Remove the public server install surface that exists only to preload compatibility profile state.
- Make native agent definitions (`brains/`, `roles/`, `blueprints/`) the source of truth for both session-backed and native headless launch.
- Reuse one native launch-resolution model for top-level headless launch and session-backed TUI launch.
- Treat brain-only launch as a first-class supported case with an intentionally empty system prompt.
- Keep provider-specific compatibility artifacts internal and launch-scoped rather than operator-installed state.

**Non-Goals:**

- Removing the explicit `houmao-mgr cao ...` namespace.
- Removing CAO-compatible `/cao/*` session and terminal routes that remain part of the supported pair.
- Retiring currently supported provider identifiers such as `claude_code`, `codex`, or `q_cli`.
- Reworking managed-agent post-launch routes, history, or stop semantics beyond what is needed to remove install-driven startup.

## Decisions

### 1. Remove public install and make native agent definitions the only launch source of truth

`houmao-mgr install` and `houmao-mgr cao install` will be removed from the supported pair contract. The paired server install route under `/houmao/agent-profiles/install` will also be retired as a public contract.

Session-backed launch will no longer rely on a preinstalled compatibility profile name. Instead, the existing `--agents` input on `houmao-mgr launch` and `houmao-mgr cao launch` will be interpreted as a native launch selector resolved from the effective agent-definition root.

Rationale:

- it removes a public workflow that only exists for one compatibility transport
- it makes native agent definitions the single launch source of truth
- it stops teaching operators that a separate install phase is intrinsic to Houmao

Alternatives considered:

- keep `install` and document it as compatibility-only: rejected because it preserves the wrong public model
- auto-run install inside launch: rejected because it preserves preinstalled profile state as the hidden authority instead of removing it

### 2. Introduce one shared native launch-target resolver with explicit brain-only semantics

The pair will use one shared resolution seam for launch inputs under `src/houmao/agents/`, conceptually a `ResolvedNativeLaunchTarget`, with at minimum:

- selected tool / provider lane
- effective `agent_def_dir`
- resolved recipe provenance
- resolved brain-manifest inputs / built brain-home inputs
- optional role identity
- resolved role prompt text, which may be empty

The effective agent-definition root for pair launch will follow the same contract as native headless translation:

- otherwise `AGENTSYS_AGENT_DEF_DIR` when set
- otherwise `<working_directory>/.agentsys/agents`

The first cut SHALL keep that existing native root contract. It SHALL NOT add a new pair-launch `--agent-def-dir` CLI flag.

Selector resolution for `--agents` will be deterministic and native-first:

- explicit path-like selectors may target a recipe under the effective agent-definition root
- otherwise v1 resolves a tool-lane recipe under `brains/brain-recipes/<tool>/`

Blueprint-by-name resolution is explicitly out of scope for the first cut. It can be layered on later through the same shared resolver once the matching rule is specified and tested.

When the selected launch target has no role binding or no matching role package, that launch is still valid. The resolver reports role absence explicitly, the resolved role prompt becomes the empty string, and the launch is treated as a brain-only launch rather than as a validation failure.

Rationale:

- it gives headless and session-backed launch the same native meaning for agent selection
- it makes brain-only launch explicit instead of forcing fake installed profiles or fake roles
- it keeps the first cut focused on recipe-based native launch that already fits current callers

Alternatives considered:

- continue deriving role name from the `--agents` string by convention: rejected because it bakes in a false one-name-equals-all-parts assumption
- treat missing role as an error: rejected because brain-only launch is supported by product intent
- require blueprint-first selector resolution in the first cut: rejected because it adds unproven selector-matching semantics before the core install-removal change is landed

### 3. Session-backed TUI launch will project compatibility artifacts at launch time from native launch data

The compatibility control core will stop treating installed compatibility profiles as its primary input for pair-managed launch. Instead, `create_session()` / `create_terminal()` will resolve native launch inputs and then construct a launch-scoped compatibility projection for provider adapters.

That projection may include:

- a synthesized compatibility profile model compatible with the existing adapter seam
- temporary Markdown or JSON sidecars for providers that still need profile-shaped files
- provider-startup metadata derived from the resolved native launch target

If providers such as `q_cli` or `kiro_cli` still require profile-shaped on-disk artifacts, the control core may materialize them internally at launch time. Those artifacts are an implementation detail, not a public install surface and not operator-managed persistent state.

The first cut should change the projection producer, not the provider-adapter contract. Provider adapters should continue consuming a profile-shaped launch object while the control core stops treating that object as installed persistent authority.

Rationale:

- it keeps CAO-profile artifacts as transport-specific shims instead of a public lifecycle phase
- it matches the existing `cao_rest` precedent of rendering profile artifacts on demand
- it removes the need for a persistent operator-facing compatibility profile store

Alternatives considered:

- keep a persistent compatibility profile store but make launch auto-populate it: rejected because it keeps the store as the hidden authority
- project only the system prompt and ignore the rest of the native launch model: rejected because native brain configuration is broader than prompt text alone

### 4. Session-backed launch will reuse native brain-home and launch-plan data instead of the compatibility home as the launch authority

The current compatibility launch path starts providers from a compatibility-owned home root and injects prompt/config from compatibility-profile fields. That is too narrow for native Houmao launch.

Under the new design, session-backed launch will build or resolve the same native brain-home inputs used by headless launch and will pass the resulting launch-plan environment, home selector, and role-injection data into the TUI provider adapters.

Concretely:

- session-backed launch should reuse native tool-home projection and allowlisted env values from the built brain
- compatibility provider adapters should consume a synthesized profile-shaped projection plus launch-plan-derived provider env instead of treating the compatibility home as the source of truth
- compatibility artifacts that still need files should be written as launch-scoped sidecars attached to the resolved native launch target

Rationale:

- this prevents session-backed launch from becoming a second-class launch path with different config/credential behavior
- it aligns TUI-backed launch with the existing native brain-first model

Alternatives considered:

- keep the current compatibility home and map only role prompt into it: rejected because it discards native brain config and credentials as first-class launch inputs

### 5. Native raw launch contracts will allow brain-only launch

The native headless launch contract should no longer require a non-empty role prompt as a mandatory precondition for a valid launch. The raw server contract may keep an optional role identity field for provenance, but it must allow role omission or null semantics and interpret that case as an empty role prompt.

The same rule applies to session-backed native-to-compat projection: missing role means empty prompt.

Rationale:

- it makes brain-only launch explicit in both public and internal contracts
- it avoids fake placeholder role packages just to satisfy validation

Alternatives considered:

- keep raw contracts strict and synthesize placeholder roles in the CLI: rejected because it hides a supported product case behind fake artifacts

### 6. The interactive demo will migrate from tracked compatibility profile Markdown to tracked native agent-definition inputs

The interactive demo will stop calling `houmao-mgr install` and will no longer treat a Markdown compatibility profile as its startup source of truth.

Instead, startup will point launch at tracked demo-owned or other non-test native agent-definition assets and call detached `houmao-mgr cao launch --headless` directly with the same demo-owned timeout budget and run-root ownership rules already in place.

The supported startup contract will not depend on `tests/fixtures/agents/` as the source for those demo launch assets.

Rationale:

- the demo should model the intended operator workflow after this change
- keeping the old Markdown profile in the demo would reintroduce the obsolete public concept immediately

## Risks / Trade-offs

- [Breaking CLI and server surfaces] → Remove `install` in one coordinated change, update docs/specs/tests in the same rollout, and provide explicit migration wording that launch now resolves native agent definitions directly.
- [Future selector ambiguity when blueprints are added] → Keep the first cut recipe-based and defer blueprint-by-name matching until its rule is specified and tested.
- [Session-backed launch could still diverge from native launch behavior] → Reuse native brain-home projection and launch-plan data rather than mapping only a system prompt into compatibility providers.
- [Provider adapters may still need profile-shaped files] → Allow internal launch-scoped artifact materialization, but keep those artifacts ephemeral or cache-like and never operator-installed.
- [Brain-only support reaches deep into current role-based launch assumptions] → Treat optional role support as an explicit contract change across launch-plan composition, server models, and validation rather than a local CLI workaround.

## Migration Plan

1. Introduce shared native launch-target resolution with optional role support.
2. Change session-backed pair launch to use launch-time compatibility projection from native launch targets.
3. Remove public `install` CLI commands and the public server install route from docs, tests, and supported specs.
4. Migrate the interactive demo from tracked compatibility profile Markdown to tracked native agent-definition inputs.
5. Break up the current compatibility profile-store responsibilities so public install, source-resolution, and index-authority code goes away while any remaining launch-scoped materialization helpers stay internal.

Rollback is intentionally not a compatibility goal for this repository state. If implementation exposes an unresolved provider gap, the corrective action is to fix the native-to-compat projection path rather than restoring public install as the operator workflow.

## Open Questions

None for this revision.
