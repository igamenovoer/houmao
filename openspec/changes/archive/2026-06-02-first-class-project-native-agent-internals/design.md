## Context

Houmao currently has two overlapping authoring layers:

- a low-level file-tree agent-definition layer aligned with native provider launch concepts,
- a higher-level project/easy layer that stores specialists, easy profiles, credentials, skills, and launch defaults in the project catalog and managed content roots.

Ordinary users mostly use the project/easy path, but the CLI still presents `project easy` as a convenience wrapper and keeps low-level `project agents ...` command groups beside it. That makes "agent", "profile", "launch profile", and "agent definition" ambiguous in docs, system skills, command templates, and generated config drafts.

The filesystem model has a second ambiguity: local project overlays use `.houmao`, and the shared registry also defaults under `~/.houmao`. Once project discovery walks ancestors, a home-level `~/.houmao` can look like an accidental project candidate for nested workspaces.

## Goals / Non-Goals

**Goals:**

- Make Houmao project the ordinary required context for maintained local Houmao workflows.
- Promote the existing high-level `project easy` workflows to first-class `project` command groups.
- Move low-level provider-aligned authoring to `houmao-mgr internals native-agent`.
- Adopt clear terminology:
  - project layer: specialist, profile, managed agent / agent instance,
  - internal layer: native agent, recipe, role, launch dossier.
- Move the default shared registry root to the platformdirs user config root while preserving `HOUMAO_GLOBAL_REGISTRY_DIR`.
- Update system skills, command templates, config drafts, docs, and tests so agents learn the new vocabulary.

**Non-Goals:**

- Preserving the old public `project easy` or `project agents <raw>` command paths as ordinary supported aliases.
- Migrating or deleting legacy `~/.houmao` shared registry data automatically.
- Removing the native-provider compatibility layer. It remains useful because provider CLIs do not understand Houmao specialists directly.
- Redesigning the project catalog schema beyond the fields needed to present and project the renamed concepts.

## Decisions

### Decision: Promote project/easy commands instead of creating a new top-level command

Promote the existing rich commands into the `project` family:

- `project easy specialist ...` becomes `project specialist ...`
- `project easy profile ...` becomes `project profile ...`
- `project easy instance ...` becomes a project-scoped managed-agent lifecycle group, with exact naming chosen during implementation from the existing `project agents` collision constraints.

Alternative considered: introduce a separate `houmao-mgr specialists` top-level family. That would make project less central and would keep the old "project is optional collection area" feeling.

### Decision: Move low-level file-tree material to `internals native-agent`

Direct role, recipe, tool setup, and launch dossier commands belong under:

```text
houmao-mgr internals native-agent ...
```

Direct native-agent commands resolve a native-agent root through explicit `--native-agent-root` or `HOUMAO_NATIVE_AGENT_ROOT`. They do not discover or bootstrap a Houmao project. Project commands may still materialize native-agent projections internally when provider launch code needs file-tree material.

Alternative considered: place these under `project internals`. That was rejected because native provider material is intrinsically below projects, not inside the project model.

### Decision: Treat missing project as an error for ordinary stateful workflows

Only `project init` creates a project. `project status` and related inspection may report that no project is active, but ordinary stateful commands fail with initialization guidance instead of bootstrapping `<cwd>/.houmao`.

Alternative considered: keep auto-bootstrap for create/launch commands. That preserves convenience but conflicts with first-class project semantics and makes accidental project creation too easy.

### Decision: Use platformdirs user config as the shared Houmao anchor

`resolve_houmao_home_root()` should stop deriving `Path.home() / ".houmao"` from platformdirs. The shared default should be the platformdirs user config path for `houmao`, expected as `~/.config/houmao` on Linux. The registry default becomes `<config-root>/registry`.

Project overlays remain repo-local `.houmao` directories. This keeps `.houmao` meaning "project overlay" instead of "global shared home".

Alternative considered: rename project overlays away from `.houmao`. That would be a much larger migration with less immediate value than moving the global shared root.

### Decision: Keep internal persisted compatibility names stable where harmless

Public CLI/docs/output should use profile and launch dossier terminology, but some internal lane names may remain stable during the first implementation pass if changing them would churn catalog storage without user benefit. Any retained names must be hidden behind project-layer renderers and not leak into ordinary command help.

Alternative considered: rename every internal field immediately. That is cleaner but raises migration risk and distracts from the user-facing model.

## Risks / Trade-offs

- Old docs and skills may keep teaching retired paths -> update packaged skills, README, reference docs, command templates, and config drafts in the same change.
- Removing auto-bootstrap may make first use feel stricter -> error messages should name `houmao-mgr project init` and the selected/discovered overlay context.
- Native-agent root resolution may feel verbose -> keep it internal and make project commands the ordinary path.
- Platformdirs path differs by OS -> tests should monkeypatch platformdirs output and assert behavior by function, not by assuming Linux paths everywhere.
- Legacy `~/.houmao` registry records become invisible by default -> document the change and preserve `HOUMAO_GLOBAL_REGISTRY_DIR` for operators who need the old path temporarily.

## Migration Plan

1. Introduce terminology helpers and path constants for project terms, native-agent terms, and platformdirs config roots.
2. Refactor CLI registration:
   - promote project specialist/profile/lifecycle groups,
   - move native file-tree groups under `internals native-agent`,
   - remove `easy` from public help.
3. Change project resolution so ordinary stateful flows require an active project, with explicit `project init` as the creation path.
4. Update project projection code so catalog-backed project resources still materialize native-agent file trees for provider launch internals.
5. Change the shared registry default to the platformdirs user config root and update docs/tests.
6. Update command templates, config drafts, system skills, and docs.
7. Run full lint, typecheck, unit tests, OpenSpec validation, and focused CLI shape tests.

Rollback is code-level: revert the command-tree and path-default changes before publishing a stable release. Do not auto-migrate legacy registry data during rollout, so rollback does not need to move user files back.

## Open Questions

- Should the promoted project lifecycle group be `project agents` or `project instance`? `project agents` reads naturally for managed agents, but currently collides with the old raw subtree.
- Should `HOUMAO_AGENT_DEF_DIR` be accepted with a deprecation warning for one release, or removed immediately in favor of `HOUMAO_NATIVE_AGENT_ROOT`?
- Should packaged skill names change now, or should existing skill ids stay as compatibility entrypoints that route to the new terminology?
