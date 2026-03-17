# Issue: CAO Claude Code `mode=last` Output Fails (Marker Mismatch), Falls Back to ANSI `mode=full`

## Status
Resolved in this repository on 2026-03-17.

## Resolution Summary
This repository's runtime no longer depends on CAO Claude `mode=last` extraction. Claude turns now use runtime-owned shadow parsing over `mode=full`, so the original marker mismatch no longer blocks normal Claude operation here.

## Summary

When using the vendored CAO server (`extern/orphan/cli-agent-orchestrator`) with provider `claude_code`, the endpoint:

- `GET /terminals/{terminal_id}/output?mode=last`

returns HTTP `404` with:

- `No Claude Code response found - no ⏺ pattern detected`

even when a valid Claude response is visible in `mode=full`. Downstream callers (including this repo's brain launch runtime) then fall back to `mode=full`, which is raw tmux scrollback and includes ANSI escape sequences and TUI chrome. This produces heavily styled/noisy `response_text` and can appear to "not answer the prompt".

## Resolution Status (Updated 2026-02-28)

This issue is now mitigated in this repository's runtime implementation:

- `src/agent_system_dissect/agents/realm_controller/backends/cao_rest.py` now
  uses a Claude-specific shadow path that:
  - does not use CAO `GET /terminals/{id}` `status` for Claude turn gating,
  - fetches only `mode=full` for Claude turns (no `mode=last` / `mode=tail` use),
  - extracts and returns plain assistant text via runtime-owned parsing.
- `src/agent_system_dissect/agents/realm_controller/backends/claude_code_shadow.py`
  adds versioned presets, bounded-tail shadow status parsing, baseline-aware
  completion gating, and explicit `waiting_user_answer` detection.

Upstream CAO provider behavior may still exhibit the original marker/status drift for
`claude_code`; the runtime no longer depends on those CAO semantics for Claude turns.

## Affected Components

- CAO Claude provider (response parsing + status detection):
  - `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/providers/claude_code.py`
  - `RESPONSE_PATTERN` (line ~28) hardcodes `⏺` (U+23FA)
  - `extract_last_message_from_script()` (line ~205) raises `ValueError` when no `⏺` marker exists
  - `PROCESSING_PATTERN` (line ~34) requires a parenthesized suffix `( … )`
- CAO output endpoint maps provider extraction errors to HTTP `404`:
  - `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/services/terminal_service.py`
  - `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py`
- CAO tmux history capture includes escape sequences:
  - `extern/orphan/cli-agent-orchestrator/src/cli_agent_orchestrator/clients/tmux.py`
  - `get_history()` uses `capture-pane -e -p` (line ~304)
- Brain launch runtime fallback behavior:
  - `src/agent_system_dissect/agents/realm_controller/backends/cao_rest.py`
  - `_get_terminal_output_with_fallback()` retries `mode=tail` (CAO does not implement it; returns `422`) then `mode=full`

## Reproduction (Minimal)

1. Start `cao-server` with `ANTHROPIC_*` credentials in the process environment so Claude Code is authenticated.
2. Create a Claude Code session:
   - `POST /sessions?provider=claude_code&agent_profile=developer`
3. Send input:
   - `POST /terminals/{id}/input?message=Reply+with+exactly:+OK`
4. Fetch output:
   - `GET /terminals/{id}/output?mode=full` (contains the visible response)
   - `GET /terminals/{id}/output?mode=last` (returns `404`)

## Observed Behavior (2026-02-28)

### 1) `mode=full` shows a response with `●` (U+25CF), not `⏺` (U+23FA)

ANSI-stripped excerpt:

```text
❯ Reply with exactly: OK
● OK
```

### 2) `mode=last` fails with HTTP 404

CAO server log excerpt:

```text
2026-02-28 06:54:16,354 - cli_agent_orchestrator.services.terminal_service - ERROR - Failed to get output from terminal ff14e4db: No Claude Code response found - no ⏺ pattern detected
```

### 3) Demo symptom: ANSI-heavy `response_text` and missing answer

From the demo run `tmp/demo_cao_claude_20260228_065232_705668/` (untracked), CAO requests show the fallback sequence:

```text
GET /terminals/<id>/output?mode=last  -> 404
GET /terminals/<id>/output?mode=tail  -> 422
GET /terminals/<id>/output?mode=full  -> 200
```

In the same demo's `report.json`, `response_text` contains tmux output with ANSI escape sequences. After stripping ANSI, the captured content still contains TUI prompts/spinners rather than a plain assistant answer:

```text
❯ Reply with a single short sentence about test coverage.
✽ Razzmatazzing…
❯
```

## Root Cause

1. **Response marker mismatch**:
   - CAO's Claude provider assumes Claude responses are prefixed by `⏺` (U+23FA).
   - Claude Code v2.1.62 prefixes responses with `●` (U+25CF).
   - Result: `extract_last_message_from_script()` finds no matches and raises, which the API maps to HTTP `404`.

2. **Processing detection mismatch (contributing to "missing answer")**:
   - `PROCESSING_PATTERN = r\"[✶✢✽✻·✳].*….*\\(.*\\)\"` requires a parenthesized suffix.
   - Newer Claude Code spinner lines can appear without parentheses (example: `✽ Razzmatazzing…`).
   - Result: CAO may misclassify a still-running turn as `IDLE` if the `❯` prompt is present, so callers may request output before any response marker exists.

## Why ANSI/TUI Styling Appears in `response_text`

CAO's `mode=full` returns raw tmux scrollback captured with `capture-pane -e -p`, which includes escape sequences for colors and TUI UI elements. ANSI stripping is only applied to the extracted last message path, but that path is currently failing, so callers end up consuming raw `mode=full`.

## Impact

- `mode=last` is currently unreliable/unusable for Claude Code v2.1.62 in this environment.
- Brain launch runtime can end up recording:
  - raw, ANSI-heavy transcripts, and/or
  - prompt/spinner text instead of the final assistant answer.

## Workarounds

- Runtime-side: on `mode=last` failure, fetch `mode=full`, strip ANSI, and heuristically extract the most recent assistant message.
- Remove `mode=tail` fallback unless CAO adds a supported "tail" output mode (today it returns `422` because `OutputMode` only defines `full` and `last`).

## Proposed Fix (Vendored CAO)

- `providers/claude_code.py`
  - Update `RESPONSE_PATTERN` to accept both `⏺` (U+23FA) and `●` (U+25CF).
  - Update extraction stop condition to recognize `❯` prompts in addition to `>` (and keep separator handling).
  - Relax `PROCESSING_PATTERN` so the parenthesized suffix is optional (match both old and new spinner variants).
- Optionally extend CAO API to support a real `mode=tail`, or remove downstream usage of it.
