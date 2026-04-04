## Why

Managed headless turns currently expose raw provider JSON directly on the live tmux pane and in downstream inspection flows. That machine-oriented output is durable, but it is not readable enough for operators, and the repo does not yet have a stable canonical event layer that separates provider protocols from Houmao-facing rendering and inspection.

## What Changes

- Add a headless-output bridge that launches Claude, Codex, and Gemini headless CLIs as subprocesses, preserves their raw stdout/stderr artifacts, and renders a human-readable live stream for the tmux pane.
- Introduce a canonical normalized headless event model so provider-specific JSON is parsed once and then reused by tmux rendering, turn inspection, passive-server compatibility, and managed-agent detail/history projections.
- Add two operator-facing headless output knobs:
- `style`: `plain`, `json`, or `fancy`
- `detail`: `concise` or `detail`
- Default live headless output to `plain` + `concise` while keeping raw provider JSON available as durable artifacts and debug surfaces.
- Update managed headless turn inspection surfaces so `events` return canonical semantic events instead of thin provider passthrough, while `stdout`/`stderr` artifact routes remain the raw provider/debug artifacts.
- Align `houmao-mgr` headless inspection and rendering behavior with the existing print-style vocabulary without overloading the provider protocol output-format setting.

## Capabilities

### New Capabilities
- `headless-output-rendering`: Normalize provider headless JSON into canonical Houmao semantic events, preserve raw provider artifacts, and render operator-facing live and inspection output with style/detail controls.

### Modified Capabilities
- `houmao-server-agent-api`: Managed headless turn status, events, and detail surfaces will expose canonical normalized headless output summaries and event semantics rather than only raw provider-oriented payloads.
- `passive-server-headless-management`: Passive server headless turn events and related compatibility surfaces will adopt the canonical normalized headless event contract while preserving raw artifact retrieval.
- `houmao-srv-ctrl-native-cli`: Native `houmao-mgr agents turn ...` and related headless inspection flows will expose the new headless output style/detail controls and render canonical normalized headless events.

## Impact

- Affected code: headless runtime backends, managed-agent turn artifact readers, passive/server headless services, `houmao-mgr` managed-agent commands and renderers, and shared models for headless events/detail.
- Public contracts: managed headless turn event payloads, managed-agent headless detail/status summaries, and native CLI headless inspection behavior.
- Artifacts: raw provider `stdout.jsonl`/`stderr.log` stay intact; a new canonical normalized event artifact will be added for replay and rendering.
- Testing: new parser fixtures and golden rendering coverage for Claude, Codex, and Gemini across `plain/json/fancy` and `concise/detail`.
