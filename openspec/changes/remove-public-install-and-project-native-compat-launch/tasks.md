## 1. Remove Public Install From The Pair Contract

- [x] 1.1 Remove top-level `houmao-mgr install` and namespaced `houmao-mgr cao install` from the supported CLI tree, help text, and command tests.
- [x] 1.2 Remove the public `/houmao/agent-profiles/install` server route, client methods, request models, and verification coverage that exist only for compatibility-profile preinstall.
- [x] 1.3 Update pair docs and migration docs so the supported workflow launches directly from native agent definitions instead of preinstalled compatibility profiles.

## 2. Unify Native Launch Resolution

- [x] 2.1 Introduce one shared native launch-target resolver under `src/houmao/agents/` for pair launch that resolves the effective agent-definition root, the first-cut tool-lane recipe selector, and optional role binding.
- [x] 2.2 Change top-level native headless launch translation and session-backed pair launch to use that shared native resolver instead of treating `--agents` as an installed compatibility profile name or requiring blueprint-by-name resolution in the first cut.
- [x] 2.3 Make native launch contracts support brain-only launch explicitly by allowing optional role provenance, mapping missing role prompt to an empty system prompt, and avoiding synthesized role identity when no role package exists.

## 3. Replace Preinstalled Compatibility Profiles With Launch-Time Projection

- [x] 3.1 Update the compatibility control core so session-backed `create_session()` / `create_terminal()` resolve native launch inputs at launch time instead of loading preinstalled compatibility profiles.
- [x] 3.2 Rework session-backed provider startup so launch-time projection produces a profile-shaped compatibility object for the existing adapter seam while native brain-home / launch-plan environment becomes the launch authority and sidecars stay ephemeral under the session root.
- [x] 3.3 Break up `CompatibilityProfileStore` so public install, source-resolution, and index-authority responsibilities are removed while any remaining markdown or provider-artifact materialization helpers survive only as internal launch-scoped utilities.

## 4. Migrate Demo And Verification

- [x] 4.1 After task 3.1 lands, update the interactive full-pipeline demo to launch from demo-owned non-test tracked native agent-definition inputs with no `houmao-mgr install` step.
- [x] 4.2 Add or revise unit and integration coverage for removed install commands, shared recipe-based selector resolution, brain-only empty-prompt launch, and session-backed launch-time projection.
- [x] 4.3 Update OpenSpec-aligned docs and regression tests so pair verification covers native selector resolution and no longer expects public install behavior.
