## Context

The AG-UI workbench already owns tmux presentation through a local Fastify server, runtime effects, and pane-local xterm objects. An archived change added xterm refresh hooks after scroll, parsed writes, fits, Dockview dimension changes, and Dockview visibility changes. That fixed the earlier deterministic fixture failure, but manual validation against a real tmux session still reproduced stale edge regions that disappeared after an outer window resize.

The same validation pass checked first-connect graphics. Existing and relaunched agents can publish template graphics to the workbench on first connect, including omitted-route active-thread fallback. A true new-agent validation path is currently blocked before the GUI path can be tested because one project preset still references retired `houmao-agent-ag-ui`, and the launch path reports that stale reference while launching an unrelated Claude specialist.

## Goals / Non-Goals

**Goals:**

- Make real tmux attachments repaint the full visible terminal area after scroll and layout changes without requiring browser resize.
- Keep tmux size synchronization correct when a pane measures terminal dimensions before the attach WebSocket reaches `attached`.
- Preserve the existing boundary where xterm objects, layout measurements, and terminal bytes stay outside reduced runtime state and localStorage.
- Make project agent launch validation source-scoped so a stale unrelated preset does not block launching another specialist.
- Restore a true new-agent first-connect graphics smoke path and make the smoke assertion robust to Plotly's multiple SVG layers.

**Non-Goals:**

- Do not implement the pending cross-runtime tmux PTY backend in this change.
- Do not change AG-UI event schemas, gateway publish semantics, or Houmao typed graphic payload schemas.
- Do not add durable tmux scrollback storage or replay terminal bytes through runtime state.
- Do not treat tmux pane attach, detach, or close as managed-agent lifecycle operations.

## Decisions

### Add an explicit post-attach size synchronization path

`TmuxTabPanel` should distinguish "last measured terminal size" from "last size delivered to the active attachment." If `fitAddon.fit()` runs while the pane is still attaching, the pane may know the correct xterm columns and rows but withhold `tmux/resizeRequested`. When attach later succeeds, the pane should send the current measured size once for that attachment before relying on future changed-size fits.

Alternative considered: always send resize on every fit. That is simpler but adds redundant tmux resize traffic for same-size Dockview and visibility events, which the existing spec explicitly avoids.

### Treat wheel interception as the measured repaint fallback

The archived design left host-level wheel handling as the fallback if xterm's own wheel handling plus `onScroll` refresh still left stale edges. This change should add that fallback only at the terminal host boundary: prevent outer browser scrolling for terminal wheel events, call xterm's scroll API, then schedule a full visible-row refresh.

Alternative considered: rely on the current `onScroll` refresh hooks because the fixture test passes. Manual real-tmux evidence shows that fixture coverage is not enough, so the fallback needs to be implemented and covered.

### Strengthen tests with real-size evidence instead of exact pixel matching

The deterministic fixture test should continue to cover ordinary tmux repaint behavior. Add a real tmux smoke or manual-capable Playwright probe that records xterm rows/columns, terminal host dimensions, and `tmux list-panes` size before and after attach, scroll, and resize. Assertions should check broad visibility and size synchronization rather than exact pixel parity.

Alternative considered: assert screenshot equality before and after resize. Browser font rendering and GPU paths make exact pixel assertions brittle; size evidence and visible text/pixel sanity checks are more useful.

### Scope launch validation to the selected launch source

Project launch should parse and validate the selected specialist/profile/preset and the dependencies needed to construct that launch. It should not fail because another project preset contains a retired system-skill selector. When the selected source itself contains a retired selector, the launch should still fail clearly with the source path/name and unknown skill.

Alternative considered: update only the stale project preset. That unblocks this workspace once, but it leaves the broad-validation bug in place and can regress when another stale unused record appears.

### Keep the smoke fixture honest

The project-local Kimi preset should reference current `houmao-interop-ag-ui` or no AG-UI system skill, depending on the intended preset behavior. The real-agent smoke should use a chart-visible assertion that accepts Plotly's multiple SVG layers, matching the existing workbench fixture tests that use `locator("svg").first()`.

Alternative considered: keep the existing strict SVG assertion and treat the failure as a renderer problem. The screenshot and transcript evidence show the renderer is working; the failure is the test locator.

## Risks / Trade-offs

- Real tmux repaint may remain browser or GPU sensitive -> include a manual-capable smoke that saves screenshots and size diagnostics so failures are actionable.
- Wheel interception can alter scroll feel -> keep it scoped to the xterm host and verify it does not affect page-level controls or tmux input.
- Post-attach resize dispatch can duplicate a resize already applied by tmux attach defaults -> track size delivery per attachment and dispatch only when no current attachment has received that measured size.
- Source-scoped launch validation can hide stale unused config until selected -> keep list/inspect/edit surfaces responsible for reporting their own invalid selected records clearly.
- Updating the local test preset can affect Kimi-specific tests -> choose the current skill name only if that preset is meant to exercise AG-UI; otherwise remove the stale selector and cover AG-UI through the maintained Claude smoke.

## Migration Plan

This is a development-time bug fix. Existing browser storage does not need migration because no new persisted pane fields are required. Existing stale project presets or profiles that select retired system skills should fail only when used or inspected through the selected record path; this workspace's stale test preset should be updated as part of the change.

Rollback is straightforward: revert the tmux pane repaint and post-attach resize changes, restore the prior launch validation behavior, and restore the prior smoke assertion. No runtime data migration is needed.

## Open Questions

- Should the real tmux smoke run in CI only when tmux is available, or remain a manual script that the bug-fix task must run locally?
- Should the stale `test-kimi-code-tui` preset use `houmao-interop-ag-ui`, or should it omit AG-UI skills because it is intended to test Kimi TUI only?
