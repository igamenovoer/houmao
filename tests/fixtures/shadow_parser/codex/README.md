# Codex Variant Inventory

The Codex shadow parser currently covers these CAO `mode=full` variant families:

- Label style turn output (`You ...` + `assistant:` / `assistant>`)
- TUI bullet output (`› prompt` + `• answer` lines)
- Prompt/footer chrome (`›` idle prompt + `? for shortcuts` / `context left`)
- Approval prompts (`Approve ... [y/n]`, `Allow ... [y/n]`)
- Trust prompts (`Allow Codex to work in this folder? [y/n]`, `Do you trust the contents of this directory?`)
- Numbered option menus (`❯ 1. ...`, `2. ...`, with hint lines)

Fixture files:

- `label_completed.txt`
- `tui_completed.txt`
- `waiting_approval.txt`
- `waiting_trust_prompt.txt`
- `waiting_trust_prompt_v2.txt`
- `waiting_menu.txt`
- `drifted_unknown.txt`
