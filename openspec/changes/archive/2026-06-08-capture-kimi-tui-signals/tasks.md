## 1. Recorder and Replay Tooling

- [x] 1.1 Add `kimi` as a supported terminal-record tool identity for `start` and replay/analyze paths.
- [x] 1.2 Add or verify high-rate sampling support for about 10 fps capture with `--sample-interval-seconds 0.1`.
- [x] 1.3 Ensure Kimi capture roots can be created under `tmp/kimi-tui-tracking/<run-id>/`.
- [x] 1.4 Ensure pane snapshots preserve ANSI/style data and record enough target metadata for replay.
- [x] 1.5 Add derived-stream tooling that creates about 2 fps snapshots from a high-rate source stream while preserving source sample ids.
- [x] 1.6 Make pane snapshot capture remain replay-grade when the human-facing cast recorder exits or degrades, with explicit taint metadata.
- [x] 1.7 Extend terminal-record labels to support Kimi sample ranges, parser-facing expectations, public tracked-state expectations, and evidence notes.

## 2. Live Kimi Capture Corpus

- [x] 2.1 Capture at least 5 development live Kimi sessions at about 10 fps, with each session spanning multiple TUI state changes.
- [x] 2.2 Capture at least 3 held-out test live Kimi sessions at about 10 fps, with each session spanning multiple TUI state changes and kept out of detector design/tuning.
- [x] 2.3 Ensure the combined development corpus covers idle/editor-ready, draft editing, prompt submit, active response, completed response, ready return, approval prompt, approval rejection, interrupt, and footer-thinking-metadata states.
- [x] 2.4 Ensure the held-out test corpus includes overlapping state families without reusing the exact development prompts or interaction sequence.
- [x] 2.5 Derive an about 2 fps stream for every development and held-out test session.
- [x] 2.6 Record Kimi CLI version, source reference version or commit context, terminal size, theme/color mode, sample interval, input authority, and scenario notes for every capture run.

## 3. Manual Labels and Signal Contracts

- [x] 3.1 Manually label ready, draft, active, completed, approval-blocked, approval-rejected, interrupted, and footer-metadata ranges across the captured scenarios.
- [x] 3.2 Investigate Kimi TUI source code for editor, footer, activity spinner, approval panel, modal, and message-rendering components.
- [x] 3.3 Create `openspec/changes/capture-kimi-tui-signals/context/` artifacts summarizing capture runs, source-code findings, scenario intent, and notable observations.
- [x] 3.4 Create `openspec/changes/capture-kimi-tui-signals/design/` artifacts explaining Kimi structural anchors, style facts, temporal facts, and bounded semantic regions.
- [x] 3.5 Create `openspec/changes/capture-kimi-tui-signals/contracts/` artifacts defining the Kimi signal contract, source-backed stability rationale, and replay oracle fields.
- [x] 3.6 Review labels and signal contracts against development 10 fps and 2 fps streams before writing detector rules.
- [x] 3.7 Keep held-out test labels available for acceptance validation without using them to tune detector rules.

## 4. Kimi TUI Tracking Implementation

- [x] 4.1 Add the Kimi shared tracker app id and profile registration scaffold.
- [x] 4.2 Implement Kimi prompt/editor region extraction from raw ANSI-preserving snapshots.
- [x] 4.3 Implement Kimi style-aware prompt and modal classification based on the signal contract.
- [x] 4.4 Implement Kimi current activity detection using current-turn/live-edge structural and temporal evidence.
- [x] 4.5 Implement Kimi approval-blocked detection from approval panel structure and bounded command/tool regions.
- [x] 4.6 Ensure footer metadata such as model `thinking` text does not create active-turn evidence by itself.
- [x] 4.7 Implement Kimi temporal hints for transcript growth, spinner cadence, and stable return to ready when labels prove they are needed.

## 5. Replay Validation and Tests

- [x] 5.1 Add Kimi replay/analyze support that emits parser-facing and shared tracked-state observations from recorded snapshots.
- [x] 5.2 Add strict validation that compares Kimi replay output against labeled public tracked-state fields.
- [x] 5.3 Add optional parser-state validation for labeled Kimi modal and approval ranges.
- [x] 5.4 Verify every required Kimi scenario against both high-rate and derived low-rate streams in the development corpus.
- [x] 5.5 Verify held-out Kimi test sessions separately and report their pass/fail status as the acceptance gate.
- [x] 5.6 Promote compact curated Kimi fixtures or fixture metadata for deterministic unit tests.
- [x] 5.7 Add unit tests for Kimi detector profile resolution, prompt classification, activity detection, approval detection, and footer metadata handling.

## 6. Integration and Documentation

- [x] 6.1 Update terminal-record reference and developer docs for Kimi capture, high-rate sampling, derived streams, and labels.
- [x] 6.2 Update shared TUI tracking docs to describe the Kimi signal-contract workflow and evidence-first gate.
- [x] 6.3 Update the active `add-kimi-tui-support` change so its Kimi parser/profile work depends on this capture corpus and signal contract.
- [x] 6.4 Run `openspec status --change capture-kimi-tui-signals` and fix artifact issues.
- [x] 6.5 Run `openspec validate capture-kimi-tui-signals --type change --strict`.
- [x] 6.6 Run focused recorder, replay, Kimi detector, and shared tracker tests.
- [x] 6.7 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
