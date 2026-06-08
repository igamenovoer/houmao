# Kimi TUI Signal Design

The Kimi profile uses minimal current-surface signals in this order:

1. Explicit input events when available. The initial corpus is output-only, so validation relies on visible draft/active/terminal-state evidence.
2. Structural anchors: editor box, prompt row, approval panel horizontal rules, approval header region, and current-turn/live-edge region above the editor.
3. Style facts: raw ANSI is preserved; prompt payload with dim styling is treated as placeholder-like, while non-dim non-empty payload is treated as typed draft. The contract avoids exact color numbers.
4. Temporal facts: recent frame growth in the current-turn region can mark activity when no spinner is visible. This hint is conservative and disabled when approval, interruption, or typed draft is current.
5. Bounded semantics inside source-backed regions: short approval headers, numbered approval choices, `cwd:`/`$` shell display rows, and `Interrupted by user`.
6. Exact text fragments only as bounded role tokens or diagnostics, never as a full-sentence primary detector.

Prompt/editor extraction:

- Find the latest stripped row matching the Kimi editor side border plus `> ` prompt token.
- Trim the right editor border before extracting prompt text.
- Confirm editor-box posture from nearby top/bottom border rows when visible.
- Classify prompt payload as `empty`, `placeholder`, `slash`, or `typed`. `typed` means ordinary draft editing.

Activity extraction:

- Build the current-turn region as a bounded window above the latest prompt row.
- Treat moon spinner rows and braille `working...` or `thinking...` rows in that region as active evidence.
- Use transcript-growth temporal hints only across contiguous recent frames and only when the latest editor is empty, no approval panel is visible, and no interruption is visible.
- Ignore footer model `thinking` unless the live-edge region has separate active evidence.

Approval extraction:

- Detect an approval panel only inside a bounded horizontal-rule region with a source-backed approval header and numbered approval choices.
- Emit parser-facing `business_state=awaiting_operator`, `input_mode=modal`, `ui_context=approval`.
- Emit public state `surface_accepting_input=no`, `surface_editing_input=no`, `surface_ready_posture=no`, `turn_phase=active`. The model vocabulary does not have a separate blocked turn phase, so active means the turn is not complete and is waiting on operator approval.

Interruption extraction:

- Detect `Interrupted by user` or `step interrupted` only in the current-turn/live-edge region.
- Emit public `last_turn_result=interrupted`, `last_turn_source=surface_inference`, and ready posture when the empty editor has returned.

Replay validation:

- Labels cover source sample id ranges. Derived 2 fps frames validate against the same labels through `source_sample_id` mapping.
- Success labels start only after the settle timer is stable at both sampling cadences.
- Held-out labels were written after the detector passed development validation and were not used to tune the detector.
