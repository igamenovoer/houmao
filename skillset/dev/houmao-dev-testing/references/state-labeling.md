# Public-State Ground-Truth Rubric

## Workflow

1. **Read only raw terminal, runtime, and input evidence.** Do not inspect tracker or parser output.
2. **Identify sample ranges where the public meaning stays constant.** Keep boundaries at observable changes, inputs, runtime changes, and settle transitions.
3. **Assign all seven fields** using **Field Rubric** and record concrete evidence.
4. **Adjudicate ready-versus-busy operationally.** A submitted prompt must begin immediately for ready posture to be `yes`.
5. **Check complete, non-overlapping source coverage** and freeze the label set with the source digest.

If the evidence cannot determine a field, use the native planning tool to seek additional raw evidence from the same frozen run; if none exists, use `unknown` where valid and document the uncertainty instead of borrowing the detector's answer.

## Public Fields and Values

| Field | Allowed Values |
| --- | --- |
| `diagnostics_availability` | `available`, `unavailable`, `tui_down`, `error`, `unknown` |
| `surface_accepting_input` | `yes`, `no`, `unknown` |
| `surface_editing_input` | `yes`, `no`, `unknown` |
| `surface_ready_posture` | `yes`, `no`, `unknown` |
| `turn_phase` | `ready`, `active`, `unknown` |
| `last_turn_result` | `success`, `interrupted`, `known_failure`, `none` |
| `last_turn_source` | `explicit_input`, `surface_inference`, `none` |

## Field Rubric

### Diagnostics Availability

- `available`: the supported TUI is alive and the pane provides usable evidence.
- `tui_down`: runtime evidence shows the TUI process or pane is gone.
- `unavailable`: the surface exists but required diagnostics cannot be obtained.
- `error`: the observation/probe itself failed.
- `unknown`: evidence cannot distinguish the posture.

Use runtime observations for liveness claims. Do not infer `tui_down` from a quiet or blank-looking pane alone.

### Surface Accepting Input

Label whether the surface accepts user input at this moment. This may be `yes` while a turn remains active and submitted text would be queued. It is not a readiness verdict.

### Surface Editing Input

Label whether the user can currently edit a draft in the composer. A visible typed draft is strong evidence. Editing does not imply the CLI will process a submission immediately.

### Surface Ready Posture

Label `yes` only when a prompt submitted now would begin processing immediately instead of entering a CLI-owned queue or waiting for the current turn. Favor operational evidence from the next recorded submit and immediate surface response. Use `no` for a demonstrably busy/non-admitting surface and `unknown` for an ambiguous editor with no decisive outcome.

### Turn Phase

- `active`: the current turn is processing, including tool work, thinking, streaming, retry/reconnect activity, or other current live-edge evidence.
- `ready`: no turn remains in flight and immediate prompt processing is available.
- `unknown`: the surface does not support a reliable active/ready judgment.

A prompt glyph or visible composer does not end an active turn when stronger activity evidence remains.

### Last Turn Result

- `success`: the public settle contract has elapsed after a completed turn without blocking failure/ambiguity.
- `interrupted`: recorded input and surface evidence show intentional interruption.
- `known_failure`: a recognized terminal failure family completed the turn.
- `none`: no completed result is currently attributable, including active turns and ready recovery that must not manufacture success.

Apply the declared settle window, normally one second, as part of public ground truth. Label the pre-settle candidate span separately from settled success.

### Last Turn Source

- `explicit_input`: the result belongs to a recorded prompt or interrupt event.
- `surface_inference`: the result was inferred from the visible surface without authoritative input evidence.
- `none`: there is no attributable last result.

## Evidence Notes

Each range should cite concrete evidence such as:

- source sample IDs and elapsed interval
- exact managed input event or operation name
- visible live-edge status/tool/interrupt text
- draft presence and what happened on submit
- runtime observation showing pane or supported-process loss
- settle boundary calculation

Do not cite detector names, detector reasons, parser projections, tracker events, or comparison results in independent GT evidence.

## Range and Coverage Rules

- Ranges are inclusive and ordered by source sample ID.
- Every source sample has exactly one label.
- No ranges overlap or reverse.
- Every range contains all seven fields.
- Short ambiguous or transitional spans remain explicit; do not stretch a neighboring label across them for convenience.
- Derived streams do not get a separate ground-truth label set. They map back to canonical labels through `source_sample_id`.

## Admission Safety Priority

False-ready and sustained false-busy errors matter more than cosmetic boundary differences because downstream prompts depend on them. Label ready/busy boundaries conservatively but do not convert uncertainty into permanent busy. Preserve ambiguous spans as `unknown`, then let comparison report whether the implementation's behavior remains safe and useful.
