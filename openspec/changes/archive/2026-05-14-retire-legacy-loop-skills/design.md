## Context

The current system-skill inventory exposes multiple loop-authoring paths:

- stable tree-loop package: `houmao-agent-loop-pairwise`;
- enriched variants: `houmao-agent-loop-pairwise-v2`, `v3`, `v4`;
- generated-execplan predecessor: `houmao-agent-loop-pairwise-v5`;
- graph-oriented package: `houmao-agent-loop-generic`;
- current consolidated package: `houmao-agent-loop-pro`.

`houmao-agent-loop-pro` already has topology modes for `tree-loop` and `generic-loop`, staged execplan generation, generated agent/workspace/validation/launch stages, mail-schema event guidance, and the mail-notifier runtime model. The older package names now create a fragmented authoring surface and make managed homes install several loop skills whose responsibilities overlap.

One deployment detail matters: removing names from the current catalog is not enough. Existing tool homes may already contain symlinks or copied directories for legacy loop skills. If those paths remain, agents can still discover and invoke retired packages even after a new install.

## Goals / Non-Goals

**Goals:**

- Make `houmao-agent-loop-pro` the only current packaged loop-authoring and generated-loop execution skill.
- Retire pairwise-named and generic loop packages from current install inventory, managed auto-install, docs, examples, and routing guidance.
- Preserve retired loop skill source trees in a source-only legacy reference directory under `src/`.
- Clean known retired Houmao loop skill paths from managed/project tool homes during supported system-skill operations.
- Preserve useful concepts in pro: `tree-loop`, `generic-loop`, legacy topology aliases, graph helper usage, mail-driven runtime model, and generated execplan stages.
- Keep historical archived OpenSpec changes intact.

**Non-Goals:**

- Do not remove low-level graph helper commands such as `houmao-mgr internals graph high`.
- Do not rewrite old archived changes or historical context logs.
- Do not migrate existing authored loop-plan directories into pro execplan directories automatically.
- Do not provide compatibility wrapper skills or supported installer routes under retired names.
- Do not remove elemental local-close, relay, notifier, mailbox, gateway, or workspace-manager patterns that pro can still compose.

## Decisions

### 1. Pro is the only current loop skill

`src/houmao/agents/assets/system_skills/catalog.toml` should declare `houmao-agent-loop-pro` as the current loop skill and include it in `core` and `all`. The retired loop packages should be removed from current `[skills]` entries and install sets.

Alternative considered: keep `houmao-agent-loop-generic` alongside pro. Rejected because the user direction is to keep only the pro version, and pro already owns generic-loop topology mode.

### 2. Retired names are explicit cleanup targets

The system-skill catalog or loader should know the retired loop skill names:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-pairwise-v4`
- `houmao-agent-loop-pairwise-v5`
- `houmao-agent-loop-generic`

Supported install, reinstall, status, and uninstall workflows should treat these as known retired Houmao-owned paths, not as arbitrary user skills. A current install should remove these exact projection paths from the selected tool home while installing pro. Status should be able to report retired leftovers when present. Uninstall should remove current Houmao skills and known retired Houmao loop skill paths.

Alternative considered: rely on current installer behavior that preserves unrecognized or legacy paths. Rejected because it leaves retired loop skills discoverable after a nominal upgrade.

### 3. Move retired package assets to a source-only legacy directory

The retired package directories under `src/houmao/agents/assets/system_skills/` should move to a legacy reference directory under `src/`, such as `src/houmao/agents/assets/system_skills/legacy/`.

The legacy directory is not a packaged skill source. It should not be referenced by `catalog.toml`, project-scope symlinks, current docs, current routing guidance, or generated managed homes. It exists only for repository reference and for users who intentionally choose to manually handle old skill material outside the supported installer path.

Alternative considered: delete retired assets entirely. Rejected because the old skills still have reference value and may be useful to users who manually opt into unsupported legacy material.

Alternative considered: leave retired assets in the current asset root but unregistered. Rejected because flat current roots make it easy for project-scope symlink scripts and humans to accidentally re-expose old skills.

### 4. Pro absorbs documentation routes, not old package names

Docs should describe loop authoring as:

```text
houmao-agent-loop-pro
├── topology: tree-loop
└── topology: generic-loop
```

Docs may mention `pairwise` only as legacy terminology or as a graph-tool mode alias. They should not present old package names as current choices.

Alternative considered: document old names as deprecated transition paths. Rejected because that keeps the selection burden and undermines the single-skill goal.

### 5. Graph tooling remains, wording changes

`houmao-mgr internals graph high` remains useful for pro authoring and validation. Existing mode names such as `pairwise-v2` can remain as compatibility aliases or examples where they reflect current CLI behavior, but docs should explain that pro is the consuming loop skill.

Alternative considered: remove pairwise-v2 graph tooling. Rejected because the graph helpers are deterministic utilities, not loop skills, and pro can use them while generating or validating topology-derived artifacts.

### 6. Specs should mark retired capabilities explicitly

Current specs for pairwise/generic loop skills should stop requiring those packages to be current installable skills. Their delta specs should state the retirement requirement rather than silently deleting history. The pro and system-skill specs should become the current source of truth for loop skill availability.

Alternative considered: remove old spec files outright. Rejected because OpenSpec history and sync flows work better when behavior changes are expressed as requirement deltas.

## Risks / Trade-offs

- [Existing homes keep stale copied skills] -> Add known-retired cleanup behavior to system-skill install/status/uninstall and update project-scope symlinks.
- [Users invoke old skill names from memory] -> Fail clearly through absence from current inventory and route current docs/touring to `houmao-agent-loop-pro`.
- [Docs lose concrete pairwise-v2 recovery examples] -> Keep legacy runtime-file references only where needed, labeled as legacy; explain current pro-generated loops define their own generated state contracts.
- [OpenSpec specs become noisy] -> Limit deltas to current capability specs and leave archived changes untouched.
- [Graph docs still contain `pairwise-v2`] -> Reframe those as graph helper modes or legacy aliases rather than current skill names.

## Migration Plan

1. Add `houmao-agent-loop-pro` to the current packaged catalog and install sets.
2. Add known-retired loop skill cleanup metadata and installer/status/uninstall handling.
3. Remove retired loop skill entries from the catalog and remove retired asset directories.
4. Move retired loop skill source trees to the source-only legacy reference directory.
5. Remove project-scope symlinks for retired loop skills and keep the pro symlink.
6. Update docs, touring, advanced-usage routing, examples, and current specs.
7. Update tests to assert pro-only loop skill availability, source-only legacy preservation, and retired-path cleanup behavior.

Rollback is straightforward before release: move legacy source trees back to the current asset root, restore retired catalog entries, remove the retired cleanup list, and restore tests/docs that enumerate the older loop packages.

## Open Questions

- Should the known-retired cleanup list live in `catalog.toml` with schema support, or as code-owned constants in the system-skill installer? The catalog is preferable as the skill inventory source of truth.
- Should `houmao-mgr system-skills status` expose retired leftovers in plain output, JSON output, or both? JSON should expose them; plain output can summarize when present.
