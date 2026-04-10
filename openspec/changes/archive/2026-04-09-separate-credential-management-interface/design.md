## Context

Houmao already has two credential storage models, but only one of them has a supported management surface.

- Active project overlays store credentials as catalog-backed auth profiles with mutable display names and opaque bundle refs.
- Plain agent-definition directories store credentials directly as named directories under `tools/<tool>/auth/<name>/`.

The current CLI exposes credential CRUD only through `houmao-mgr project agents tools <tool> auth ...`, which mixes credential management into the low-level tool-projection subtree and leaves plain agent-definition directories without a supported credential-management interface. The current skill and documentation surface also reinforce that project-only nested routing even though the rest of Houmao already recognizes agent-definition directories as a separate source lane.

This change is cross-cutting because it affects the top-level `houmao-mgr` command tree, the `project` view, shared credential write helpers, skill guidance, and CLI/docs routing.

## Goals / Non-Goals

**Goals:**

- Introduce a first-class credential-management interface that is separate from `project agents tools`.
- Support credential management for both active project overlays and plain agent-definition directories.
- Preserve catalog-backed identity semantics for project-overlay credentials.
- Reuse one shared tool-contract layer for Claude, Codex, and Gemini env/file validation across both backends.
- Make the operator-facing command shape concern-oriented (`credentials`) instead of projection-oriented (`project agents tools ... auth`).

**Non-Goals:**

- Change per-tool credential payload contracts such as supported env vars, auth files, or clear flags.
- Convert plain agent-definition directories into catalog-backed storage.
- Add automatic credential discovery, credential import from ambient homes, or login-generation workflows.
- Preserve the old `project agents tools <tool> auth ...` subtree as a maintained public workflow.

## Decisions

### 1. Add `houmao-mgr credentials` as the canonical credential-management family

The CLI will add a new top-level family:

```text
houmao-mgr credentials <tool> list|get|add|set|rename|remove
```

The supported tool lanes remain:

- `claude`
- `codex`
- `gemini`

Why:

- credentials are a first-class operator concern and should not look like a subdirectory-maintenance detail,
- the same credential concern exists for both project overlays and plain agent-definition dirs,
- a top-level family matches how `mailbox` exposes a concern-oriented operator surface outside `project`.

Alternatives considered:

- Keep credential CRUD only under `project agents tools <tool> auth ...` and add a second unrelated direct-dir command.
  Rejected because it would preserve split ownership and keep credentials looking like tool-tree maintenance.
- Add only `project credentials ...` without a top-level `credentials` family.
  Rejected because it would still leave plain agent-definition-dir management without a clear canonical home.

### 2. Add `houmao-mgr project credentials` as an explicit project-scoped wrapper

`houmao-mgr project` will gain:

```text
houmao-mgr project credentials <tool> list|get|add|set|rename|remove
```

This wrapper will always resolve through the active project overlay and will delegate to the same shared credential action handlers used by the top-level family.

Why:

- it preserves the existing `project` family as the explicit local-overlay entry point,
- it gives operators a non-ambiguous project-only spelling when they do not want automatic target resolution,
- it keeps the project tree symmetric with other concern-oriented wrappers such as `project mailbox`.

Alternatives considered:

- Expose only the top-level `credentials` family.
  Rejected because `project` is already an important explicit local-state view and credential management belongs there as well.

### 3. Use one command surface with two storage backends

The new credential interface will resolve one target and then route to one of two backends:

```text
credentials command
       |
       v
 target resolution
   /           \
  v             v
project backend direct-dir backend
catalog-backed  filesystem-backed
```

Project backend:

- source of truth is `ProjectCatalog`,
- `add|set|get|list|rename|remove` keep the existing display-name and bundle-ref semantics,
- rename remains metadata-only.

Direct-dir backend:

- source of truth is `tools/<tool>/auth/<name>/`,
- `add|set|get|list|remove` operate directly on the named auth directory,
- rename is a filesystem rename plus maintained reference rewrites in the selected agent-definition directory.

Why:

- Houmao already has both storage models,
- the operator-facing action vocabulary is the same across both,
- the backend split avoids forcing catalog semantics onto plain agent-definition dirs just to expose management commands.

Alternatives considered:

- Force all credential management through project overlays only.
  Rejected because the user specifically needs management for plain agent-definition dirs too.
- Add a catalog to every plain agent-definition dir.
  Rejected because that is a much larger architectural change than the interface problem being solved here.

### 4. Target resolution prefers explicit input and detects overlay-managed compatibility trees

For `houmao-mgr credentials ...`, target resolution will use this order:

1. explicit `--agent-def-dir`
2. explicit `--project`
3. `HOUMAO_AGENT_DEF_DIR`
4. active project-overlay discovery
5. otherwise fail with a clear target-resolution error

If an explicit or env-provided agent-definition directory resolves to the compatibility projection owned by a valid project overlay, the command will promote that target to the project backend rather than treating it as a plain directory backend.

`houmao-mgr project credentials ...` skips this ambiguity and always resolves the active project overlay.

Why:

- explicit input should win,
- `HOUMAO_AGENT_DEF_DIR` is already part of Houmao's maintained agent-definition resolution model,
- overlay-managed `agents/` directories must keep catalog-backed semantics even if addressed through an agent-def path.

Alternatives considered:

- Treat every `--agent-def-dir` literally as a direct-dir backend.
  Rejected because pointing at `.houmao/agents` would silently bypass the catalog-backed auth model and produce the wrong rename semantics.

### 5. Extract one shared credential payload engine and keep backend-specific persistence separate

The implementation will split the current project-only credential helpers into:

- shared request validation and temporary-tree mutation logic,
- backend-specific persistence and listing/lookup operations.

The shared layer will continue to derive the supported env/file contract from each tool's adapter so both backends enforce the same tool-specific flags and validation rules.

Why:

- the current project-only auth writers already do most of the useful normalization and validation,
- duplicating tool-specific env/file handling for direct dirs would create drift,
- backend differences are mostly about persistence and rename behavior, not about tool contracts.

Alternatives considered:

- Duplicate the existing project credential logic into a second direct-dir implementation.
  Rejected because it would create avoidable divergence across Claude, Codex, and Gemini handling.

### 6. Plain-directory rename will rewrite maintained in-tree references explicitly

For the direct-dir backend, `rename` will:

1. rename `tools/<tool>/auth/<old>/` to `tools/<tool>/auth/<new>/`,
2. rewrite maintained YAML references under the selected agent-definition directory that store `auth: <old>` for that tool,
3. report the renamed path plus the rewritten files.

The maintained rewrite scope is:

- `presets/*.yaml`
- `launch-profiles/*.yaml`

It does not attempt to rewrite arbitrary prose, tests, or external scripts.

Why:

- plain agent-definition directories still use directory basenames as auth identity,
- recipes and launch profiles are the maintained semantic references that must stay in sync,
- explicit rewritten-file reporting makes the behavioral difference from project rename visible.

Alternatives considered:

- Make direct-dir rename unsupported.
  Rejected because the action vocabulary should remain symmetrical across backends when practical.
- Try to scan and rewrite every possible textual reference in the repo.
  Rejected because that is unbounded and brittle.

### 7. `project agents tools` stops owning credential CRUD

`project agents tools <tool>` will remain the low-level tool-tree maintenance surface for:

- `get`
- `setups ...`

It will no longer own `auth ...` CRUD as part of the maintained command tree. Credential ownership moves to `credentials ...` and `project credentials ...`.

Why:

- this draws a cleaner responsibility boundary,
- it matches the docs and skill direction that credentials are their own concern,
- it reduces the mismatch between catalog-owned credential identity and projection-tree-oriented CLI shape.

Alternatives considered:

- Keep both old and new command families long-term.
  Rejected because duplicate ownership would make docs, skills, and test coverage harder to keep coherent.

## Risks / Trade-offs

- [Two backends have different rename semantics] → Make the distinction explicit in specs, help text, and command output; project rename preserves identity, direct-dir rename rewrites maintained references.
- [Target resolution could be surprising when both project and agent-def-dir context exist] → Prefer explicit selectors, document the precedence, and auto-detect overlay-managed compatibility trees.
- [Hard-cut removal of `project agents tools <tool> auth ...` breaks existing scripts and docs] → Update maintained skills, CLI docs, and tests in the same change.
- [Direct-dir rename could miss non-maintained references] → Limit rewrites to maintained YAML resources and report the rewritten files; do not claim broader repo-wide rewrite semantics.
- [Shared credential helper extraction touches multiple command paths] → Keep backend persistence boundaries small and reuse existing project credential tests as the contract anchor.

## Migration Plan

This is a repo-wide hard cut for the maintained operator surface.

1. Add `credentials ...` and `project credentials ...`.
2. Move credential action handlers onto the shared/backend-split implementation.
3. Remove maintained auth CRUD from `project agents tools <tool>`.
4. Update skills, docs, and tests to use the new command families.

No credential data migration is required for project overlays because storage stays catalog-backed.

No storage migration is required for plain agent-definition directories because the new interface manages the existing directory layout directly.

Rollback is out of scope; the repo should converge on the new credential command families rather than carrying parallel maintained surfaces.

## Open Questions

- None for proposal scope. The main design choices are settled: separate credential command family, explicit project wrapper, dual backend implementation, and hard-cut routing away from `project agents tools <tool> auth ...`.
