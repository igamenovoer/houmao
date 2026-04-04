## Context

`make-operations-project-aware` made maintained local command flows derive `agents/`, `runtime/`, `jobs/`, and `mailbox/` from the active overlay by default. The supported demo surface still contains older wiring that predates that contract:

- `scripts/demo/minimal-agent-launch/` exports separate `HOUMAO_AGENT_DEF_DIR` and `HOUMAO_GLOBAL_RUNTIME_DIR` values even though its generated run tree already has a natural `.houmao/` anchor.
- `single-agent-mail-wakeup` already selects a redirected overlay through `HOUMAO_PROJECT_OVERLAY_DIR`, but it still exports separate agent-definition, runtime, and jobs overrides while describing runtime and jobs as sibling output-root directories.

That makes the maintained demo surface teach a more complicated local-root story than the live CLI contract now requires.

## Goals / Non-Goals

**Goals:**

- Reduce maintained demo root wiring to the smallest set of overrides still required for the supported workflows.
- Make `minimal-agent-launch` use one generated overlay root as the source of truth for local Houmao-owned state.
- Make `single-agent-mail-wakeup` keep using its redirected overlay root, but let runtime, jobs, and mailbox default under that overlay unless a remaining explicit isolation need still exists.
- Update demo docs, output-layout descriptions, and focused tests together with the runner or helper changes.

**Non-Goals:**

- Change general CLI root-resolution semantics again.
- Repair or modernize archived `scripts/demo/legacy/` material.
- Remove explicit registry isolation where a supported demo still needs it to avoid cross-run or cross-project collisions.
- Expand this change into unrelated docs or non-demo helper surfaces.

## Decisions

### Decision: `minimal-agent-launch` will keep one explicit overlay selector, not separate root env overrides

The minimal demo will switch from exporting separate `HOUMAO_AGENT_DEF_DIR` and `HOUMAO_GLOBAL_RUNTIME_DIR` values to selecting one generated overlay root for the run, using `HOUMAO_PROJECT_OVERLAY_DIR=<run-root>/workdir/.houmao`.

The runner may continue launching from the repository root, but the selected generated overlay becomes the single local-state anchor for:

- `agents/`
- `runtime/`
- `jobs/`
- any future overlay-local defaults the maintained launch path consumes

Rationale:

- The demo already generates its canonical agent tree under `workdir/.houmao/agents`.
- A single explicit overlay selector keeps the runner robust even when `--output-dir` points outside the repository tree.
- This removes the redundant root-env split while preserving deterministic run-local placement.

Alternative considered:

- Drop all root env vars and rely only on the current working directory.
- Rejected because the runner supports custom output roots that may live outside the repository tree, and the demo should not depend on `pixi` or CLI discovery from an arbitrary external cwd.

### Decision: `single-agent-mail-wakeup` will keep overlay selection and isolated registry, but drop redundant local-root overrides

The wake-up demo will keep:

- `HOUMAO_PROJECT_OVERLAY_DIR=<output-root>/overlay`
- explicit demo-local registry isolation

It will stop exporting separate agent-definition, runtime, and jobs overrides solely to keep the workflow self-contained. Runtime, jobs, and mailbox will instead derive from the redirected overlay as:

- `<output-root>/overlay/runtime`
- `<output-root>/overlay/jobs`
- `<output-root>/overlay/mailbox`

Rationale:

- The demo already uses a redirected overlay as its project-local authority.
- Registry is the one shared default root that still needs an explicit demo-local override to avoid global collision.
- Dropping the other root env vars aligns the demo with the contract the CLI now implements.

Alternative considered:

- Preserve sibling `runtime/` and `jobs/` directories under the output root and keep explicit env overrides.
- Rejected because those overrides no longer express a true behavioral need; they only preserve an older layout that the new contract makes unnecessary.

### Decision: Demo specs and docs will describe only intentionally retained overrides

The updated demo docs and capability specs will describe:

- which override is still required and why
- which local roots now come from overlay-local defaults
- the resulting generated output layout

They will stop teaching root env vars that are only historical implementation detail.

Rationale:

- The maintained demo surface is part of the operator story.
- Leaving stale env-var scaffolding in tutorial text would undercut the project-aware defaulting work.

### Decision: Shared TUI tracking remains out of scope for this follow-up

Although `shared-tui-tracking-demo-pack/` is a supported demo surface, it is not currently using the redundant multi-root env override pattern that 4.5 is targeting.

Rationale:

- Keeping the change scoped to the demos that actually still carry the old root split makes the follow-up smaller and easier to validate.

## Risks / Trade-offs

- [Output-path churn for demo artifacts] → Update README/tutorial output descriptions, expected reports, and focused tests in the same change so the new layout is explicit.
- [Operators may rely on old sibling `runtime/` or `jobs/` paths for ad hoc inspection] → Keep the generated state under the same run root and document the new overlay-local paths clearly.
- [Registry isolation could be removed accidentally while simplifying env wiring] → Treat demo-local registry override as an explicit retained requirement in the wake-up demo.
- [Minimal demo could become sensitive to caller location] → Keep one explicit overlay selector for that runner rather than relying purely on cwd-based discovery.
