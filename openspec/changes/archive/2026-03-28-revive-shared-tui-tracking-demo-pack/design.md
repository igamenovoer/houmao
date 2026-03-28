## Context

The archived shared TUI tracking demo pack is more than historical shell glue. It already contains a real standalone workflow for:

- launching Claude or Codex in tmux,
- observing the visible pane through the shared tracker,
- optionally retaining recorder evidence,
- replaying recorded sessions into public tracked state,
- comparing replay against human-authored ground truth, and
- evaluating coarse robustness sweeps over sparser capture cadences.

The current problem is not the tracker-facing architecture. The problem is that the pack was retired from the supported `scripts/demo/` surface and still bootstraps from `tests/fixtures/agents/` in both `live_watch.py` and `recorded.py`. That makes the demo depend on repository fixture state instead of owning a local demo-shaped source tree the way `minimal-agent-launch` does.

There is also a mismatch between the archived operator docs and the current repository state:

- the archived README already describes a non-legacy `scripts/demo/shared-tui-tracking-demo-pack/` location,
- the source package still lives under `src/houmao/demo/legacy/shared_tui_tracking_demo_pack/`,
- the default config still assumes a committed recorded corpus under `tests/fixtures/shared_tui_tracking/recorded/`, but that corpus is not present in this checkout.

The user asked for a narrower restoration than the broader `houmao-mgr project` work. This design therefore keeps the demo self-contained and local like the neighboring minimal demo instead of depending on `.houmao/` project discovery.

## Goals / Non-Goals

**Goals:**

- Restore the shared TUI tracking demo as a supported `scripts/demo/` surface.
- Give the demo its own tracked secret-free `inputs/agents/` tree with canonical `skills/`, `roles/`, and `tools/` layout.
- Build every live-watch or recorded-capture run from a generated run-local `.agentsys/agents` tree rather than from `tests/fixtures/agents/`.
- Materialize one demo-local auth alias for the selected tool at run time from host-local fixture auth bundles, following the working pattern already used by `minimal-agent-launch`.
- Preserve the existing demo-owned config, scenario, recorder, replay, sweep, and ownership-recovery architecture where it still fits.
- Make the restored operator surface and docs reference only the supported non-legacy paths.
- Fail clearly when recorded-corpus commands are pointed at a missing or empty committed fixture tree.

**Non-Goals:**

- Depending on `houmao-mgr project init`, `.houmao/`, or project-aware agent-definition discovery.
- Redesigning shared tracked-TUI public-state semantics, detector logic, or replay contracts.
- Replacing tmux ownership recovery, recorder lifecycle, or the scenario DSL with an entirely different mechanism.
- Committing plaintext auth bundles inside the restored demo tree.
- Reconstructing a large canonical recorded fixture corpus in the same change if the workflow restoration can land first with explicit preflight behavior.

## Decisions

### Decision 1: Restore the pack as a supported standalone demo with non-legacy source and script paths

The repository should restore the shared TUI tracking pack under supported paths:

- `scripts/demo/shared-tui-tracking-demo-pack/`
- `src/houmao/demo/shared_tui_tracking_demo_pack/`

The old `legacy/` copy can remain archived for history during migration, but the maintained operator surface, code, and docs should point only at the restored supported location.

Rationale:

- The archived README already documents the intended supported location, so the current layout is internally inconsistent.
- The pack is sufficiently self-contained to stand as a maintained demo, unlike purely historical examples that no longer represent current workflows.
- Restoring the supported paths simplifies operator docs and avoids embedding `legacy/` as a normative contract again.

Alternatives considered:

- Keep the implementation under `legacy/` and only bless it in docs: rejected because that leaves the supported surface structurally ambiguous.
- Wait for a larger demo-surface redesign before restoring this pack: rejected because the main blocker here is local bootstrap ownership, not a missing product concept.

### Decision 2: Adopt a demo-owned tracked `inputs/agents/` tree, patterned after `minimal-agent-launch`

The restored pack should own a tracked secret-free agent-definition tree under:

```text
scripts/demo/shared-tui-tracking-demo-pack/inputs/agents/
```

That tree should follow the same canonical shape already used by the minimal demo:

- `skills/`
- `roles/<role>/system-prompt.md`
- `roles/<role>/presets/<tool>/<setup>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/...`

It should contain only the secret-free tracked assets required by the shared-tracker demo, especially the `interactive-watch` role/presets and the tool adapter/setup content needed for Claude and Codex.

Rationale:

- This is the user-requested scoping: make the agent-definition directory local like the neighboring demo.
- A tracked demo-local tree is easier to understand, test, and maintain than an implicit dependency on the broad repository fixture tree.
- It avoids blocking the demo on project-overlay work that is conceptually related but intentionally out of scope here.

Alternatives considered:

- Keep building from `tests/fixtures/agents/`: rejected because that keeps the demo unsupported in practice and hides its launch contract in a repo-wide fixture tree.
- Add a generic project-discovery resolver now: rejected because the user explicitly asked not to depend on `houmao-mgr project` yet.

### Decision 3: Generate a run-local `.agentsys/agents` tree and project a demo-local `default` auth alias

Each run should materialize a generated working tree under the run root, for example:

```text
<run-root>/workdir/.agentsys/agents/
```

The workflow should copy the tracked demo-local `inputs/agents/` tree into that working tree and then materialize one selected-tool auth alias named `default` by linking or projecting from a host-local fixture auth bundle under `tests/fixtures/agents/tools/<tool>/auth/...`.

Tracked demo presets should declare `auth: default` rather than leaking host-specific fixture bundle names into the tracked demo assets.

Rationale:

- This exactly matches the proven pattern used by `minimal-agent-launch`.
- It keeps tracked demo assets secret-free while still allowing local real-tool launches.
- It avoids teaching operators fixture-specific auth names as part of the demo contract.

Alternatives considered:

- Keep the presets bound to `personal-a-default` or other fixture names: rejected because it makes the tracked demo depend on repository-local fixture naming.
- Copy plaintext auth contents into the demo tree: rejected because auth remains local-only host state.

### Decision 4: Reuse the existing shared-tracker workflow architecture instead of reimplementing the demo on top of `houmao-mgr agents launch`

The restored demo should continue to use its existing dedicated workflow modules for:

- live watch,
- recorded capture,
- replay validation,
- sweeps,
- config resolution, and
- durable ownership recovery.

It should not be rewritten as a thin shell wrapper around `houmao-mgr agents launch`.

Rationale:

- The pack needs tighter control over recorder startup, pane sampling, scenario driving, replay artifacts, and cleanup than a generic managed-agent demo wrapper provides.
- The current code already has the right architectural seams; the broken part is launch-source ownership.
- Reusing the existing workflow logic minimizes change risk while restoring the supported surface.

Alternatives considered:

- Rebuild the demo entirely as shell around `houmao-mgr`: rejected because the value of this pack is deeper than a launch smoke test.
- Strip the pack down to live-watch only: rejected because the replay and sweep path is part of what makes the demo useful for tracker development.

### Decision 5: Keep config, scenario, and public-state comparison contracts, but retarget them to the restored paths and local launch assets

The restored pack should preserve:

- `demo-config.toml` plus schema validation,
- the scenario JSON DSL,
- strict replay-vs-ground-truth comparison over public tracked state,
- transition-contract sweeps,
- live-watch recorder optionality, and
- session ownership / cleanup semantics.

These contracts should be retargeted to the supported demo paths and the demo-local launch assets, but not redesigned unnecessarily.

Rationale:

- These were the strongest parts of the archived pack and still align with the active shared tracker modules.
- Preserving them maintains continuity with the prior design and reduces rework.
- It keeps the restored demo relevant to both operator smoke tests and tracker regression analysis.

Alternatives considered:

- Collapse config into ad hoc CLI flags and drop the schema: rejected because the config/reference split was already a deliberate improvement.
- Compare replay against raw pane text or detector internals instead of public tracked state: rejected because that would weaken the contract the pack is explicitly designed to test.

### Decision 6: Treat the committed recorded corpus as optional in the first restored implementation, but make absence explicit

The restored pack should continue to support:

- validating one specified fixture root,
- capturing one new recorded run from a scenario, and
- running sweeps against one specified fixture root.

When the configured committed corpus root is absent or empty, corpus-oriented commands should fail during preflight with a clear error that identifies the missing path instead of assuming the corpus exists.

Rationale:

- The current checkout does not contain the historical committed corpus, so pretending otherwise would produce a broken supported surface.
- Clear preflight behavior allows the workflow restoration to land before a larger fixture-authoring effort.
- Single-fixture capture and validation still preserve the important regression and investigation path.

Alternatives considered:

- Require full committed corpus restoration in the same change: rejected because it widens the change significantly and blocks the more fundamental surface restoration.
- Remove corpus commands entirely: rejected because the existing design and docs still have a valid place for them once fixtures are restored.

## Risks / Trade-offs

- [Risk] Demo-local tracked agent assets can drift from broader repository fixture assets. → Mitigation: keep the demo-owned tree intentionally narrow, reuse canonical adapter/setup content, and test the materialized run-local tree directly.
- [Risk] Auth alias projection can fail on hosts that do not have the expected fixture auth bundles restored. → Mitigation: perform explicit preflight checks and surface the missing source path before launch.
- [Risk] Restoring the supported pack while leaving the legacy copy in place can create temporary path confusion. → Mitigation: update maintained docs and runner paths to point only at the supported location and treat legacy content as archival reference only.
- [Risk] Restoring corpus commands without a present committed corpus can still confuse operators. → Mitigation: make missing-corpus behavior fail fast with a concrete path-oriented message and document live watch as the primary immediate workflow.
- [Risk] The restored pack may still inherit stale assumptions from the archived code. → Mitigation: add targeted tests around generated agent trees, path resolution, auth aliasing, and command preflight behavior instead of only relying on manual demo runs.

## Migration Plan

1. Restore the pack under supported `scripts/demo/` and `src/houmao/demo/` paths while keeping the archived copy out of the maintained operator contract.
2. Add the tracked demo-local `inputs/agents/` tree and switch tracked presets to the demo-local `default` auth alias contract.
3. Add a demo-specific materialization helper that creates `workdir/.agentsys/agents` for each run and projects the selected tool’s local auth alias.
4. Update live-watch and recorded-capture launch paths to build from that generated run-local agent-definition tree.
5. Repoint operator docs, config defaults, and dashboard self-launch paths to the restored supported location.
6. Add explicit preflight handling for missing auth sources and missing/empty committed fixture roots.
7. Add targeted tests and then run the restored demo workflows before removing any remaining maintained references to the legacy path.

Rollback strategy:

- Because this is a demo-surface restoration rather than a shared runtime contract change, rollback can archive the restored supported pack again without migrating user data.
- The main rollback boundary is the path and launch-bootstrap change; the shared tracker modules themselves remain authoritative regardless of demo-surface status.

## Open Questions

No open technical questions remain for the initial proposal. The larger follow-up question of how much committed recorded corpus to restore can be handled as a later scope decision without changing the core restored demo architecture.
