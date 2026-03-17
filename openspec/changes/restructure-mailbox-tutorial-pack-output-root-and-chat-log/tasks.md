## 1. Output-Root Contract

- [x] 1.1 Update the tutorial-pack layout helpers, CLI defaults, and documentation so the canonical default output root is `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/`.
- [x] 1.2 Add the disposable-output-root behavior for full runs and document that stepwise commands still reuse one prepared output root for the same run.
- [x] 1.3 Add a demo-local `.gitignore` rule so `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/` stays untracked.

## 2. Mailbox And Chat Outputs

- [x] 2.1 Move the canonical mailbox root to `<output-root>/mailbox` and update the tutorial-pack layout/report helpers, tests, and docs accordingly.
- [x] 2.2 Introduce `<output-root>/chats.jsonl` as the append-only semantic conversation log with stable event fields for time, sender, recipient, and content.
- [x] 2.3 Ensure the receiver's final tutorial reply is appended through a pack-owned structured write path instead of being reconstructed from TUI transcript extraction.

## 3. Input And Verification Model

- [x] 3.1 Update tracked tutorial inputs so they provide initial-message seed content plus reply-authoring instructions rather than a canned final reply body.
- [x] 3.2 Update live/unit/scenario verification to validate mailbox threading plus `chats.jsonl` structure and content, instead of exact reply-body equality against a tracked canned reply file.
- [x] 3.3 Refresh README guidance, expected sanitized-report assumptions, and any scenario evidence docs to reflect the new output-root and chat-log contract.
