## Context

Houmao already has two related but distinct operator layers:

- specialist authoring through `houmao-mgr project easy specialist ...`
- runtime-managed agent lifecycle through `houmao-mgr agents ...` and specialist-backed instance launch through `houmao-mgr project easy instance launch`

The packaged Houmao-owned skill inventory currently includes mailbox skills plus `houmao-manage-specialist`. That packaged specialist skill intentionally excludes runtime lifecycle work such as instance launch. The new change adds a second packaged non-mailbox skill focused on agent-instance creation and lifecycle from predefined sources without mixing in mailbox management, prompt/control paths, or specialist CRUD.

The current packaged system-skill catalog is authoritative for installable Houmao-owned skills and fixed default selections. Any new packaged skill therefore needs explicit catalog treatment, visible inventory behavior, and docs/test coverage.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned skill named `houmao-manage-agent-instance`.
- Make that skill route only agent-instance lifecycle work based on predefined sources:
  - direct managed launch from `agents launch`
  - specialist-backed launch from `project easy instance launch`
  - adoption through `agents join`
  - live-instance inspection through `agents list`
  - shutdown through `agents stop`
  - stopped-session artifact cleanup through `agents cleanup session|logs`
- Keep the new skill installable through the packaged system-skill catalog.
- Make CLI-default system-skill installs include both specialist-management guidance and instance-lifecycle guidance.

**Non-Goals:**

- No mailbox management, mailbox cleanup, mailbox registration, or mailbox transport guidance.
- No prompt submission, gateway control, interrupt, relaunch, or turn management.
- No specialist CRUD in the new skill; that remains in `houmao-manage-specialist`.
- No change to managed-launch or managed-join auto-install defaults unless later work explicitly expands that scope.

## Decisions

### 1. Create a separate packaged skill instead of broadening `houmao-manage-specialist`

The new lifecycle skill will be a separate packaged directory under `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/`.

Why:

- `houmao-manage-specialist` is already scoped to reusable specialist definitions.
- Launch/join/stop/cleanup belong to runtime lifecycle, not template authoring.
- Keeping the skills separate preserves a cleaner mental model:
  - specialist skill = define reusable templates
  - agent-instance skill = create/adopt/manage live instances

Alternative considered:

- Expand `houmao-manage-specialist` to also cover instance lifecycle.
- Rejected because it would collapse authoring and runtime management into one broad skill and weaken the current boundary already documented in the skill and CLI reference.

### 2. Treat join as one form of agent-instance creation

The new skill will model two creation lanes for managed agent instances:

- launch from a predefined role/preset or specialist
- join an already-running provider session into Houmao control

Why:

- The runtime contract already treats `agents join` as creation of the same manifest-first managed-agent envelope used by launch.
- This keeps the skill lifecycle-oriented instead of source-oriented.

Alternative considered:

- Exclude `join` because it does not start the provider process.
- Rejected because the user-facing result is still the creation of a new managed agent instance under Houmao control.

### 3. Use canonical `agents` surfaces once an instance exists

The lifecycle skill will treat live-instance listing and stopping as canonical `houmao-mgr agents list` and `houmao-mgr agents stop` operations, even for specialist-backed launches.

Why:

- The docs already define a specialist-backed instance as a managed agent once running.
- This avoids teaching two parallel lifecycle control surfaces for the same live object.

Alternative considered:

- Route specialist-backed list/stop through `project easy instance list|get|stop`.
- Rejected for the initial skill because that creates a split lifecycle story and adds project-overlay-specific branching where the runtime already has one canonical surface.

### 4. Limit cleanup to `agents cleanup session|logs`

The cleanup action will only cover stopped-session envelope cleanup and session-local log cleanup.

Why:

- Those commands are lifecycle cleanup for one managed instance.
- `agents cleanup mailbox` is mailbox-secret cleanup and falls outside the requested boundary.
- Admin cleanup remains a broader maintenance surface, not instance lifecycle guidance.

Alternative considered:

- Include `agents cleanup mailbox` or `admin cleanup runtime ...`.
- Rejected because the requested scope excludes mailbox management and broader runtime-administration work.

### 5. Add a dedicated catalog set and change CLI-default selection only

The packaged system-skill catalog will gain a new named set for the new lifecycle skill, and `auto_install.cli_default_sets` will include that set alongside the existing `project-easy` set.

Why:

- The new skill is not purely `project-easy`; it spans generic `agents` lifecycle plus specialist-backed instance launch.
- A dedicated set keeps catalog intent clear.
- Changing CLI-default selection satisfies the requested exposure without automatically changing managed-launch or managed-join auto-install behavior.

Alternative considered:

- Add the new skill to `project-easy`.
- Rejected because the skill scope is broader than project-easy specialist authoring.

Alternative considered:

- Also add the new set to `managed_launch_sets` and `managed_join_sets`.
- Rejected for this change because the user only asked to broaden CLI-default selection, and widening managed-home auto-install would be a larger behavior change.

## Risks / Trade-offs

- [Two related Houmao skills may feel overlapping] → Keep the split explicit in both skills and the CLI docs: one manages reusable specialists, the other manages live instances.
- [Operators may expect project-aware `instance list|stop` coverage] → Document that the new skill uses canonical `agents list|stop` after instance creation, and keep project-aware specialist work in the existing skill.
- [CLI-default installs diverge from managed auto-install defaults] → Call out that CLI-default and managed auto-install have different scope on purpose; avoid implying that `--default` and auto-install are identical.
- [Future lifecycle work may want relaunch/prompt/gateway in the same skill] → Keep the current skill action layout modular so later lifecycle expansion can add actions without restructuring the whole skill.

## Migration Plan

1. Add the new packaged skill directory and metadata.
2. Add a new catalog skill entry plus a dedicated named set for the new lifecycle skill.
3. Update `auto_install.cli_default_sets` to include that new set while leaving `managed_launch_sets` and `managed_join_sets` unchanged.
4. Update docs and tests so `system-skills list|install|status` and the CLI reference reflect the expanded packaged inventory and default selection.
5. Roll back by removing the new skill directory and reverting the catalog/default-selection entries; no stored data migration is required because install state already records skill names and projected directories per install.

## Open Questions

- None for proposal scope. The change intentionally leaves managed-home auto-install expansion for future work.
