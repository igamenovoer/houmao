# Claude Code Interrupted Signal

## Context

- Observed on 2026-03-20 in tmux session `gig-3`
- Tool: Claude Code
- Command-reported version: `claude --version` -> `2.1.80 (Claude Code)`
- Visible UI banner version during observation: `v2.1.80`
- Intent: define one concrete known interruption pattern for the simplified turn model

## Classification

When this signal matches, the tracked turn outcome is:

- terminal outcome: `turn_interrupted`
- current posture after the interrupted turn returns: `turn_ready`

## Required Conditions

All three conditions below MUST be true in the same observed surface. This is a conjunctive matcher, not a heuristic.

1. A visible line contains the exact text `Interrupted · What should Claude do instead?`
2. That line is a `⎿` continuation/status line
3. A fresh `❯` input prompt is visible after that interrupted line

If any one of the three conditions is missing, the tracker SHALL NOT emit `turn_interrupted` from this pattern alone.

## Non-Match Guidance

- Do not treat the bottom status strip `⏵⏵ bypass permissions on (shift+tab to cycle)` as the interruption signal
- Do not infer interruption from a fresh `❯` prompt alone
- Do not infer interruption from an `⎿` line alone
- Do not infer interruption from the interrupted text alone if a later fresh `❯` prompt is not visible
- If the full pattern is not present, fall back to other supported signals or `turn_unknown`

## Example Surface

```text
❯ learn about this codebase

● Explore(Explore houmao codebase structure)
  ⎿  Read(docs/reference/houmao_server_pair.md)
     Read(src/houmao/server/cli.py)
     Bash(find /data1/huangzhe/code/houmao/src/houmao -name "*.py" | wc -l)
     +39 more tool uses (ctrl+o to expand)
  ⎿  Interrupted · What should Claude do instead?

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on (shift+tab to cycle)
```

## Notes

- The interrupted turn may be a plain text prompt or a tool-using turn; the matcher is anchored on the visible interrupt marker and the returned ready prompt, not on the specific turn contents
- This note defines a Claude-specific known interruption pattern only. Other tools need their own signal notes
