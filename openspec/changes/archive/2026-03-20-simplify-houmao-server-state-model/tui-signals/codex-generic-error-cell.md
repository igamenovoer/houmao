# Codex Generic Error Cell Signal

## Context

- Source-inspected on 2026-03-20
- Tool: Codex TUI (app-server variant)
- Local source checkout: `extern/orphan/codex`
- Source revision: `fa2a2f0be94e744d6d565a803e12c870d283f930`
- Primary source artifacts:
  - `extern/orphan/codex/codex-rs/tui_app_server/src/history_cell.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/snapshots/codex_tui_app_server__history_cell__tests__error_event_oversized_input_snapshot.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget/snapshots/codex_tui_app_server__chatwidget__tests__interrupted_turn_error_message.snap`
- Intent: define what the generic red error cell is strong enough to mean, and what it is not strong enough to mean

## Classification

When this signal matches, it establishes:

- normalized evidence: `current_error_present=yes`

This note does not, by itself, emit:

- `last_turn=known_failure`
- `last_turn=interrupted`
- `last_turn=success`

## Required Conditions

All of the following are true:

1. A visible latest-turn history line matches the Codex generic error-cell structure `■ <message>`
2. That line is the red plain-history error renderer produced by `new_error_event()`
3. That error cell is still the latest relevant error-bearing result for the current turn and has not been superseded by a later ready/success/active surface for a newer turn

Representative generic error surface:

```text
■ Message exceeds the maximum length of 1048576 characters (1048577 provided).
```

## What This Means

The generic red error cell is strong enough to mean:

- the latest relevant turn surface currently contains an error-bearing result
- success for that same latest turn must be blocked

The generic red error cell is not strong enough to mean:

- a specifically recognized known-failure class
- interruption, unless the exact interruption note also matches

Reason:

- source inspection shows the same renderer is used for many heterogeneous situations
- one of those situations is the dedicated interruption message, but many others are generic failures or local validation problems

Live recorder validation on 2026-03-20 matched that source reading:

- recorder run root: `tmp/terminal_record/codex-signal-check-20260320/`
- sample `s001009` showed the same red generic error cell shape carrying the exact interruption message, with a ready composer already visible again
- so the red cell shape itself still was not enough; the exact text remained the deciding feature

## Success-Blocking Rule

If the latest relevant turn surface contains a current generic red error cell, the tracker SHALL NOT emit:

- `turn_ready` with `last_turn=success`

from that surface alone.

Instead:

- keep `current_error_present=yes`
- use a more specific rule if one matches
- otherwise degrade the public outcome to `turn_unknown` rather than manufacturing `known_failure`

## Non-Match Guidance

- Do not emit `known_failure` from a generic red `■ <message>` cell alone
- Do not emit `interrupted` from a generic red `■ <message>` cell alone unless the exact interruption text matches the dedicated interruption note
- Do not let an older stale red error cell in scrollback block success for a later newer turn
- Do not confuse yellow warning cells such as `⚠ ...` with the red generic error-cell renderer
- Do not assume the current tracker already recognizes every live red error cell correctly; in recorder run `codex-signal-check-20260320`, `state_observed.ndjson` still flattened the interrupted red error sample to `idle` + `ready`

## Current Design Implications

- This source pass does not justify a Codex-specific `known_failure` rule from generic red error styling alone
- The Codex generic error cell is best treated as `current_error_present` evidence plus a success blocker
- Specific terminal results should only be emitted from narrower exact-message or structurally unique Codex rules
