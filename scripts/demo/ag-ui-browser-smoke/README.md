# AG-UI Browser Smoke

This opt-in fixture validates the browser-side `houmao_render_graphic` rendering contract with Bun-global Playwright. It does not require a live Houmao gateway. The Bun script imports `playwright`, intercepts a deterministic AG-UI SSE response, reconstructs the graphics tool call, and verifies visible title, alt text, and SVG evidence.

Run it explicitly:

```bash
scripts/demo/ag-ui-browser-smoke/run_smoke.sh
```

The script fails early when `bun` or Bun-global `playwright` is unavailable. The default Python test commands do not run this browser fixture.
