# Codex Interactive Overlay Signals

## Context

- Source-inspected on 2026-03-20
- Tool: Codex TUI (app-server variant)
- Local source checkout: `extern/orphan/codex`
- Source revision: `fa2a2f0be94e744d6d565a803e12c870d283f930`
- Primary source artifacts:
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/mod.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/approval_overlay.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/request_user_input/mod.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/mcp_server_elicitation.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/app_link_view.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/snapshots/codex_tui_app_server__bottom_pane__approval_overlay__tests__approval_overlay_permissions_prompt.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/request_user_input/snapshots/codex_tui_app_server__bottom_pane__request_user_input__tests__request_user_input_options.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/snapshots/codex_tui_app_server__bottom_pane__mcp_server_elicitation__tests__mcp_server_elicitation_approval_form_with_param_summary.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/snapshots/codex_tui_app_server__bottom_pane__app_link_view__tests__app_link_view_install_suggestion_with_reason.snap`
- Intent: define Codex modal/operator-interaction surfaces that should degrade to `turn_unknown` rather than manufacturing `turn_active`, `turn_ready+success`, or `turn_known_failure`

## Shared Classification

When any overlay signal in this note matches, the tracked current turn state is:

- current posture: `turn_unknown`

This note does not define a terminal outcome.

## Shared Source Facts

The bottom pane source does all of the following when these overlays are pushed:

- pauses the status timer for the modal
- disables normal composer input with a modal-specific continuation message
- pushes the modal view onto the active bottom-pane stack

Source tests also confirm that the normal `Working` overlay row is not rendered above an approval modal.

Interpretation:

- these are dedicated operator-interaction surfaces
- they must not be collapsed into ordinary active or ready posture

## Overlay Group A: Approval Modal

### Matching Surface

A visible modal approval view with all of the following:

1. an approval title such as:
   - `Would you like to run the following command?`
   - `Would you like to grant these permissions?`
   - `Would you like to make the following edits?`
   - `<server_name> needs your approval.`
2. numbered selectable options such as `1. Yes ...`, `2. No ...`
3. a footer like `Press enter to confirm or esc to cancel` or `... or o to open thread`

Representative surface:

```text
  Would you like to grant these permissions?

  Reason: need workspace access

  Permission rule: network; read `/tmp/readme.txt`; write `/tmp/out.txt`

› 1. Yes, grant these permissions (y)
  2. Yes, grant these permissions for this session (a)
  3. No, continue without permissions (n)

  Press enter to confirm or esc to cancel
```

### Classification

- current posture: `turn_unknown`

### Non-Match Guidance

- Do not treat this as `turn_active` even if a running turn caused the modal to appear
- Do not treat this as `turn_ready`
- Do not treat denial/cancel options as a terminal known failure from this surface alone

## Overlay Group B: Request-User-Input Modal

### Matching Surface

A visible modal question view with all of the following:

1. a progress header like `Question <n>/<m> (<k> unanswered)`
2. a question body
3. option rows and/or a notes/freeform composer
4. footer controls such as:
   - `tab to add notes | enter to submit answer | esc to interrupt`
   - `enter to submit all | ctrl + p / ctrl + n change question | esc to interrupt`
   - unanswered-confirmation footer `Press enter to confirm or esc to go back`

Representative surface:

```text
  Question 1/1 (1 unanswered)
  Choose an option.

› 1. Option 1  First choice.
  2. Option 2  Second choice.
  3. Option 3  Third choice.

  tab to add notes | enter to submit answer | esc to interrupt
```

### Classification

- current posture: `turn_unknown`

### Non-Match Guidance

- Do not treat the footer text `esc to interrupt` as generic active-turn evidence
- Do not treat this as `turn_ready`
- Do not treat the unanswered-confirmation subview as a success/failure terminal result

## Overlay Group C: MCP Server Elicitation Form

### Matching Surface

A visible form view with all of the following:

1. a header like `Field <n>/<m>` or `Field <n>/<m> (<k> required unanswered)`
2. an elicitation prompt such as `Allow this request?` or a tool-specific message
3. form fields or approval-action choices
4. footer text `enter to submit | esc to cancel`

Representative surface:

```text
  Field 1/1
  Allow Calendar to create an event

  Calendar: primary
  Title: Roadmap review
  Notes: This is a deliberately long note that should truncate bef...

  › 1. Allow   Run the tool and continue.
    2. Cancel  Cancel this tool call

  enter to submit | esc to cancel
```

### Classification

- current posture: `turn_unknown`

### Non-Match Guidance

- Do not classify this as `turn_active` from the presence of a form alone
- Do not classify this as `turn_ready`
- Do not classify a visible `Cancel` option as a terminal interruption or known failure by itself

## Overlay Group D: App-Link / Tool-Suggestion View

### Matching Surface

A visible suggestion modal with all of the following:

1. an app or tool name and description
2. instructional text about installing or enabling the app
3. numbered actions such as `Install on ChatGPT`, `Enable app`, or `Back`
4. footer text like `Use tab / ↑ ↓ to move, enter to select, esc to close`

Representative surface:

```text
  Google Calendar
  Plan events and schedules.

  Plan and reference events from your calendar

  Install this app in your browser, then return here.
  Newly installed apps can take a few minutes to appear in /apps.
  After installed, use $ to insert this app into the prompt.

  › 1. Install on ChatGPT
    2. Back
  Use tab / ↑ ↓ to move, enter to select, esc to close
```

### Classification

- current posture: `turn_unknown`

### Non-Match Guidance

- Do not treat this as `turn_ready`
- Do not treat this as `turn_active` from the modal alone
- Do not treat this as a terminal known failure or interruption

## Current Design Implications

- Codex modal/operator-interaction surfaces are explicit and numerous; they should collapse into `turn_unknown` unless stronger active or terminal evidence exists elsewhere
- Footer strings like `esc to interrupt` or `enter to submit` are reused across different overlays and are not safe lifecycle signals by themselves
- Modal appearance can temporarily hide the normal busy row, so "no Working row visible" does not automatically imply `turn_ready`
