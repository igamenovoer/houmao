## Context

The AG-UI workbench already separates protocol state from local presentation state. The runtime owns long-lived AG-UI streams, watched-target reconnect loops, active-thread polling, tmux attach WebSockets, and shared tmux inventory. React panes own DOM refs, short-lived input state, xterm objects, and local rendering choices.

The current tmux tab creates an xterm `Terminal`, opens it into a host element, fits once, and refits when a `ResizeObserver` reports host changes. That path sends tmux resize messages only when rows or columns change, which is correct, but it does not force a repaint when the terminal viewport scrolls or when Dockview emits same-size layout changes. Tailmux handles a similar browser-terminal surface by explicitly fitting on Dockview dimension and visibility changes and by treating scroll as a terminal-local operation.

The current template graphics path is message-driven. A completed `houmao.graphic.template` tool call is reconstructed from AG-UI events, validated in the workbench, then rendered by a registry keyed by renderer id. The renderer choice comes from `payload.renderer.preferred`, `payload.renderer.fallback`, and built-in defaults. That behavior is correct for `auto`, but manual testing now needs a GUI-side way to force a renderer without changing the agent message.

The current picker resolves selected discovered agents and then either creates a pane or retargets an existing pane. The pane's Connect button separately marks active thread where supported and registers the target as watched. The picker can reuse that same intent so selecting an agent from the list opens a usable pane immediately.

## Goals / Non-Goals

**Goals:**

- Refresh the full visible xterm area after local scroll, parsed writes, and layout/refit events.
- Keep tmux terminal bytes, xterm objects, and fit state outside reduced runtime state.
- Add a pane-level `auto | vega-lite | recharts` template renderer preference.
- Persist the renderer preference as safe UI metadata only.
- Propagate the renderer preference through display rendering without mutating AG-UI events or tool-call arguments.
- Auto-connect discovered-agent new-pane and retarget picker actions through the same watched-target and active-thread paths used by explicit Connect.
- Add deterministic browser coverage for the new behaviors.

**Non-Goals:**

- Do not change the AG-UI protocol, gateway event fanout, or Python template graphic schema.
- Do not add raw Vega-Lite Layer 2 graphics or custom React component support in this change.
- Do not persist transcript text, raw AG-UI events, tool-call payloads, terminal bytes, prompt text, credentials, or request bodies in localStorage.
- Do not make tmux tab scrollback durable across browser reloads.
- Do not auto-connect blank manual panes.

## Decisions

### Store renderer preference as pane presentation metadata

Add a small presentation config to `PaneRecord`, for example:

```ts
type TemplateGraphicBackendOverride = "auto" | "vega-lite" | "recharts";

interface PanePresentationConfig {
  templateGraphicBackend: TemplateGraphicBackendOverride;
}
```

`storage.ts` should provide a default of `auto`, sanitize unknown values back to `auto`, and persist this alongside target metadata. `workbenchContext.tsx` should expose an `updatePanePresentation` callback. `AgentSessionPanel` should render a compact select control labeled for template rendering and update only that pane's config.

Alternative considered: store one global renderer preference. A global preference is simpler but makes side-by-side renderer comparison difficult, which is one of the main reasons for adding the control.

### Pass renderer preference through rendering context

Extend the display and component renderer path rather than changing reduced AG-UI event state:

```text
PaneRecord.presentation.templateGraphicBackend
  -> AgentSessionPanel
  -> AgUiDisplaySurface
  -> ToolCallRenderer
  -> renderTemplateGraphic(payload, context)
  -> selectTemplateRenderer(payload, override)
```

`auto` should use the existing selection order. A forced renderer should evaluate only the selected renderer; if unsupported, return a visible fallback explaining that the override cannot render the payload. This keeps raw diagnostics trustworthy because the tool-call payload remains unchanged.

Alternative considered: rewrite `payload.renderer.preferred` in the reconstructed tool-call arguments before validation. That would make diagnostics lie about what the agent sent and would blur the contract between protocol data and GUI presentation.

### Reuse connect intent for picker auto-connect

Extract the Connect button behavior into an App-level helper that can be called after pane creation or retargeting:

```text
connectPaneToTarget(paneId, target, source)
  -> persist or update watched target record
  -> dispatch pane/targetChanged for immediate runtime view update
  -> dispatch activeThread/setRequested when target is discovered and has gateway/thread identity
```

`addAgentPane(target, { autoConnect: true })` should return the new pane id so the picker can trigger the helper. `retargetPane(paneId, target, { autoConnect: true })` should clear obsolete active-thread selection and pane-local state as it does today, then invoke the helper for the new target. The helper should tolerate unavailable gateways by creating or updating the watched target and letting the existing watcher enter waiting, offline, or reconnecting states.

Alternative considered: have `AgentSessionPanel` auto-connect in a `useEffect` when mounted with a discovered target. That would make manual restores or unrelated discovered target edits unexpectedly connect. The picker intent is explicit, so the auto-connect request should originate from the picker/App flow.

### Keep active-thread mutation best-effort and runtime-owned

The helper should dispatch `activeThread/setRequested` only when the normalized gateway key and thread id are available. Runtime active-thread effects already suppress mutations for gateways marked unsupported. A fresh gateway should be allowed to try because the route may have become available after a sidecar restart.

Alternative considered: wait for the pane's active-thread selector to report `canMutate` before setting. That selector lives in pane rendering and would require imperative cross-component coordination. Runtime actions already model the mutation lifecycle.

### Refresh xterm locally without changing tmux runtime state

Add a local `scheduleTerminalRefresh()` helper in `TmuxTabPanel` that calls `terminal.refresh(0, terminal.rows - 1)` in `requestAnimationFrame`. Register xterm disposables for `terminal.onScroll` and `terminal.onWriteParsed` to schedule the refresh. Call the refresh helper after every `fitAddon.fit()` even when the fitted rows and columns are unchanged.

Use Dockview panel API hooks in addition to the existing `ResizeObserver`: `onDidDimensionsChange` and `onDidVisibilityChange` should schedule a fit. Keep resize dispatch gated by actual column/row changes so repaint-only work does not send redundant tmux resize messages.

Alternative considered: make the runtime store terminal output and replay it on repaint. That would violate the current persistence and runtime boundary and would still not fix local xterm rendering artifacts.

### Treat explicit wheel interception as a fallback tactic

The first implementation should rely on xterm's own wheel handling plus `onScroll` repaint scheduling. If Playwright or manual testing still reproduces stale edges, add a host-level wheel handler that mirrors Tailmux: prevent default browser scrolling, call `terminal.scrollLines(...)`, then schedule a refresh.

Alternative considered: immediately override all wheel behavior. That can change scroll sensitivity and risks double-scrolling if xterm also handles the event.

### Test behavior through deterministic browser flows

Use the existing workbench Playwright harness and fixture services. Renderer override tests can drive deterministic AG-UI fixture events and inspect renderer-specific test ids or DOM evidence. Picker auto-connect tests can use fake passive-server discovery and fake gateway streams. Tmux repaint tests should use the tmux fixture bridge, produce enough output to create scrollback, wheel-scroll the terminal, and assert visible terminal evidence changes without resizing the browser.

Alternative considered: unit-test the tmux repaint helper only. That would not cover the stale-edge bug because the failure depends on xterm, Dockview layout, CSS, and browser paint behavior.

## Risks / Trade-offs

- Renderer override can confuse the meaning of `renderer.preferred` → Keep override UI local and leave diagnostics/raw payloads unchanged.
- Forced renderer errors can look like chart failures → Use explicit diagnostic wording that names the forced renderer and payload title.
- Auto-connect can open background streams the user did not expect → Limit auto-connect to discovered-agent row selection, not blank manual panes or passive list refresh.
- Active-thread route can be stale or unsupported → Let runtime model unsupported state and keep watched-target connect independent from active-thread success.
- Tmux repaint can be browser-timing sensitive → Refresh after scroll/write/fit and include Dockview dimension/visibility hooks; keep explicit wheel interception as a measured fallback.
- Browser tests may be flaky if they assert pixels too tightly → Prefer DOM evidence, terminal text visibility, and broad screenshot/pixel checks over exact pixel parity.

## Migration Plan

This is an additive workbench change. Existing panes with no presentation config should load with `templateGraphicBackend = "auto"`. Existing AG-UI messages, gateway routes, and Python graphics authoring remain valid.

Rollback is straightforward: remove the renderer preference storage field and UI, return `ToolCallRenderer` to passing only pane/tool-call ids, and remove the tmux refresh hooks. Existing localStorage entries with unknown presentation fields should be ignored by sanitization.

## Open Questions

- Should forced renderer failure be a visible component fallback only, or should it also add an entry to the pane error stack?
- If the first repaint fix passes Playwright but manual testing still shows stale edges on a specific browser/GPU path, should we adopt Tailmux-style wheel interception unconditionally or behind a terminal option?
