## Context

The managed-agent join flow intentionally allows later local `state`, `show`, `prompt`, `interrupt`, and gateway-capable control to reuse the same manifest-first control path as native launches. For joined TUI sessions, the adopted tmux window name is part of that authority because the runtime tracker resolves the target pane using tmux session name, window index `0`, and window name together.

The regression appears after a successful join, not during it. Initial join materialization already knows the adopted window name and can build a correct manifest payload. The break happens on the first resumed local control path, where the runtime rewrites the manifest from resumed backend state that no longer carries `tmux_window_name`. Once that write lands, managed-agent identity falls back to the launch-time default window name `agent`, and local TUI probing fails against sessions whose adopted window is still named something else such as `claude`.

## Goals / Non-Goals

**Goals:**

- Preserve the adopted tmux window name for joined `local_interactive` sessions across resume and manifest rewrites.
- Keep local managed-agent `state` and `show` working after a successful TUI join without requiring the join path to rename the user’s tmux window.
- Add regression coverage for the exact failure sequence observed in the live `test-agent-join` reproduction.

**Non-Goals:**

- Redesign joined-session tmux topology or change the v1 contract that window `0` is the canonical adopted surface.
- Add arbitrary window selection or rename the adopted window during join.
- Change headless join semantics beyond preserving any analogous tmux window metadata if the shared persistence path touches it.

## Decisions

### 1. Preserve adopted window metadata in resumed local interactive backend state

The resumed local interactive state object should explicitly carry `tmux_window_name`, and the shared backend-state serializer used by `persist_manifest()` should emit it when present.

Why:

- The overwrite happens because the persisted manifest is rebuilt from backend state during resume-time capability publication.
- The runtime already treats tmux session name as backend state for resumed local interactive sessions; tmux window name belongs in the same bucket for joined TUI sessions.
- This is the most direct repair because it fixes the value at the source of the later manifest rewrite instead of patching downstream readers one by one.

Alternative considered: preserve the old manifest fields during `persist_manifest()` by merging the previous payload. Rejected because it hides the real missing state in the resumed backend model and makes persistence behavior more ad hoc.

### 2. Keep a defensive read-side fallback from joined launch metadata

Managed-agent local TUI identity resolution should keep using persisted manifest tmux window fields first, but it should also have a safe fallback to joined launch metadata when a joined manifest lacks normalized tmux window fields unexpectedly.

Why:

- The resumed joined launch plan already retains `launch_plan.metadata.tmux_window_name`.
- A defensive fallback reduces the chance that one incomplete manifest rewrite makes local TUI tracking unrecoverable.
- This is especially useful for already-created joined manifests produced before the fix, where the launch metadata may still be the only surviving copy of the adopted window name.

Alternative considered: rely only on fixed manifest persistence and ignore older broken manifests. Rejected because it leaves existing joined sessions brittle until they are re-joined.

### 3. Regression tests should exercise the actual overwrite path

The verification plan should include one regression that reproduces the real failure chain:

```text
join succeeds
  -> resume_runtime_session() runs through local control
  -> controller.ensure_gateway_capability() persists manifest
  -> later managed-agent state/show still probe the adopted window name
```

Why:

- The bug is not “join writes the wrong window name”; isolated payload construction is already correct.
- The failure depends on the first resumed manifest rewrite, so tests must include that path rather than only asserting initial join payload content.

Alternative considered: only test manifest builders in isolation. Rejected because that would miss the exact regression that escaped here.

## Risks / Trade-offs

- [Risk] Preserving tmux window name in shared resumed state could unintentionally affect non-joined local interactive flows. → Mitigation: scope assertions and tests around joined manifests and ensure the field remains optional for native launches that still use the default window naming path.
- [Risk] Adding a read-side fallback could mask future write-side regressions. → Mitigation: keep the fallback narrow to joined-session metadata and retain explicit regression coverage for correct persistence.
- [Risk] Existing broken joined manifests may still be partially inconsistent. → Mitigation: make the local tracking read path tolerant when launch metadata still contains the adopted window name, and document that re-joining is the clean recovery path if a manifest is already missing all copies.

## Migration Plan

No storage migration is required.

Implementation sequence:

1. extend resumed local interactive state and backend-state serialization to preserve `tmux_window_name`,
2. add the defensive read-side fallback for joined local TUI identity/tracking,
3. add regression coverage for join followed by local `state`/`show`.

Rollback is straightforward: revert the fix and re-join any sessions created during testing if needed. This does not require a schema version change.

## Open Questions

None.
