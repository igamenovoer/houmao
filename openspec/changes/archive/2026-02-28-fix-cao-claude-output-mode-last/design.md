## Context

This repo vendors CAO (CLI Agent Orchestrator) under `extern/orphan/cli-agent-orchestrator`, but treats it as upstream code that we do not modify in this repo.

For CAO provider `claude_code`, CAO exposes:

- `GET /terminals/{terminal_id}/output?mode=full` (raw tmux scrollback, includes ANSI/TUI)
- `GET /terminals/{terminal_id}` (terminal metadata + CAO-computed status via provider regexes)
- `GET /terminals/{terminal_id}/output?mode=last` (CAO provider-extracted last assistant message; currently unreliable for Claude Code v2.1.62)

Today, CAO’s Claude Code provider frequently misclassifies terminal state and fails to extract the last response:
- marker mismatch (`⏺` expected vs `●` emitted),
- spinner-only lines not matched as processing, and
- prompt-boundary extraction bugs with ANSI-prefixed prompts.

This causes the brain launch runtime to request output too early and/or fall back to `mode=full`, producing ANSI-heavy transcripts and spinner/prompt UI instead of a plain answer.

Root causes (see `context/issues/known/issue-cao-claude-code-output-mode-last-marker-mismatch.md`):

- CAO Claude provider hardcodes response marker `⏺` (U+23FA), but Claude Code v2.1.62 prefixes responses with `●` (U+25CF).
- CAO `PROCESSING_PATTERN` requires a parenthesized suffix and misses spinner lines like `✽ Razzmatazzing…`, allowing early `idle` classification and premature output capture.
- `extract_last_message_from_script()` stop condition only recognizes `>` prompts and may over-capture under the `❯` prompt style.

## Goals / Non-Goals

**Goals:**

- For CAO-backed Claude Code sessions, always produce a plain, unstyled assistant answer for completed turns.
- Determine Claude Code `idle`/`processing`/`completed`/`waiting_user_answer` using runtime-owned logic that is robust to CAO provider regex drift.
- Avoid depending on CAO `mode=last` and CAO terminal `status` semantics for Claude Code turns.
- Provide an operational escape hatch to pin parsing presets when Claude Code output changes (`AGENTSYS_CAO_CLAUDE_CODE_VERSION`).
- Add tests that pin runtime parsing behavior against representative Claude Code tmux output samples.

**Non-Goals:**

- Modifying vendored CAO source code under `extern/orphan/cli-agent-orchestrator`.
- Adding a new CAO API output mode (for example `mode=tail`) in this change.
- Replacing tmux scrollback parsing with a structured Claude Code protocol (Claude Code TUI does not expose one via CAO today).
- Changing tmux capture behavior (`capture-pane -e`) across providers.

## Decisions

### 1) Shadow provider in the runtime (CAO as transport only)

**Decision:** For `tool=claude` with backend `cao_rest`, the runtime SHALL treat CAO as a transport for:
- sending input (`POST /terminals/{id}/input`), and
- fetching scrollback (`GET /terminals/{id}/output?mode=full`),

and SHALL perform status detection and last-message extraction locally from the `mode=full` text.

The runtime SHALL NOT use CAO `mode=last` or CAO terminal `status` for turn gating for Claude Code, because those values are derived from upstream regexes that are known to drift.

**Rationale:** We cannot patch CAO in this repo, and CAO's `claude_code` provider logic is currently the source of incorrect readiness/completion behavior. Owning the parsing in the runtime makes correctness depend only on what we can observe (`mode=full`) and what we can test.

**Alternative considered:** Patch CAO's `claude_code` provider (marker/spinner/prompt fixes). Rejected due to the "do not modify upstream CAO" constraint and the maintenance burden of carrying a fork.

### 2) Runtime-owned parsing presets resolved by version

**Decision:** Implement a version-to-preset registry inside this repo (runtime-side) that defines:
- response marker(s),
- spinner/processing rules,
- idle prompt rules, and
- separator line rules.

Version selection priority:
1) `AGENTSYS_CAO_CLAUDE_CODE_VERSION` env override (if set),
2) auto-detected version from the scrollback banner (e.g., `Claude Code v2.1.62`), and
3) latest known preset (fallback), using floor lookup for unknown versions.

**Rationale:** Keeps matching bounded to the expected version behavior and provides an operational escape hatch when upstream output changes.

**Note:** If version detection fails entirely (no banner/version found), the runtime falls back to the latest known preset. If those patterns do not match an older Claude Code build, set `AGENTSYS_CAO_CLAUDE_CODE_VERSION` to pin the correct preset.

### 3) Output-driven turn lifecycle (shadow status)

**Decision:** The runtime SHALL maintain a shadow terminal status for Claude Code derived from recent `mode=full` output. It SHALL:
- wait for `shadow_status == idle` before submitting a new prompt,
- after submitting, poll until `shadow_status == completed` (or `waiting_user_answer`) for that turn, and
- use a per-session cursor/baseline so completion detection requires a response marker that appears after prompt submission, not a marker from earlier scrollback.

`completed` is a first-class shadow status meaning: the terminal is idle and a preset-recognized response marker is present after the current turn baseline.

Baseline representation:
- Before prompt submission, capture `baseline_pos` as the character offset of the end of the last response marker match in the current `mode=full` output (or `0` if no match exists).
- If later `mode=full` output is shorter than `baseline_pos` (scrollback reset/truncation), treat the baseline as invalidated and fall back to requiring both a response marker and a stop boundary in the new output to declare completion.

To reduce false positives from stale scrollback, shadow status classification MUST operate on a bounded tail window rather than the entire history. Default:
- Shadow status: last 100 lines from the end of `mode=full` output.
- Answer extraction: all text after `baseline_pos` (no tail limit), to avoid truncating long answers.

**Rationale:** CAO status can be wrong; prompt characters can appear while processing; a cursor/baseline is needed to distinguish a new answer from earlier output.

### 4) Never return raw tmux output as the answer

**Decision:** For Claude Code, the runtime SHALL never return raw `mode=full` scrollback as the user-visible response text. It SHALL return:
- extracted plain answer text on success, or
- a clear extraction failure with a short ANSI-stripped tail excerpt for debugging.

**Rationale:** Returning tmux UI output is the failure mode users observe today.

### 5) Waiting-user-answer is surfaced as an explicit error

**Decision:** If the runtime detects `waiting_user_answer` for Claude Code, it SHALL fail the turn with an explicit error and include an ANSI-stripped excerpt showing the selection options.

**Rationale:** The runtime does not yet provide a programmatic "send choice" mechanism for interactive selection UI. Failing loudly is more honest than returning partial output or hanging.

### 6) Prevent accidental reliance on CAO status endpoints

**Decision:** All Claude Code readiness/completion waits in the runtime MUST go through the shadow-status path. Code paths that currently call `GET /terminals/{id}` for gating (for example generic “wait for ready” loops) SHALL be bypassed for Claude Code sessions.

For this change, the runtime will implement this via explicit `tool == "claude"` branching in `cao_rest.py`. A separate dedicated session class (for stronger regression resistance) is a follow-up consideration.

**Rationale:** The easiest way to regress is to "reuse" a generic CAO wait loop. Making the Claude path explicit prevents accidental coupling to CAO provider semantics.

## Risks / Trade-offs

- **[More polling / bigger payloads]** → Mitigation: parse bounded tail windows; consider caller-configurable tail limits for status checks.
- **[Heuristic parsing drift]** → Mitigation: versioned presets + `AGENTSYS_CAO_CLAUDE_CODE_VERSION` override + tests with representative samples.
- **[Waiting-user-answer flows]** → Mitigation: detect and surface `waiting_user_answer` explicitly rather than treating it as completion.

## Migration Plan

- Implement runtime-side Claude Code scrollback parser + shadow status.
- Update CAO REST backend to use the shadow path for Claude Code (and remove unsupported `mode=tail` fallback).
- Add unit tests for parser behavior without requiring live tmux sessions.
- Re-run the existing CAO Claude demo to confirm the runtime receives a plain answer without falling back to returning raw `mode=full`.

## Open Questions

- Should we follow up by splitting out a dedicated `CaoRestClaudeSession` class to make regressions harder (instead of keeping explicit `tool == "claude"` branches in `cao_rest.py`)?
