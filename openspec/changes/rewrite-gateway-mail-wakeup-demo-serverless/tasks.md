## 1. Fixture And Output-Root Preparation

- [ ] 1.1 Define the rewritten pack-local output ownership model, including tool-scoped roots under `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/<tool>/` and a pack-local `.gitignore` for generated artifacts.
- [ ] 1.2 Update tracked demo inputs so the pack selects Claude and Codex serverless defaults from `tests/fixtures/agents` instead of the old single-lane pair-managed defaults.
- [ ] 1.3 Decide and implement the tracked fixture path for live Claude/Codex serverless startup, including any required recipe or blueprint additions under `tests/fixtures/agents`.

## 2. Serverless Runner Rewrite

- [ ] 2.1 Replace the old pair-managed orchestration with a serverless runner that initializes the pack-local mailbox root, launches one selected tool through `houmao-mgr`, registers mailbox support, attaches the gateway, and enables notifier polling.
- [ ] 2.2 Rework the manual workflow commands so `start`, `manual-send`, `manual-send-many`, `inspect`, `verify`, and `stop` all target the same persisted serverless run state.
- [ ] 2.3 Add tool selection and a matrix-capable automatic flow that runs one tool per live run while preserving separate tool-scoped artifacts.
- [ ] 2.4 Keep mail injection on the managed filesystem delivery boundary and remove direct dependence on demo-owned `houmao-server` or `houmao_server_rest`.

## 3. Inspection, Verification, And Reporting

- [ ] 3.1 Rebuild inspect artifact generation around serverless managed-agent, gateway, mailbox, and output-file evidence.
- [ ] 3.2 Update report sanitization and golden verification so the contract checks processed-message read state, notifier audit evidence, output-file completion, and pack-local output ownership.
- [ ] 3.3 Refresh `expected_report/report.json` and any pack-local helper surfaces to match the rewritten serverless artifact model.

## 4. Documentation

- [ ] 4.1 Rewrite the pack README to teach the serverless `houmao-mgr` mailbox and gateway workflow, separate Claude/Codex usage, unread-set semantics, and the pack-local output-root model.
- [ ] 4.2 Update any operator-facing notes or appendix material so the documented commands, artifacts, and snapshot-refresh steps match the rewritten runner.

## 5. Coverage

- [ ] 5.1 Rewrite unit coverage for the demo pack around the serverless flow, pack-local ownership rules, and the new sanitized-report contract.
- [ ] 5.2 Add or refresh a real-agent or autotest path that exercises both Claude Code and Codex against the rewritten serverless wake-up contract with separate tool-scoped artifacts.
