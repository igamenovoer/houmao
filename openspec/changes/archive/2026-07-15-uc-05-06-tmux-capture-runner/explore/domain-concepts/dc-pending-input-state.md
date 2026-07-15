# Pending-Input State

## Language

**`can_accept_input`**:
A binary ground-truth label (with `unknown` allowed during transitions) that is `yes` when the provider TUI is non-busy and a new prompt submitted now would start immediately as an independent turn.
_Avoid_: Using `ready` alone; the detector target is the operational admission decision, not the visual presence of a prompt composer.

**`has_pending_message`**:
A binary ground-truth label (with `unknown` allowed during transitions) that is `yes` when the provider TUI visibly holds user text that has already been accepted for a later turn while the current turn remains active.
_Avoid_: Confusing this with a draft that has not been submitted; `has_pending_message` requires visible provider-native evidence that the text is queued for the next turn.

**`busy_pending_input`**:
An older UC-05/UC-06 independent behavioral label for the same state that `has_pending_message=yes` describes. It is retained here as descriptive background but is not the canonical detector-training label for this change.
_Avoid_: Using `busy_pending_input` in the binary label template; use `has_pending_message` instead.

**`pending_input` (active reason)**:
The tracker's current detector-internal signal that a visible pending-input signature is present. It appears in `active_reasons` while the public `turn_phase` remains `active`. This is implementation evidence, not a ground-truth label.
_Avoid_: Treating `active_reasons` containing `pending_input` as equivalent to `has_pending_message` without explicit mapping logic.

## Relationships

- `can_accept_input=yes` implies `has_pending_message=no` and `turn_phase=ready` in the current tracker schema.
- `has_pending_message=yes` implies `can_accept_input=no` and, in the current tracker, `turn_phase=active` with an `active_reasons` entry for pending input.
- A sample may be `can_accept_input=no` and `has_pending_message=no` while the CLI is simply busy with no queued text.
- The lifecycle transition sequence is:
  1. `can_accept_input=yes`, `has_pending_message=no`
  2. first prompt submitted
  3. `can_accept_input=no`, `has_pending_message=no` (processing)
  4. second prompt submitted
  5. `can_accept_input=no`, `has_pending_message=yes` (pending)
  6. pending consumed and processed
  7. `can_accept_input=yes`, `has_pending_message=no` (done)

## Flagged Ambiguities

- The UC-05 use case text calls this concept both a "pending instruction" and "pending input." For this change the canonical detector-training labels are `can_accept_input` and `has_pending_message`.
- UC-05 acceptance criterion 8 says the public tracker state should expose `turn_phase=busy_pending_input`. That is a future tracker schema target, not the current implementation. Until a separate product change promotes it, `has_pending_message` is recorded only in the independent label file.
