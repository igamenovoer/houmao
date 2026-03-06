# Demo Re-Run: fix-cao-claude-output-mode-last

Date: 2026-02-28
Command:

```bash
bash scripts/demo/cao-claude-session/run_demo.sh
```

## Result

- Status: **SKIP** (demo script exit `0` with skip classification)
- Workspace:
  - `tmp/demo_cao_claude_20260228_102738_864639`
- Prompt stage error (`prompt.log`):

```text
error: Timed out waiting for Claude Code terminal 81314e9d to become ready from mode=full shadow status
```

## Evidence Collected

- The CAO server log for this run shows repeated Claude output fetches using:
  - `GET /terminals/81314e9d/output?mode=full`
- No `mode=last` or `mode=tail` requests were observed during the prompt stage.
- Claude Code version confirmed from terminal pipe log: **v2.1.62**.
- Terminal pipe log (`~/.aws/cli-agent-orchestrator/logs/terminal/81314e9d.log`) shows:
  - Claude Code launched successfully and rendered the welcome box.
  - The idle prompt rendered with ghost/placeholder text: `❯ Try "fix typecheck errors"`.
  - Auto-update attempted and failed: `✗ Auto-update failed · Try claude doctor or npm i -g @anthropic-ai/c…`.

## Root Cause

The shadow parser's `_is_idle_prompt_line` rejected idle prompt lines carrying
ghost/placeholder text.  Claude Code v2.1.62 renders autocomplete suggestions
on the prompt line (e.g. `❯ Try "fix typecheck errors"`).  After ANSI stripping,
`tmux capture-pane` output contains this text as plain characters.

The previous implementation only accepted:

1. A bare idle prompt char (`❯`), or
2. The prompt char followed by whitespace and a cursor block character (`▌`, `█`, etc.).

The ghost text `Try "fix typecheck errors"` matched neither case, so every poll
classified the terminal as `processing`.  After the 120-second timeout the
runtime raised the observed error.

## Bugfix

**File:** `src/gig_agents/agents/brain_launch_runtime/backends/claude_code_shadow.py`

`_is_idle_prompt_line` now returns `True` for any line starting with an idle
prompt character followed by a space, regardless of trailing content (ghost text,
cursor block chars, typed input, etc.).

```python
# Before
trailing = trimmed[1:].strip()
if not trailing:
    return True
return trailing in _PROMPT_TRAILING_CHARS

# After
return trimmed[1].isspace()
```

**Tests added** (`tests/unit/agents/brain_launch_runtime/test_claude_code_shadow_parser.py`):

- `test_claude_shadow_status_idle_with_ghost_text_on_prompt_line` — verifies
  `classify_shadow_status` returns `idle` when the prompt line has ghost text.
- `test_claude_shadow_extract_stops_at_ghost_text_prompt_line` — verifies
  `extract_last_answer` stops extraction at a ghost-text prompt line.

All 14 shadow parser unit tests pass after the fix.

## Notes

- This run did **not** reach a completed Claude answer, so task `4.1` remains open.
- A secondary issue observed: Claude Code auto-update fired and failed during
  startup.  This did not directly cause the timeout (the ghost-text prompt was
  already undetectable) but may have caused additional screen redraws that
  compounded the problem.  Consider pinning the Claude Code version or disabling
  auto-update in the demo environment to avoid future interference.

## Follow-up Re-Run (2026-02-28 11:01 UTC)

Command:

```bash
DEMO_TIMEOUT_SECONDS=240 bash scripts/demo/cao-claude-session/run_demo.sh
```

Result:

- Status: **PASS**
- Workspace:
  - `tmp/demo_cao_claude_20260228_105922_897518`
- Report:
  - `tmp/demo_cao_claude_20260228_105922_897518/report.json`
- Plain assistant response captured:
  - `Unit tests live in tests/unit/ and are run with pytest tests/unit/.`
- Prompt event payload confirms shadow extraction path:
  - `output_mode: full`
  - `shadow_status: completed`
  - `shadow_preset_version: 2.1.62`

CAO server log evidence:

- Requests during prompt stage were `GET /terminals/<id>/output?mode=full` only.
- No `mode=last` or `mode=tail` requests were issued.

Claude Code version evidence:

- `~/.aws/cli-agent-orchestrator/logs/terminal/e3ae78ff.log` contains
  `Claude Code v2.1.62` in the terminal banner.
