# Kimi TUI Source Investigation

Source reference: `extern/orphan/kimi-code/apps/kimi-code/src/tui/` at commit `b64f3b4`.

Stable component findings:

- Editor: `components/editor/custom-editor.ts` extends pi-tui `Editor`, injects a visible `> ` prompt token into the first editor content row, and wraps editor output with box borders (`╭`, `╰`, `│`). The detector treats the bordered prompt row as a structural anchor. Draft text is taken only from that bounded row.
- Footer: `components/chrome/footer.ts` renders model name plus optional ` thinking` as model capability/status metadata and separately renders `context:` usage on the second footer line. The detector treats footer `thinking` as metadata unless the current-turn region contains spinner or transcript-growth evidence.
- Activity pane: `kimi-tui.ts` switches activity modes from `waiting`, `thinking`, `composing`, and `tool`. It creates moon spinners for waiting/tool modes and a braille spinner labeled `working...` for composing. `components/chrome/moon-loader.ts` owns spinner frames and cadence.
- Thinking transcript: `components/messages/thinking.ts` renders live thinking with braille frames and `thinking...`. This is current-turn evidence when it appears in the live-edge region above the editor, not when the word `thinking` appears in the footer.
- Approval panel: `components/dialogs/approval-panel.ts` renders a bounded horizontal-rule panel. `headerFor()` returns short semantic headers such as `Run this command?`, `Write this file?`, and `Apply these edits?`. The panel renders display blocks such as `cwd:` and `$ <command>` for shell approvals, followed by numbered choices. Default approval choices are defined in `reverse-rpc/approval/adapter.ts` as `Approve once`, `Approve for this session`, `Reject`, and `Reject with feedback`.
- Approval rejection transcript: `kimi-tui.ts` records approval outcomes with transcript status content such as `Rejected: <action>` for non-plan tool approvals. Live captures showed Kimi may either summarize the rejected tool call and return ready, or retry the same tool and show another approval panel.
- Interruption: `controllers/editor-keyboard.ts` maps Escape and Ctrl+C to stream cancellation while streaming. `controllers/session-event-handler.ts` renders `Interrupted by user` when the interrupted turn reason is user abort. The detector scopes this to the current-turn/live-edge region.

Signals treated as accidental or fragile:

- Full assistant wording, full footer tips, release/update banners, welcome text, and rotating keyboard hints.
- Exact terminal width, exact color numbers, and exact theme choices. The detector may use raw ANSI style roles such as dim/normal prompt payload and focused/bordered regions, but the contract does not depend on one RGB value.
- Old transcript rows above the current live edge. Stale spinner or approval text above a later ready editor must not control current state.
