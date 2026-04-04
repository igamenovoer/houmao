## 1. Runtime Bridge And Canonical Event Model

- [ ] 1.1 Add a shared headless output bridge that launches the provider CLI as a subprocess, preserves raw stdout/stderr artifacts, and writes a separate canonical normalized event artifact.
- [ ] 1.2 Introduce the canonical headless semantic event model and parser registry for Claude, Codex, and Gemini, including normalized session identity, concise-field mappings, and passthrough handling for unknown provider events.
- [ ] 1.3 Extract a shared headless-domain renderer core for canonical events that supports incremental streaming and replay, run it inside the live bridge process on the tmux pane, and reuse it from the later `houmao-mgr` replay path.
- [ ] 1.4 Thread the new headless output controls (`style` and `detail`) through the supported managed headless runtime configuration path with defaults of `plain` and `concise`.

## 2. Managed-Agent And Passive-Server Surfaces

- [ ] 2.1 Update local managed-agent headless artifact readers to prefer canonical event artifacts and fall back to legacy raw-stdout parsing for older turns.
- [ ] 2.2 Update `houmao-server` managed headless turn status, events, and detail projections to consume canonical semantic events while keeping raw artifact routes unchanged.
- [ ] 2.3 Update passive-server headless turn inspection and compatibility paths to consume canonical semantic events with the same raw-artifact preservation and legacy fallback behavior.

## 3. CLI Rendering, Tests, And Documentation

- [ ] 3.1 Update `houmao-mgr agents turn events` and related headless inspection rendering to show canonical events, honor root print styles, reuse the shared headless renderer core, and support `--detail concise|detail`.
- [ ] 3.2 Add parser fixtures and golden tests for Claude, Codex, and Gemini covering raw artifact preservation, canonical event generation, live-render style/detail combinations, replay parity between gateway live output and CLI inspection, and legacy fallback behavior.
- [ ] 3.3 Update relevant help text and documentation for the new headless output behavior, including the distinction between raw artifacts and rendered/canonical inspection output, the concise rendering contract, and the shared live/replay renderer semantics.
- [ ] 3.4 Keep the provider schema notes under this change's `schema/` directory aligned with captured fixtures and parser behavior for Claude, Codex, and Gemini, especially around thinking-accounting availability and action lifecycle mapping.
