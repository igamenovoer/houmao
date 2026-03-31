## Why

Houmao currently splits local state across multiple default roots: project overlays own catalog and agent-definition content, runtime defaults remain shared under `~/.houmao/runtime`, jobs default under `<working-directory>/.houmao/jobs`, and generic mailbox/admin/server flows often remain outside the project-aware path model. That split forces operators and demos to export several environment variables to keep one workflow self-contained, and it makes "project-aware" behavior inconsistent across command families.

We want one maintained local model: when a Houmao command runs in project context, it should resolve or bootstrap one active project overlay and keep local Houmao-owned state there by default. The only shared default root that remains global should be the live-agent registry.

## What Changes

- **BREAKING** redefine local default-root ownership so the active project overlay owns local Houmao state by default: `agents/`, `runtime/`, `jobs/`, `mailbox/`, `easy/`, catalog, and managed content all live under the selected overlay root.
- **BREAKING** keep only the shared registry under `~/.houmao/registry` by default, unless the existing registry env override redirects it.
- **BREAKING** make local Houmao command flows project-aware by default through one common overlay-selection contract: explicit CLI override, `HOUMAO_PROJECT_OVERLAY_DIR`, nearest discovered project overlay within the current Git worktree boundary, then auto-bootstrap when no overlay exists.
- **BREAKING** remove the requirement that operators run `houmao-mgr project init` before local project-aware launch, build, mailbox, runtime-maintenance, or server-management workflows can create local Houmao state.
- Extend project-aware defaulting beyond `project ...` commands so generic local command families such as `brains`, `agents launch`, mailbox administration, runtime cleanup, and server lifecycle align with the same overlay-local root contract.
- Preserve shared-registry discovery semantics so global `agents ...` resolution still works across projects via absolute registry pointers into overlay-local manifests.

## Capabilities

### New Capabilities

- `project-aware-local-roots`: Define one maintained cross-command contract for selecting, bootstrapping, and using an active project overlay as the default local root for Houmao-owned state other than the shared registry.

### Modified Capabilities

- `houmao-owned-dir-layout`: Change default root ownership so runtime, jobs, and mailbox default under the active project overlay while registry remains the only shared default root.
- `houmao-mgr-project-cli`: Change overlay selection and bootstrap semantics from explicit `project init` setup to common ensure-or-create project-aware defaults, with CLI/env/discovery/bootstrap precedence.
- `houmao-mgr-project-easy-cli`: Change easy specialist and instance workflows so they operate correctly without prior manual project bootstrap and use overlay-local runtime and jobs roots by default.
- `houmao-mgr-agents-launch`: Change local `agents launch` defaults so project-aware launches build and start under overlay-local roots rather than shared runtime roots.
- `brain-launch-runtime`: Change local build/start runtime defaults so project-context brain homes, manifests, session roots, and job dirs derive from the active overlay instead of shared or working-directory split defaults.
- `houmao-mgr-mailbox-cli`: Change generic mailbox administration defaults so project-context mailbox operations target the active overlay mailbox root unless explicitly overridden.
- `houmao-mgr-cleanup-cli`: Change runtime cleanup defaults so project-context cleanup targets overlay-local runtime and jobs state by default while registry cleanup remains shared-root aware.
- `houmao-mgr-server-group`: Change server lifecycle defaults so project-context server runtime artifacts derive from the active overlay rather than the shared runtime root when no explicit runtime-root override is supplied.

## Impact

- Affected code spans project overlay discovery/bootstrap, root resolution helpers, local launch/build flows, mailbox command defaults, cleanup commands, and server lifecycle defaults.
- The change is intentionally breaking for local path defaults, command side effects, and operator expectations around `~/.houmao/runtime`, `<working-directory>/.houmao/jobs`, and pre-bootstrapped project overlays.
- Documentation and workflow artifacts that currently describe runtime/jobs/mailbox as separate default root families will need updates.
- Existing shared-registry behavior remains central to cross-project discovery, so global name ambiguity and registry-wide visibility continue to exist by design.
