## Context

The repository currently has multiple tmux-facing paths that compose raw tmux command strings or rely on session-name targets directly. That has two concrete problems.

First, session-name tmux targets are easy to misuse. We already hit a real foreground gateway failure because one helper used `tmux list-panes -t <session>` and only saw the current window instead of all panes in the session. The same pattern exists in other tracking and recorder-adjacent helpers.

Second, tmux surface targeting is not consistently modeled as an explicit pane or window identity. Some tracked-TUI flows still fall back to "active pane" or "current window" behavior when a session has multiple windows. That becomes incorrect as soon as a session grows an auxiliary gateway or dashboard window.

The repository already has `libtmux` available locally. Its object model provides a safer starting point for session-wide pane enumeration, window-scoped pane lookup, and pane-id-based refresh than continuing to hand-roll raw tmux subprocess usage everywhere.

## Goals / Non-Goals

**Goals:**
- Establish a repo-owned libtmux-first tmux integration boundary for discovery, lookup, capture, and control.
- Eliminate the current-window-only pane-enumeration bug class for session-scoped lookups.
- Make multi-window tmux flows resolve explicit pane or window identity instead of relying on current-window heuristics.
- Preserve existing public behavior and storage contracts where possible while fixing the discovered bugs.
- Retain a bounded escape hatch for tmux operations that libtmux does not expose directly.

**Non-Goals:**
- Rework all tmux-using code in the repository into libtmux in one step regardless of risk or value.
- Replace public managed-agent, gateway, or recorder APIs.
- Remove all low-level tmux format queries when libtmux still requires direct command execution for a specific field.
- Redefine managed-agent identity around tmux focus state or current active window behavior.

## Decisions

### Decision: Introduce a repo-owned libtmux-first integration layer

The change will define one repo-owned tmux integration layer that becomes the preferred interface for session, window, and pane discovery plus common control operations.

That layer will use `libtmux.Server`, `Session`, `Window`, and `Pane` objects as the primary source of truth for:
- session existence and lookup,
- session-wide pane enumeration,
- window-scoped pane lookup,
- pane-id lookup and refresh,
- capture and send-key style pane control where libtmux already supports it.

Existing callers should consume repo-owned helpers or adapters rather than importing libtmux ad hoc throughout unrelated modules. This keeps the migration bounded and preserves current repository-level data models such as `TmuxPaneRecord` where they still help with compatibility and tests.

Alternatives considered:
- Keep raw subprocess tmux helpers and only patch the known `list-panes` mistakes.
  Rejected because the same bug pattern already appeared in multiple places and raw targets make similar mistakes easy to repeat.
- Replace every caller with direct libtmux usage immediately.
  Rejected because that would spread libtmux-specific assumptions throughout the codebase and create a larger migration surface than needed.

### Decision: Prefer explicit pane or window identity over current focus heuristics

For flows that must interact with a specific tmux surface, the targeting order will be:
1. stored `pane_id`,
2. stored `window_id`, `window_index`, or contractual `window_name`,
3. session-wide unambiguous pane resolution.

Current active window or active pane will only be used when the workflow contract explicitly means "current focus" or when the session truly has a single unambiguous target pane.

This is the key behavioral boundary that prevents multi-window sessions from silently drifting from the agent pane to an auxiliary gateway or dashboard pane.

Alternatives considered:
- Continue using session-only identities and prefer the active pane when multiple candidates exist.
  Rejected because that is exactly the ambiguity that makes foreground gateway and tracked-TUI ownership incorrect in multi-window sessions.
- Require pane ids for every tmux-backed contract immediately.
  Rejected because some existing contracts already expose stable window names or indices and do not need a disruptive pane-id-only migration in the first step.

### Decision: Session-scoped pane enumeration must be truly session-wide

Session-scoped pane lookup will use libtmux's session-wide pane enumeration semantics, which already map to `list-panes -s -t <session_id>`.

Helpers that conceptually answer "what panes exist in this session?" will no longer rely on bare session targets whose semantics depend on the current window. Window-scoped operations will use window ids explicitly.

This is a structural fix for the specific gateway bug and the same duplicate bug found in other helper code.

Alternatives considered:
- Keep using existing raw helpers but append `-s` manually everywhere.
  Rejected as the primary strategy because it still leaves the repository organized around raw tmux string composition rather than a safer integration boundary.

### Decision: Keep fallback tmux commands, but route them through libtmux command dispatch

Some tmux data or operations still need direct format queries or lower-level command execution. For those cases, fallback command execution remains allowed, but it should flow through libtmux-owned command dispatch such as:
- `server.cmd(...)`,
- `session.cmd(...)`,
- `window.cmd(...)`,
- `pane.cmd(...)`.

This preserves access to tmux features like `display-message -p '#{pane_dead}'` without proliferating unrelated subprocess wrappers and target-string assembly throughout the repo.

Alternatives considered:
- Ban all raw tmux commands outright.
  Rejected because libtmux does not fully expose every field we currently need.
- Continue using direct `subprocess.run(["tmux", ...])` everywhere fallback is needed.
  Rejected because it recreates the same targeting and quoting risks we are trying to constrain.

### Decision: Migrate by cluster while preserving existing contracts

The first migration wave should cover the highest-risk and highest-centrality callers:
- shared tmux runtime helpers,
- foreground gateway lifecycle,
- official/shared tracked-TUI target resolution,
- terminal recorder target resolution,
- tmux-facing explore/demo helpers that duplicated the same bug pattern.

Where current public or cross-module contracts already expose repo-owned records, those records can remain as the integration boundary even if their data is hydrated from libtmux internally.

## Risks / Trade-offs

- [libtmux does not expose every needed field directly] -> Use libtmux object-bound `cmd()` fallbacks for missing fields such as pane-dead probes and keep those fallbacks centralized.
- [Partial migration leaves duplicate raw helpers behind] -> Migrate the central helper layer first, then sweep the known duplicate call sites in the same change and add regression tests for multi-window sessions.
- [Some tracked identities still lack explicit window metadata] -> Tighten tracked-surface resolution rules and extend the affected identity producers in the same change where multi-window ambiguity matters.
- [libtmux object refresh may look heavier than current string helpers] -> Prefer short-lived lookups per control cycle and preserve repo-owned lightweight records for higher-level callers when repeated direct object mutation is unnecessary.
- [Changing target-selection rules could surface ambiguity that was previously hidden] -> Fail explicitly or degrade to diagnostic/non-authoritative behavior rather than silently controlling or tracking the wrong pane.

## Migration Plan

1. Introduce the repo-owned libtmux-first integration helpers and cover them with unit tests, including session-wide pane enumeration and libtmux-command fallback behavior.
2. Migrate the shared tmux runtime helper layer used by gateway and related runtime code.
3. Migrate foreground gateway liveness and shutdown targeting to rely on the libtmux-backed session-wide pane lookup.
4. Migrate tracked-TUI transport resolution and affected identity producers so multi-window sessions keep observing the intended agent surface.
5. Migrate terminal recorder target resolution and the known raw duplicate helpers in explore/demo code that currently use current-window-sensitive session targets.
6. Run targeted unit/integration coverage and the live foreground gateway repro to confirm the original bug is fixed under the new integration layer.

Rollback is code-only. No persisted storage migration is required, so reverting the tmux integration layer and migrated callers is sufficient if the change needs to be backed out.

## Open Questions

- Should tracked-TUI identities grow an explicit `pane_id` field where available, or is contractual `tmux_window_name` / `window_index` sufficient for the current migration?
- How much of the explore/demo tmux helper surface should be migrated in this change versus left to follow-up cleanup after the shared helper layer is stable?
