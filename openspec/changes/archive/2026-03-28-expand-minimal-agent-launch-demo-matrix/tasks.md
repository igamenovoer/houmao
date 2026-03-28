## 1. Runner And Outputs

- [x] 1.1 Update the minimal demo runner so `--provider` defaults to TUI and `--headless` selects the headless lane for the supported matrix.
- [x] 1.2 Partition generated outputs by lane so Claude/Codex and TUI/headless runs do not overwrite each other ambiguously.
- [x] 1.3 Make TUI launches preserve and report tmux handoff outputs, including the attach command for non-interactive callers.

## 2. Demo Docs

- [x] 2.1 Update the minimal demo tutorial to document all four supported lanes: Claude headless, Claude TUI, Codex headless, and Codex TUI.
- [x] 2.2 Update `scripts/demo/README.md` so the supported demo description reflects the full provider/transport matrix instead of a headless-first interpretation.

## 3. Verification

- [x] 3.1 Run and verify the Claude headless and Claude TUI lanes, then fold the observed outputs into the tutorial verification/troubleshooting notes.
- [x] 3.2 Run and verify the Codex headless and Codex TUI lanes, then fold the observed outputs into the tutorial verification/troubleshooting notes.
