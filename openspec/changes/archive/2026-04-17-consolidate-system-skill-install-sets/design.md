## Context

The implemented catalog and documentation work changed the system-skill install surface before the corresponding OpenSpec artifacts were updated. The prior specs describe many granular named sets (`mailbox-core`, `mailbox-full`, `user-control`, `agent-memory`, `agent-instance`, `utils`, and other single-purpose sets). The current implementation deliberately reduces that public set surface to two closed installable sets while keeping the packaged skill projection model flat and tool-native.

The same implementation added `houmao-utils-workspace-mgr`, a utility skill for planning and executing multi-agent workspace layouts before agents are launched. That skill is shipped as a top-level router plus `in-repo` and `out-of-repo` subskill pages instead of one large `SKILL.md`.

## Goals / Non-Goals

**Goals:**

- Make `core` and `all` the only installable named sets in the packaged catalog.
- Treat `automation`, `control`, and `utils` as documentation/catalog organization groups, not set names accepted by the installer.
- Keep managed homes utility-free by default through `managed_launch_sets = ["core"]` and `managed_join_sets = ["core"]`.
- Keep explicit CLI installation broad by default through `cli_default_sets = ["all"]`.
- Require installable sets to be closed over internal skill-routing references so an installed skill does not point at another catalog skill that is missing from the same set.
- Specify the new workspace-manager utility skill, including plan mode, execute mode, in-repo/out-of-repo subskills, submodule materialization, local-state symlink policy, launch-profile cwd updates, and optional memo-seed augmentation.
- Update README and system-skill guide requirements to match the current catalog.

**Non-Goals:**

- Preserve old granular set names as aliases. This change is intentionally breaking.
- Introduce nested or computed set expansion. Sets remain explicit ordered skill lists.
- Change the flat visible projection paths for Claude, Codex, Copilot, or Gemini.
- Launch agents from the workspace-manager skill. Workspace preparation remains separate from agent lifecycle skills.

## Decisions

### 1. Only `core` and `all` are installable named sets

The catalog exposes two named sets:

- `core`: all automation and operator-control skills that managed agents need for autonomous Houmao operation.
- `all`: `core` plus utility skills.

This removes the older granular public set surface. The older names were useful during incremental packaging, but they created fragile partial installs because skills can route to one another. A small closed set surface is easier to reason about and test.

### 2. Organization groups are documentation-only

Documentation may group skills as `automation`, `control`, and `utils`, but those labels are not accepted as `--skill-set` values. The catalog still stores an ordered flat inventory, and the installer only resolves named sets present in `[sets]`.

### 3. Managed defaults and CLI defaults intentionally differ

Managed launch and join install `core` to avoid placing general utility workflows into every managed runtime home. Explicit `houmao-mgr system-skills install` uses `all` when the operator omits both `--skill-set` and `--skill`, because an external tool home is usually being prepared for operator-directed work and should receive the complete packaged surface.

### 4. Set closure is a catalog invariant

Each installable set must include any catalog skill that another member references as an internal routing target. This invariant is verified by a regression test that scans Markdown content in the packaged skills for catalog skill identifiers. The test is intentionally conservative: if a set contains a skill whose docs point to another packaged skill, the referenced skill must also be in the same set.

### 5. Workspace management is a utility skill with explicit plan and execute modes

`houmao-utils-workspace-mgr` is included only through `all` or explicit skill selection. It must default to plan mode when the user has not clearly requested mutation. Execute mode mutates workspace files, worktrees, launch profiles, and optional memo seed files, but it does not launch agents.

### 6. Workspace flavors are split into subskill pages

The top-level workspace skill owns shared policy: mode selection, naming, local-state symlinks, submodule handling, shared repos, launch-profile edits, memo seeds, `workspace.md`, and guardrails. Flavor-specific layout and execution rules live in:

- `subskills/in-repo-workspace.md`
- `subskills/out-of-repo-workspace.md`

This keeps the main skill routable while allowing each workspace flavor to remain detailed.

### 7. Submodules use seeded worktrees by default

Large tracked submodules should be accessible inside each agent worktree without a fresh checkout, while still allowing agents to create branches, commit, and push normally inside the submodule. The default materialization mode is `seeded-worktree`: create a real Git worktree from the initialized source submodule, seed files from the source checkout without copying `.git` metadata, and put the agent on an agent-owned branch.

Operators may still choose `empty` or `checkout`, but `seeded-worktree` is the default when normal submodule Git behavior is needed without another large network checkout.

## Risks / Trade-Offs

- Removing old set names breaks scripts that pass `--skill-set user-control`, `--skill-set utils`, or similar values. The direct migration is to use `--skill-set core` for non-utility managed/control coverage or `--skill-set all` for the full packaged surface.
- The closure check can force broader installs than a purely minimal task would need. That is intentional: these are system skills with internal routing, and partial routability is worse than a slightly larger install.
- `seeded-worktree` submodule handling depends on the source checkout being initialized and locally available. If not, the plan must report that `checkout` or source initialization is required.

## Migration Plan

- Replace old catalog set constants and docs examples with `core` and `all`.
- Keep explicit single-skill installation available for narrow operator installs.
- Update system-skill list/install/status docs to show current named sets and current auto-install defaults.
- Update README and getting-started docs to include `houmao-utils-workspace-mgr`.
- Add or keep tests that verify catalog validity, docs consistency, and installable-set closure.

## Open Questions

None.
