## Context

The earlier project-aware roots change introduced shared helpers in [overlay.py](/data1/huangzhe/code/houmao/src/houmao/project/overlay.py) for:

- resolving the active overlay without filesystem mutation
- ensuring or bootstrapping the active overlay when local state is needed
- deriving overlay-local defaults for agents, runtime, jobs, mailbox, and easy state

Most maintained command families were moved onto that contract, but [project.py](/data1/huangzhe/code/houmao/src/houmao/srv_ctrl/commands/project.py) still contains many direct `_require_project_overlay()` call sites. Those commands now lag behind the contract that the rest of the CLI follows.

The remaining inconsistency is not uniform. Some `project` subcommands create new local state and should bootstrap the active overlay when it is missing. Others inspect, remove, or stop existing state and should stay non-creating. The unfinished 4.1 work is to encode that distinction explicitly instead of treating the whole `project` family as one bucket.

## Goals / Non-Goals

**Goals:**

- Route maintained `houmao-mgr project ...` subcommands through the shared project-aware resolver instead of direct `_require_project_overlay()` gating.
- Define one explicit command classification for project subcommands:
  - ensure-and-bootstrap for create or materialize flows
  - resolve-only for inspection, removal, and existing-runtime ownership checks
- Remove stale missing-overlay messaging that implies `houmao-mgr project init` is always a mandatory prerequisite.
- Preserve the already-implemented ensure behavior for `project easy specialist create` and `project easy instance launch`.
- Add focused tests for missing-overlay behavior across the maintained `project` families still audited under 4.1.

**Non-Goals:**

- Redesign overlay precedence, runtime-root defaults, mailbox defaults, or jobs placement again.
- Expand the scope beyond maintained `houmao-mgr project ...` and project-managed easy flows.
- Add new per-command overlay flags or new config schema.
- Change `project status`, which already has its own read-only behavior.

## Decisions

### Decision: Introduce explicit project-command overlay access modes

`project.py` will use two internal overlay access modes instead of relying on `_require_project_overlay()` as the default:

- **ensure mode**: resolve the active overlay through `ensure_project_aware_local_roots()` and bootstrap it when missing
- **resolve-only mode**: resolve selection state through `resolve_project_aware_local_roots()` and fail clearly when no overlay exists

Rationale:

- The shared project-aware contract already exposes both behaviors.
- The unfinished commands differ by intent, not by root-selection algorithm.
- Making the access mode explicit at the command-family layer is smaller and clearer than teaching each command its own fallback rules.

Alternative considered:

- Convert every remaining `project` command to ensure mode.
- Rejected because removal, inspection, and stop flows would create empty overlays just to report that the requested project-local state does not exist.

### Decision: Bootstrap only creation or materialization flows

Maintained project-local flows that create or update local state in a way that remains meaningful against a newly bootstrapped overlay will use ensure mode. This includes at minimum:

- tool setup add
- tool auth add and set
- role init and scaffold
- role preset add
- easy specialist create
- easy instance launch

Rationale:

- These commands can sensibly create the overlay as part of their primary work.
- This matches the "no manual `project init` prerequisite" goal from the earlier roots change.

Alternative considered:

- Keep add or set flows in resolve-only mode because they may also validate existing project content.
- Rejected because the commands already define how to create their target state and do not benefit from a separate bootstrap step.

### Decision: Keep inspection, removal, and runtime-ownership checks non-creating

Maintained project-local flows that inspect existing project state, remove existing project state, or verify runtime ownership will use resolve-only mode. This includes at minimum:

- tool get
- tool setup list, get, remove
- tool auth list, get, remove
- role list, get, remove
- role preset list, get, remove
- easy specialist list, get, remove
- easy instance list, get, stop

When no overlay exists, these commands will fail clearly without bootstrapping a new overlay.

Rationale:

- Creating an empty overlay is not helpful for "show me what exists", "remove this existing thing", or "stop this existing instance" commands.
- This keeps project inspection and destructive flows consistent with the read-only intent already preserved for `project status`.

Alternative considered:

- Return empty payloads for missing overlays on list-style commands.
- Rejected because it would blur the difference between "no project overlay exists" and "the project overlay exists but currently contains no matching state."

### Decision: Replace "run project init first" error guidance with command-accurate missing-overlay messaging

Resolve-only project commands will no longer rely on the generic `require_project_overlay()` message that instructs operators to run `houmao-mgr project init` first.

Instead, the project command layer will surface a missing-overlay error that:

- identifies the selected or would-bootstrap overlay root
- states that the current command did not create it implicitly
- avoids claiming that `project init` is the only valid next step

Rationale:

- After the earlier project-aware roots change, `project init` is no longer the universal prerequisite for maintained local workflows.
- Command-accurate messaging reduces confusion for operators who can use a create or launch flow to bootstrap when appropriate.

Alternative considered:

- Keep the existing generic error text for all resolve-only paths.
- Rejected because it contradicts the current maintained workflow contract.

### Decision: Keep the work isolated to `project.py` call sites and project CLI tests

This follow-up will rely on the shared overlay helpers already added in `overlay.py` rather than introducing another layer of root-resolution logic.

Implementation work should stay centered in:

- [src/houmao/srv_ctrl/commands/project.py](/data1/huangzhe/code/houmao/src/houmao/srv_ctrl/commands/project.py)
- [tests/unit/srv_ctrl/test_project_commands.py](/data1/huangzhe/code/houmao/tests/unit/srv_ctrl/test_project_commands.py)

Rationale:

- The shared resolver already exists and is the correct abstraction boundary.
- Constraining the change reduces the chance of reopening the broader root-layout work.

## Risks / Trade-offs

- [Command classification drift] → Encode the bootstrap-vs-resolve distinction in small shared helpers so future `project` subcommands opt into one explicit mode.
- [Overlapping active OpenSpec changes on the same capability] → Keep this follow-up narrowly scoped to the remaining 4.1 audit and avoid re-specifying the broader root-layout contract.
- [Operators may still expect empty results from list commands] → Fail clearly on missing overlays so "overlay absent" stays distinct from "overlay present but empty."
- [Error text changes may require test updates beyond one command group] → Update the shared project CLI tests at the same time as the helper changes instead of relying on incidental string matches.
