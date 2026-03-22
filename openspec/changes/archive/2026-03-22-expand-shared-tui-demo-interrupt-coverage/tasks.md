## 1. Scenario Intents

- [x] 1.1 Extend the shared TUI demo scenario model to support semantic `interrupt_turn` and `close_tool` actions alongside the existing low-level actions.
- [x] 1.2 Implement recorder-driven execution for the new semantic actions with tool-specific Claude and Codex recipes, keeping raw `send_key` and kill-style actions available for debugging.
- [x] 1.3 Add repeated-lifecycle scenario definitions for Claude and Codex that drive two distinct prompts, two intentional interrupts, and a final intentional close.

## 2. Sweep Semantics

- [x] 2.1 Extend the demo config boundary/models/schema so sweep contracts can express repeated or ordered transition expectations for repeated-lifecycle cases.
- [x] 2.2 Update sweep evaluation and reporting to enforce the stronger repeated-transition contract shape instead of only first-occurrence label presence.
- [x] 2.3 Add or revise sweep definitions in the demo config for the repeated intentional-interruption cases while preserving the documented 2 Hz robustness floor.

## 3. Documentation

- [x] 3.1 Update the demo README case matrix and authoring workflow to document the new repeated intentional-interruption coverage and the distinction between semantic interrupt/close intents and low-level debug actions.
- [x] 3.2 Update the ground-truth and config reference docs to explain how repeated interrupted turns and final close posture are labeled and judged.

## 4. Fixture Authoring

- [x] 4.1 Capture a temporary Claude repeated intentional-interruption authoring run and label both interrupted turns plus the final close posture from pane snapshots.
- [x] 4.2 Capture a temporary Codex repeated intentional-interruption authoring run, identify a working interrupt recipe that yields an honest interrupted-ready public state, and label the resulting lifecycle from pane snapshots.
- [x] 4.3 Validate the temporary repeated-lifecycle fixtures without mismatches, generate review video, and promote the canonical replay-grade artifacts into the committed fixture corpus.
- [x] 4.4 Update the maintained first-wave fixture matrix so the canonical corpus includes the new repeated-interruption cases without removing the current single-interrupt cases.

## 5. Verification

- [x] 5.1 Add or update unit tests for scenario parsing, sweep-contract parsing, and repeated-transition evaluation.
- [x] 5.2 Run targeted demo-pack verification, including recorded validation for the affected fixtures, cadence sweeps for the repeated-lifecycle cases, and the relevant unit test suite.
