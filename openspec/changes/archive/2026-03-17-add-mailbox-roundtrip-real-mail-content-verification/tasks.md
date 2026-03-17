## 1. Hermetic Real-Mail Delivery

- [x] 1.1 Update the mailbox roundtrip demo integration harness in `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_runner.py` so fake `mail send` and `mail reply` commands stage canonical Markdown documents from the real `--body-file` inputs and commit them with the managed filesystem mailbox delivery stack.
- [x] 1.2 Update the fake `mail check` path and any related demo helper assumptions so unread counts and thread/message metadata come from real mailbox state instead of hard-coded synthetic success payloads.

## 2. Mailbox Inspection Evidence

- [x] 2.1 Add reusable mailbox inspection helpers for the mailbox roundtrip demo tests to locate canonical message documents, parse them, and compare send/reply bodies plus thread linkage against the tracked tutorial input files.
- [x] 2.2 Extend the pack-local scenario runner and successful scenario outputs to record stable inspection evidence such as canonical message paths, message IDs, or boolean content-match checks without embedding raw message bodies into tracked snapshots.
- [x] 2.3 Keep `verify` and snapshot behavior sanitized by limiting any new report evidence to stable structural fields and leaving raw canonical message content on disk under the demo mailbox root.

## 3. Regression Coverage And Validation

- [x] 3.1 Extend mailbox roundtrip integration coverage to assert that successful `auto` and stepwise scenarios leave inspectable canonical send and reply documents plus mailbox projections under the scenario demo root.
- [x] 3.2 Add or update targeted unit coverage around any new mailbox inspection or evidence helpers so body matching and thread-link validation are exercised independently of the scenario runner.
- [x] 3.3 Run targeted mailbox demo tests and `pixi run openspec validate --strict --json --type change add-mailbox-roundtrip-real-mail-content-verification`.
