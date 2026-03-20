# Codex Interrupted Signal

## Context

- Source-inspected on 2026-03-20
- Tool: Codex TUI (app-server variant)
- Local source checkout: `extern/orphan/codex`
- Source revision: `fa2a2f0be94e744d6d565a803e12c870d283f930`
- Primary source artifacts:
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/history_cell.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget/snapshots/codex_tui_app_server__chatwidget__tests__interrupted_turn_error_message.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget/snapshots/codex_tui_app_server__chatwidget__tests__replayed_interrupted_reconnect_footer_row.snap`
- Intent: define one concrete Codex interruption surface that returns to a ready prompt

## Classification

When this signal matches, the tracked turn outcome is:

- terminal outcome: `turn_interrupted`
- current posture after the interrupted turn returns: `turn_ready`

## Required Conditions

All conditions below MUST be true in the same latest-turn surface.

1. A visible red error cell contains the exact hardcoded interruption text:
   `Conversation interrupted - tell the model what to do differently. Something went wrong? Hit \`/feedback\` to report the issue.`
2. That line is rendered using Codex's generic red error-cell shape `■ <message>`
3. The active status row is no longer visible for that turn
4. The composer is visible again and accepting input, either with the default placeholder or with restored draft text
5. If a background-terminal footer remains visible, it is informational footer text rather than a still-running turn status row

Representative latest-turn interruption surface:

```text
■ Conversation interrupted - tell the model what to do differently. Something went wrong? Hit `/feedback` to report the issue.

› Ask Codex to do anything
```

Representative shell-backed live variant from recorder sample `s001009`:

```text
• Running sleep 30 in the shell now, then I'll return the exact requested response.

■ Conversation interrupted - tell the model what to do differently. Something went wrong? Hit `/feedback` to report the issue.

  1 background terminal running · /ps to view · /stop to close

› Use /skills to list available skills
```

## Why This Matches

Source inspection shows that ordinary interrupted turns follow this path:

1. `on_interrupted_turn()` finalizes the turn and clears running state
2. it inserts the exact red error event above into history
3. it restores queued or draft user input back into the composer when applicable
4. the ready composer remains visible after replayed interrupted reconnects instead of leaving a stale `Working` row behind

The live shell-backed sample adds one operational detail:

- an interrupted turn can return to ready posture while a separate background-terminal footer still remains visible
- that footer does not by itself mean the current turn is still active

## Non-Match Guidance

- Do not infer interruption from the disappearance of the `Working` row alone
- Do not infer interruption from a red `■ ...` error cell alone unless the exact interruption text matches
- Do not infer interruption from restored draft text alone
- Do not infer interruption from the alternate info message `Model interrupted to submit steer instructions.` because that path is tied to immediate steer resubmission and does not guarantee the same ready-return surface
- Do not let the informational footer `1 background terminal running · /ps to view · /stop to close` block interruption recognition once the exact interruption error and ready composer are already visible
- Do not infer interruption from request-user-input overlays that merely contain `esc to interrupt`; those are interactive modal surfaces, not completed interruption results

## Notes

- This note defines the ordinary Codex ready-return interruption pattern only
- The interruption text is exact and source-backed, so it is much safer than using generic red error styling alone
- The same red error-cell renderer is used for many non-interruption errors, so interruption detection must stay anchored on the exact message text
- Live recorder validation: `tmp/terminal_record/codex-signal-check-20260320/` sample `s001009`
- Current analyzer gap: the corresponding `state_observed.ndjson` sample still flattened `s001009` to `idle` + `ready`, so raw pane evidence is currently the stronger authority
