# Claude Code Colored L-Shaped Error Signal

## Context

- Observed on 2026-03-20 in tmux session `gig-3`
- Tool: Claude Code
- Command-reported version: `claude --version` -> `2.1.80 (Claude Code)`
- Visible UI banner version during observation: `v2.1.80`
- Intent: define one concrete known-failure frame for the simplified turn model without depending on a specific error message string

## Classification

When this signal matches, the tracked turn outcome is:

- terminal outcome: `turn_known_failure`
- current posture after the known-failure turn returns: `turn_ready`

## Required Conditions

All conditions below MUST be true in the same observed surface. This matcher intentionally uses structure and ANSI color, not a specific message string.

1. A visible Claude continuation/status line is present, beginning with `⎿`
2. That `⎿` continuation/status line contains an error-bearing text segment rendered in a highlighted ANSI foreground color rather than the surrounding neutral gray status color
3. A bottom status-area message is also visible, and it contains an error-bearing text segment rendered in the same highlighted ANSI foreground color
4. A fresh `❯` input prompt is visible after that continuation/status line
5. The upper colored `⎿` error line and the lower colored status-area message visually form the L-shaped Claude error frame for the same surface
6. The colored `⎿` continuation/status line is the latest relevant Claude status/result line for the current prompt posture; it is not superseded by a later neutral or non-error `⎿` line

For the observed `gig-3` sample on Claude Code `2.1.80`, the highlighted error color was `38;5;211m` and the surrounding neutral/status text was predominantly `38;5;246m`.

If any one of these conditions is missing, the tracker SHALL NOT emit this known-failure pattern from this signal note alone.

## Observed ANSI Evidence

The two error-bearing regions observed from `tmux capture-pane -e` were:

```text
[38;5;246m[49m  ⎿  [38;5;211mNot logged in · Please run /login[39m
...
[39m  [38;5;246m? for shortcuts[39m                                                                                                                     [38;5;211mNot logged in · Run /login[39m
```

Interpretation:

- `⎿` is present on the continuation/status line
- the main error text on that line is colored `38;5;211m`
- the bottom status-area error text is also colored `38;5;211m`
- surrounding neutral/status text is gray (`38;5;246m`), which helps separate the error-bearing region visually
- the upper colored status line plus the lower colored status-area message form the L-shaped error frame

## Non-Match Guidance

- Do not require any one specific error message string such as `Not logged in`
- Do not infer this known failure from colored text alone if the `⎿` continuation/status line is absent
- Do not infer this known failure from a colored `⎿` continuation/status line alone if the lower colored status-area message is absent
- Do not infer this known failure from a lower colored status-area message alone if the colored `⎿` continuation/status line is absent
- Do not infer this known failure if the colored `⎿` error line is only stale history and a later neutral or non-error `⎿` status/result line is now the latest relevant Claude line
- Do not infer this known failure from generic color changes alone without the prompt-return structure and the upper-plus-lower L-shaped frame
- If the full pattern is not present, fall back to other supported known-failure rules or `turn_unknown`

## Example Surface

```text
❯ hi
  ⎿  Not logged in · Please run /login

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ? for shortcuts                                                                                                                     Not logged in · Run /login
```

## Notes

- This is a Claude-specific known-failure rule based on a visual error frame, not on one exact error string
- The observed example uses `Not logged in`, but the message text is incidental; the matcher cares about the colored `⎿` status line, the colored lower status-area message, and the returned prompt together
- The color requirement is intentional because the error-bearing text is visually separated from ordinary status text by the highlighted foreground color in both the continuation/status line and the bottom status area
- Recency matters. A sticky lower colored status-area message does not keep the current surface in known-failure if a later non-error `⎿` result line has already superseded the older colored error line

## Non-Match Example

The following surface MUST NOT be treated as a current known failure from this rule alone:

```text
❯ hi
  ⎿  Not logged in · Please run /login

❯ /model
  ⎿  Set model to Sonnet 4.6 (default)

────────────────────────────────────────────────────────────────────────────────
❯ I am typing something, not sent yet...
────────────────────────────────────────────────────────────────────────────────
                                                                                                                                      Not logged in · Run /login
```

Reason:

- the lower colored status-area message is still visible
- but the latest relevant `⎿` status/result line is now the later neutral `/model` result
- the older colored `⎿` error line is stale history, so the current surface is not in known failure from this rule
