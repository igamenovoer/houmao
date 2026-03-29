## Context

Houmao's current project-local architecture is a catalog-backed `.houmao/` overlay:

- `.houmao/houmao-config.toml` is a lightweight discovery anchor and compatibility-projection config;
- `.houmao/catalog.sqlite` plus `.houmao/content/` are the canonical project-local store;
- `.houmao/agents/` is a compatibility projection materialized only when file-tree consumers still need `roles/`, `tools/`, and `skills/` on disk.

The remaining problem is not that `.houmao/agents/` and the catalog are competing sources of truth. The problem is contract drift: several active or still-documented consumers continue to preserve `.agentsys` as the ambient fallback or generated path family even though current project-local workflows have already moved to `.houmao`.

The current split is visible in four places:

- shared project-aware resolution discovers `.houmao/houmao-config.toml`, but no-config fallback still returns `.agentsys/agents`;
- pair-native `houmao-mgr brains build` and preset-backed `houmao-mgr agents launch` already route discovered overlays through the compatibility projection, but the non-project fallback still points at `.agentsys/agents`;
- deprecated compatibility entrypoints (`build-brain`, `start-session`) still hardcode `.agentsys` help text and fallback logic instead of matching the shared resolver contract;
- maintained demo and scratch helpers plus active docs/tests still generate or document `.agentsys*` paths.

The change is intentionally breaking: `.agentsys` is being retired rather than preserved as a compatibility fallback. At the same time, explicit CLI overrides, explicit environment overrides, and tmux-published `AGENTSYS_AGENT_DEF_DIR` for resumed name-based control remain part of the live contract.

## Goals / Non-Goals

**Goals:**

- Retire `.agentsys` as the ambient no-config fallback for filesystem agent-definition consumers.
- Keep the catalog-backed `.houmao/` overlay as the canonical project-local model and `.houmao/agents/` as the compatibility projection used by file-tree consumers.
- Remove `.agentsys/agents` as an ambient default or fallback root.
- Change the no-config default agent-definition root to `<cwd>/.houmao/agents`.
- Ensure `houmao-mgr project init` respects an existing configured `paths.agent_def_dir` value for the compatibility projection instead of assuming only `.houmao/agents`.
- Move maintained default/generated `.agentsys*` paths for agent trees and scratch outputs into `.houmao` or another Houmao-owned path family.
- Align specs, docs, tests, and CLI help text with the new contract.

**Non-Goals:**

- Renaming existing `AGENTSYS_*` environment variables in this change.
- Auto-migrating old `.agentsys/` trees on disk.
- Retargeting unrelated generic OS-temp usage in compatibility-provider internals that do not currently derive from `.agentsys*`.
- Rewriting archived OpenSpec changes or legacy demo material only for terminology cleanup.
- Changing tmux-session and shared-registry discovery for already-running managed sessions.

## Decisions

### Decision 1: Use one config-first filesystem agent-definition resolution contract everywhere

Ambient filesystem agent-definition lookup will use the same precedence everywhere it is needed for fresh build/start flows:

1. explicit `--agent-def-dir`
2. `AGENTSYS_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. default `<cwd>/.houmao/agents`

When a project config is discovered, `paths.agent_def_dir` will continue to resolve relative to the `.houmao/` directory itself.

When a discovered project overlay is catalog-backed, pair-native build and launch flows will continue to materialize the compatibility projection from that overlay before reading presets, role prompts, or tool content. Pure discovery/status paths may report the resolved compatibility-projection root without forcing materialization.

This shared contract will be reused by:

- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`
- `houmao-mgr project status`
- deprecated standalone `build-brain`
- deprecated standalone `start-session`

Alternatives considered:

- Keep `.agentsys/agents` as the no-config fallback: rejected because it continues the mixed contract and keeps generating new `.agentsys` state after the project has already standardized on `.houmao`.
- Fail when no project config exists: rejected because zero-config local workflows still need a deterministic ambient default.

### Decision 2: `project init` respects the configured compatibility-projection root without making the projection canonical or mandatory

`project init` will keep writing the default config `agent_def_dir = "agents"` for brand-new overlays.

Base init still creates the catalog-backed overlay, project-local catalog, and managed content roots. It does not need to materialize `.houmao/agents/` only because init ran.

When `.houmao/houmao-config.toml` already exists, `project init` will:

- load the existing config,
- resolve `paths.agent_def_dir` relative to `.houmao/`,
- use that resolved path for compatibility validation,
- preserve existing auth bundles under that resolved compatibility-projection root,
- create optional `compatibility-profiles/` under that same resolved path when requested.

Alternatives considered:

- Always seed `.houmao/agents` and reject any existing config that points elsewhere: rejected because it contradicts the stated role of `houmao-config.toml` as the overlay discovery/config anchor for file-tree consumers.
- Rewrite an existing config back to `agent_def_dir = "agents"`: rejected because it silently discards operator intent.

### Decision 3: Retire maintained `.agentsys*` generated and scratch defaults

The retirement covers active maintained defaults, not just lookup strings.

The path-family changes are:

- run-local generated agent-definition trees in maintained demos move from `workdir/.agentsys/agents` to `workdir/.houmao/agents`;
- workspace-local no-config ambient lookup moves from `<cwd>/.agentsys/agents` to `<cwd>/.houmao/agents`;
- workspace-local fallback scratch directories that still use `.agentsys-*` move under `<working-directory>/.houmao/`;
- active docs, help text, and tests that still describe `.agentsys` fallback move to `.houmao`.

Manifest-adjacent turn-artifact roots that are already stable and Houmao-owned do not need to be reworked just to add another `.houmao/` segment.

Alternatives considered:

- Leave demo-generated trees under `.agentsys` because they are "only temporary": rejected because they are user-visible maintained defaults and part of the same naming contract.
- Leave `.agentsys-headless-turns`-style scratch names in place because they are internal-only: rejected because they still leak the retired path family into maintained active behavior and tests.

### Decision 4: Treat standalone `houmao-cli` build/start flows as deprecated compatibility surfaces, not primary operator workflows

The repository still carries `build-brain` and `start-session`, and they still influence live tests/help text. This change will update their ambient resolution and help text to match the `.houmao` fallback contract when they are invoked.

That does not make them first-class active operator workflows again. `houmao-mgr` and `houmao-server` remain the supported current surfaces; legacy runtime-local entrypoints stay in explicit compatibility/deprecation posture.

Alternatives considered:

- Drop the legacy entrypoints from scope entirely: rejected because their still-live help text and tests would continue to preserve `.agentsys`.
- Treat the legacy entrypoints as equal peers to `houmao-mgr`: rejected because that would contradict the repository's revised operator posture.

### Decision 5: Limit the retirement to active supported surfaces and active deprecation material

The implementation will update active code, maintained demos, current docs, and current tests. Historical material may still mention `.agentsys` when it is clearly archival.

Alternatives considered:

- Rewrite archived changes, review notes, and legacy demo documentation: rejected because it adds noise without changing the live product contract.

## Risks / Trade-offs

- [Risk] Users who still rely on ambient `.agentsys/agents` without CLI or env overrides will stop being discovered automatically. → Mitigation: treat the change as explicitly breaking, update docs/help text, and keep `AGENTSYS_AGENT_DEF_DIR` as an escape hatch during migration.
- [Risk] Re-running `project init` against a repo with a non-default `paths.agent_def_dir` changes which compatibility-projection root is validated or extended. → Mitigation: use the resolved configured path consistently in both status and init output so the selected location is explicit.
- [Risk] The path cleanup touches resolver code, deprecated compatibility CLI help, maintained demos, and tests, creating broad churn. → Mitigation: route path derivation through shared helpers where possible and validate the repo with grep-backed checks for leftover active `.agentsys*` references.
- [Risk] Docs cleanup could accidentally erase valid legacy/deprecation notes for `houmao-cli`. → Mitigation: keep those notes brief and explicit, but update their fallback precedence so they no longer preserve `.agentsys` as current behavior.
- [Trade-off] Environment variable names remain `AGENTSYS_*` even though the default path family becomes `.houmao`. → Mitigation: defer env-var renaming to a separate change so path retirement is isolated and tractable.

## Migration Plan

1. Update the OpenSpec requirements so `.houmao` becomes the normative ambient/default path family.
2. Change the shared project-aware resolver to use `<cwd>/.houmao/agents` as the no-config default.
3. Update pair-native build/launch consumers and deprecated standalone compatibility entrypoints so they all follow the same `.houmao` fallback contract.
4. Update `project init` to honor an existing configured `paths.agent_def_dir` value for the compatibility projection.
5. Rename maintained demo/generated/scratch path defaults off `.agentsys*`.
6. Refresh tests, help text, and current docs to match the new contract.

Operator migration is manual by design:

- move local content from `.agentsys/agents` to `.houmao/agents`, or
- create/update `.houmao/houmao-config.toml`, or
- use `AGENTSYS_AGENT_DEF_DIR` / `--agent-def-dir` explicitly.

Rollback is straightforward: restore the old fallback resolver and revert the matching docs/tests/spec updates.

## Open Questions

No blocking open questions remain for proposal-level implementation. This design intentionally keeps env-var names and tmux-published session metadata unchanged so the retirement is limited to path selection and default path ownership.
