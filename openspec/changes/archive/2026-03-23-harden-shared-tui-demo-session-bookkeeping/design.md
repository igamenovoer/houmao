## Context

The shared tracked-TUI demo pack has two different tmux lifecycle shapes:

- `recorded-capture` launches a one-shot tool session, optionally starts terminal-recorder in active mode, drives a scenario, and is supposed to reap workflow-owned tmux resources before returning.
- `start` launches a live-watch tool session plus a separate dashboard session, optionally adds recorder-backed observation, and expects the operator to end the run later with `stop`.

Today those workflows do not persist ownership metadata early enough or consistently enough:

- `recorded-capture` does not write `capture_manifest.json` until after scenario execution and post-run bookkeeping, so there is no durable session record during the startup window between tmux launch and final-manifest write.
- `live watch` writes `interactive_watch_manifest.json` during startup, but it still relies on in-memory `_StartupResources` for failed-start cleanup and has no forceful operator-facing recovery path for stale demo-owned tmux sessions.
- Session discovery today is mostly name-based or run-root based. That is acceptable on the happy path, but it is weak when a run is interrupted after tmux state already exists and before the normal manifest path is fully persisted.

The repository already has an established tmux-discovery pattern based on tmux session environment, for example `AGENTSYS_MANIFEST_PATH` and `HOUMAO_TERMINAL_RECORD_LIVE_STATE`. This change should align with that pattern instead of adding a separate cleanup-only metadata channel such as tmux user options.

## Goals / Non-Goals

**Goals:**

- Persist demo-owned tmux session bookkeeping before and during resource creation rather than only at the end of a successful run.
- Use one shared ownership model for `recorded-capture` and `live watch`.
- Publish enough tmux session environment metadata for later recovery to map a live tmux session back to its demo run and owned role.
- Add an operator-facing forceful cleanup path for one run that can recover stale tool, dashboard, and recorder tmux sessions.
- Keep `stop` as the normal graceful live-watch finalization path while making cleanup/recovery explicit and deterministic.

**Non-Goals:**

- Introduce a background daemon that continuously reaps demo sessions.
- Kill unrelated tmux sessions by prefix match alone.
- Replace the existing live-watch `stop` flow with a force-kill-only workflow.
- Add new third-party dependencies or require `houmao-server` for cleanup.
- Generalize this demo-specific ownership model into the whole repo's tmux runtime contract in this change.

## Decisions

### 1. Add a dedicated mutable ownership artifact for each demo run

Each `recorded-capture` and `live watch` run will gain a small run-local ownership artifact, tentatively `session_ownership.json`, that is written as soon as the run root exists and updated incrementally as workflow-owned resources are created or reaped.

The artifact will be separate from `capture_manifest.json` and `interactive_watch_manifest.json` rather than replacing them. It will contain only the data needed for lifecycle recovery:

- demo id and workflow kind,
- run root,
- tool,
- ownership status such as `starting`, `running`, `cleanup_pending`, `stopped`, or `failed`,
- recorder run root when present,
- a list of owned resources with role and tmux session name,
- timestamps for last update and cleanup.

Why:

- `capture_manifest.json` is currently a late happy-path artifact, so it cannot protect the recorded-capture startup window that is actually leaking.
- `interactive_watch_manifest.json` is a richer final run contract, but it is not a good mutable startup registry for partially created resources.
- A dedicated ownership artifact lets cleanup remain simple and shared across the two workflows without overloading reporting manifests with partial-start state.

Alternatives considered:

- Reuse `capture_manifest.json` and `interactive_watch_manifest.json` only.
  Rejected because the recorded-capture manifest is written too late today and the live-watch manifest has a broader reporting contract than the recovery path needs.
- Keep only in-memory `_StartupResources` plus tmux naming conventions.
  Rejected because it does not survive crashes or interrupts after tmux state exists.

### 2. Publish recovery pointers through tmux session environment, not tmux user options

Every demo-owned tmux session will publish a small set of secret-free environment variables immediately after creation. The exact names can be finalized during implementation, but the shape is:

- a stable demo marker such as `HOUMAO_SHARED_TUI_DEMO_ID`,
- the absolute run root,
- the absolute ownership-artifact path, and
- the resource role such as `tool`, `dashboard`, or `recorder`.

The tool and dashboard sessions will be tagged directly by the demo pack. Recorder-owned tmux sessions will be tagged after recorder startup using the recorder manifest's `recorder_session_name`.

Why:

- The repo already has first-class helpers for tmux session environment publication and lookup.
- Existing specs and code paths already treat tmux environment as the durable discovery channel for related runtime metadata.
- Cleanup only needs stable secret-free pointers, which are a good fit for tmux session environment.

Alternatives considered:

- Use tmux user options like `@houmao_run_root`.
  Rejected because the repo already standardizes on tmux session environment for discovery, and adding a second metadata mechanism would create needless duplication.
- Rely on session-name prefixes alone.
  Rejected because name prefixes are not authoritative, do not encode role or run root, and make false-positive cleanup more likely.

### 3. Centralize session discovery around manifest-first resolution with tmux-env fallback

Cleanup and recovery logic will move into shared demo-pack helpers that can resolve owned tmux resources for one run by combining:

1. the run-local ownership artifact,
2. the existing final run manifests when present, and
3. tmux session environment discovery when the artifact is partial or the final manifest is absent.

The normal resolution order will be:

1. load the ownership artifact for the targeted run,
2. trust any explicitly listed session names that are still live,
3. enumerate tmux sessions and recover additional owned sessions whose published ownership path or run root matches the targeted run,
4. deduplicate by session name and role,
5. perform role-aware cleanup.

Role-aware cleanup means:

- stop recorder gracefully through `stop_terminal_record(run_root=...)` when a recorder run root is known,
- kill leftover recorder tmux session directly if graceful stop cannot run,
- kill dashboard and tool tmux sessions directly as best-effort cleanup.

Why:

- Manifest-first resolution keeps the run-local filesystem as the primary source of truth.
- Tmux-env fallback closes the gap when startup was interrupted after tmux creation but before the ownership artifact was fully updated.
- Centralizing this logic avoids live-watch and recorded-capture drifting into separate cleanup behaviors again.

Alternatives considered:

- Use tmux-env discovery only.
  Rejected because cleanup should prefer run-local durable state when it exists.
- Keep separate discovery logic in `recorded.py` and `live_watch.py`.
  Rejected because the problem is cross-cutting and the current inconsistency is part of the bug.

### 4. Add a forceful `cleanup` command and keep `stop` as the graceful live-watch path

The demo driver will gain a dedicated `cleanup` command intended for stale-run recovery. It will accept a targeted `--run-root` and may default to the latest relevant run root when omitted, following the existing live-watch command style.

`cleanup` is intentionally different from `stop`:

- `stop` remains the normal live-watch command that finalizes analysis and reporting artifacts.
- `cleanup` is a forceful recovery path that reaps workflow-owned tmux resources for a run even when graceful finalization is not possible.

The cleanup command should be explicit in its output that it is a recovery action and does not promise finalized replay/comparison/report artifacts.

Why:

- Operators need a supported recovery tool for leaked tmux sessions after partial failures.
- Overloading `stop` with forceful stale-run semantics would muddy the difference between graceful finalization and emergency reap.

Alternatives considered:

- Make `start` auto-reap all previously discovered demo-owned sessions.
  Rejected because developers may intentionally keep a separate live-watch run open, and startup should not destroy concurrent intentional sessions.
- Fold forceful cleanup into `stop` only.
  Rejected because `stop` is the reporting/finalization path and should remain predictable.

### 5. Write ownership metadata before the current leak windows and update it atomically

`recorded-capture` will create the ownership artifact before `launch_tmux_session()` and update it immediately after each owned resource is created. `live watch` will do the same before launching the tool session, before or immediately after recorder start, and before launching the dashboard session.

Ownership updates should use atomic rewrite semantics so partial process death does not leave a truncated JSON file. Status changes should be explicit:

- `starting` while resources are being created,
- `running` once the workflow reaches its normal steady state,
- `cleanup_pending` when forceful cleanup begins,
- `stopped` or `failed` when the run reaches a terminal state.

Why:

- The entire point of the change is to move durable ownership bookkeeping ahead of the leak window.
- Atomic writes reduce the chance that cleanup recovery finds a malformed file and loses the authoritative session map.

Alternatives considered:

- Write ownership metadata only once all sessions are launched.
  Rejected because that reproduces the existing startup gap.
- Append NDJSON event logs only.
  Rejected because cleanup needs a compact current snapshot, not an event-sourcing exercise.

## Risks / Trade-offs

- [Forceful cleanup can skip graceful live-watch finalization] → Keep `stop` as the documented normal path and document `cleanup` as emergency recovery that may leave analysis artifacts incomplete.
- [Tmux environment can become stale or be missing on some sessions] → Use tmux-env as fallback, not the sole source of truth, and validate ownership paths before trusting recovered sessions.
- [Adding a second run-local artifact increases bookkeeping complexity] → Keep the ownership artifact narrowly scoped to lifecycle recovery and avoid duplicating reporting fields already owned by existing manifests.
- [Recorder cleanup is more complex than plain tmux kill] → Prefer recorder-service stop by run root when known, and only fall back to direct tmux kill when graceful recorder shutdown is unavailable.

## Migration Plan

This change does not require a user data migration. Implementation can land as a clean break inside the demo pack:

1. add the ownership artifact model and shared discovery helpers,
2. update `recorded-capture` and `live watch` to publish and consume that metadata,
3. add the new `cleanup` command,
4. update docs and tests for the new recovery contract.

Rollback is a normal code revert. Old run roots without an ownership artifact can continue to be ignored or handled best-effort through the existing manifests and tmux naming.

## Open Questions

- Should the cleanup command default to the latest live-watch run only, or should it also consider the latest recorded-capture run when `--run-root` is omitted?
  Current direction: support explicit `--run-root` first and keep any omission rule conservative.
