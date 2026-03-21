# Probe, Parse, And Track Pipeline

One live tracking cycle in `houmao-server` is implemented by `HoumaoServerService.poll_known_session()` in [`../../../../src/houmao/server/service.py`](../../../../src/houmao/server/service.py). The service does not ask the child CAO for terminal status. It probes tmux directly, inspects the pane process tree, parses captured output, and records the result into the in-memory tracker.

## Poll Cycle Overview

For one `tracked_session_id`, the service runs this sequence:

1. Load the current tracker and its `HoumaoTrackedSessionIdentity`.
2. Check `tmux_session_exists(identity.tmux_session_name)`.
3. Resolve the pane target through `TmuxTransportResolver.resolve_target(...)`.
4. Inspect the pane process tree with `PaneProcessInspector.inspect(tool=identity.tool, pane_pid=target.pane.pane_pid)`.
5. If the supported TUI is up, capture the pane text from tmux.
6. If the tool is parser-supported, capture or reuse the parser baseline.
7. Parse the captured text through `OfficialTuiParserAdapter`.
8. Commit the cycle into `LiveSessionTracker.record_cycle(...)`.

The worker keeps running for most outcomes. The only normal case that returns `False` and ends the worker loop is `tmux_missing`.

## Transport Resolution

`TmuxTransportResolver` in [`../../../../src/houmao/server/tui/transport.py`](../../../../src/houmao/server/tui/transport.py) resolves one tmux pane target.

Current selection rules are:

- if no panes exist for the tmux session, raise `TmuxCommandError`
- if `tmux_window_name` is provided, keep only panes whose `pane.window_name` matches it
- if that filtered set is empty, raise `TmuxCommandError`
- when multiple panes remain, prefer the active pane
- when no window name is provided, choose from all panes, again preferring the active pane

The hardening change matters here: specifying a window name no longer falls back silently to any active pane in the session. A wrong or stale window name is treated as a probe failure instead of selecting an arbitrary pane.

## Process Inspection

`PaneProcessInspector` in [`../../../../src/houmao/server/tui/process.py`](../../../../src/houmao/server/tui/process.py) determines whether the supported TUI process is actually running inside the tracked pane.

It works by:

1. reading the live process table from `ps -ax`
2. walking descendants from the tmux pane root pid
3. matching descendants against a tool-specific expected process-name list

This yields one of four important process states:

- `tui_up`: a supported tool process is present in the pane tree
- `tui_down`: tmux is live but the supported tool process is absent
- `unsupported_tool`: the server has no configured process matcher for that tool
- `probe_error`: the pane pid is invalid or `ps` inspection failed

This is the boundary that keeps stale tmux scrollback from being mistaken for a live tool process.

## Probe Snapshot

Every cycle can record a `HoumaoProbeSnapshot`.

Before capture, it contains:

- `observed_at_utc`
- `pane_id`
- `pane_pid`
- `matched_process_names`

After a successful tmux capture, the service updates the snapshot with:

- `captured_text_hash`
- `captured_text_length`
- `captured_text_excerpt`

The excerpt is intentionally bounded to the last 4000 characters so the live state contains useful evidence without turning the route payload into a full pane dump.

## Official Parsing

`OfficialTuiParserAdapter` in [`../../../../src/houmao/server/tui/parser.py`](../../../../src/houmao/server/tui/parser.py) is a thin adapter over the shared `ShadowParserStack`.

The server-side naming is intentionally different from the lower-level implementation:

- inside `houmao-server`, this is the official parser boundary
- under the hood, it still reuses the shared parser stack and parser presets already present in the repo

The parsing sequence is:

1. `supports_tool(tool)` checks whether the shared parser stack supports the tool.
2. On the first successful parse attempt for a tracker, `capture_baseline(tool, output_text)` stores the parser baseline offset into the tracker.
3. `parse(tool, output_text, baseline_pos)` runs `ShadowParserStack.parse_snapshot(...)`.
4. Parse failures are normalized through `as_shadow_parser_error(...)` and exposed as `HoumaoErrorDetail(kind="parse_error", ...)`.
5. Parse success is converted into `HoumaoParsedSurface`.

`HoumaoParsedSurface` includes parser family and preset metadata, plus the parsed TUI surface fields that matter to live tracking:

- `availability`
- `business_state`
- `input_mode`
- `ui_context`
- `normalized_projection_text`
- `dialog_text`, `dialog_head`, and `dialog_tail`
- `anomaly_codes`
- `baseline_invalidated`
- `operator_blocked_excerpt`

## Turn-Signal Detection

After capture and parse, `LiveSessionTracker` also runs tool-specific signal detection over the current raw `output_text` plus the optional `parsed_surface`.

This detector layer lives in [`../../../../src/houmao/server/tui/turn_signals.py`](../../../../src/houmao/server/tui/turn_signals.py) and is responsible for:

- foundational surface observables such as `accepting_input`, `editing_input`, and `ready_posture`
- current active-turn evidence that can come from more than visible spinner rows
- recognized interruption and narrow known-failure signatures
- success-candidate and success-blocker hints used by the shared settle logic

The server currently selects detectors by tool identity:

- Claude uses the proven `claude_code_state_tracking` detector wrapper
- Codex uses a conservative server-local detector
- everything else falls back to a minimal parsed-surface-based detector

This keeps tool/version string matching outside the shared turn reducer while still letting the public tracked-state contract expose one common `surface / turn / last_turn` model.

## Recorded Outcomes

The poll loop distinguishes failures and partial successes explicitly instead of compressing them into one status.

Important cycle outcomes are:

- tmux missing: `transport_state="tmux_missing"`, `process_state="unknown"`, `parse_status="transport_unavailable"`, then stop the worker
- tmux resolution failure: `probe_error.kind="tmux_probe_error"`, continue the worker
- process inspection failure: `probe_error.kind="process_probe_error"`, continue the worker
- unsupported tool: `process_state="unsupported_tool"` and `parse_status="unsupported_tool"`, continue the worker
- TUI down: `process_state="tui_down"` and `parse_status="skipped_tui_down"`, continue the worker
- tmux capture failure: `probe_error.kind="tmux_capture_error"`, continue the worker
- baseline capture failure: `parse_error.kind="parse_baseline_error"`, continue the worker
- parser failure: `parse_status="parse_error"` with structured `parse_error`, continue the worker
- parse success: `parse_status="parsed"` with a populated `parsed_surface`

All of these outcomes still flow through `LiveSessionTracker.record_cycle(...)`, so the server updates:

- low-level diagnostics
- parsed-surface evidence
- foundational `surface` observables
- simplified `turn` and `last_turn`
- generic stability
- recent transitions

This remains true even when the cycle ended in a probe or parse error.

## Related Sources

- [`../../../../src/houmao/server/service.py`](../../../../src/houmao/server/service.py)
- [`../../../../src/houmao/server/tui/transport.py`](../../../../src/houmao/server/tui/transport.py)
- [`../../../../src/houmao/server/tui/process.py`](../../../../src/houmao/server/tui/process.py)
- [`../../../../src/houmao/server/tui/parser.py`](../../../../src/houmao/server/tui/parser.py)
- [`../../../../src/houmao/server/tui/turn_signals.py`](../../../../src/houmao/server/tui/turn_signals.py)
- [`../../../../src/houmao/server/tui/tracking.py`](../../../../src/houmao/server/tui/tracking.py)
