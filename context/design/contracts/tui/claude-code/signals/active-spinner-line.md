# Active Spinner Line

**Verified CLI Version:** `Claude Code 2.1.81` for capture-backed evidence, within the maintained `2.1.x` detector family

## Chosen Signal

The current Claude signal stack uses the latest-turn spinner line as the primary active-turn signal. The stable part of that signal is the rotating leading symbol plus the ellipsis-form line, not the changing verb text.

Examples observed in real captures:

- `✽ Ionizing…`
- `✻ Ionizing…`
- `· Vibing…`
- `✢ Vibing…`
- `✽ Frolicking…`
- `✶ Frolicking…`
- `· Skedaddling…`
- `* Skedaddling…`

## Why This Signal Is Chosen

- It is directly tied to the current active Claude turn.
- It remains reliable even when Claude changes the verb text across versions.
- It stays usable when the footer looks similar in both ready and active states.
- It is visible during overlapping-draft cases where the current prompt already contains the next draft.

## Why The Alternatives Were Rejected

### Reject: footer working-summary line

Why rejected:

- the footer line `⏵⏵ bypass permissions on ...` appears in both ready and active surfaces
- `esc to…` in the footer is useful context but not decisive active authority by itself

Observed failure:

- relying on the footer makes it too easy to misclassify a ready surface as active

### Reject: the verb text itself

Why rejected:

- verbs drift across versions and sessions:
  `Ionizing…`, `Vibing…`, `Frolicking…`, `Skedaddling…`
- the stable part is the spinner-symbol form, not the wording

## Evidence

### Real capture evidence

From `capture-20260323T123329Z`:

- `s000011`: `✽ Ionizing…`
- `s000012`: `✻ Ionizing…`
- `s000068`: `· Vibing…`
- `s000069`: `✢ Vibing…`

From `capture-20260323T124200Z`:

- `s000011` onward: `Frolicking…` with rotating leading symbols
- `s000112` onward: `Skedaddling…` with rotating leading symbols

The changing verbs demonstrate why the symbol-plus-ellipsis shape is the chosen stable cue.

### Operational evidence

The complex fixture authoring workflow was updated so Claude `wait_for_active` requires spinner evidence rather than footer summary text.

### Tests that lock this in

- `tests/unit/demo/test_shared_tui_tracking_demo_pack.py::test_wait_for_active_requires_spinner_evidence_for_claude`

## Current Use

Current implementation points:

- `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`
  - `SPINNER_LINE_RE`
  - `thinking_line` active reason

Current operational use:

- demo-pack `wait_for_active` for Claude
- tracked-TUI active classification during both normal active turns and overlapping-draft active turns
