# Kimi TUI Signal Contract

Maintained Kimi Code TUI tracking applies to Kimi Code `0.11.x` and compatible later versions that keep the same pi-tui component structure. The current implemented profile is `kimi_code` detector version `0.11.x`; unmatched versions resolve to a conservative fallback profile.

Required parser-facing fields for recorded Kimi replay:

- `business_state=idle`, `input_mode=freeform`, `ui_context=normal_prompt` when the editor prompt is visible and no current-turn active or modal evidence is present.
- `business_state=working`, `input_mode=none`, `ui_context=normal_prompt` when current-turn spinner or temporal growth evidence is present.
- `business_state=awaiting_operator`, `input_mode=modal`, `ui_context=approval` when a bounded approval panel is visible.

Required public tracked-state fields:

- Ready editor: `diagnostics_availability=available`, `surface_accepting_input=yes`, `surface_editing_input=no`, `surface_ready_posture=yes`, `turn_phase=ready`.
- Draft editing: `surface_accepting_input=yes`, `surface_editing_input=yes`, `surface_ready_posture=yes`, `turn_phase=ready`.
- Active response: `surface_accepting_input=no`, `surface_editing_input=no`, `surface_ready_posture=no`, `turn_phase=active`.
- Approval blocked: `surface_accepting_input=no`, `surface_editing_input=no`, `surface_ready_posture=no`, `turn_phase=active`, plus parser `awaiting_operator/modal/approval`.
- Completed success: stable empty editor after an active turn settles to `last_turn_result=success`, `last_turn_source=surface_inference`.
- Interrupted turn: current-turn interruption notice plus empty editor yields `turn_phase=ready`, `last_turn_result=interrupted`, `last_turn_source=surface_inference`.
- Footer metadata: footer model text containing `thinking` does not by itself change a ready editor into active.

Forbidden primary signals:

- Full exact assistant text, full footer tip strings, release banners, welcome text, and old transcript rows outside the bounded current-turn/live-edge region.
- Exact RGB values or terminal dimensions as required contract signals.
- `session.cast` as machine replay source of truth. The authoritative stream is `pane_snapshots.ndjson`.

Acceptance oracle:

- Development corpus: five labeled live sessions must pass high-rate and derived low-rate validation.
- Held-out corpus: three separately labeled live sessions must pass high-rate and derived low-rate validation. These sessions guard against overfit detector rules.
- Validation pass/fail compares labels against public tracked-state fields and optional parser-facing fields. Diagnostic notes and matched fragments are not pass criteria.
