## Context

The mailbox roundtrip tutorial pack already drives a full send/check/reply/check flow through `run_demo.sh`, and its pack-local scenario runner archives per-scenario demo roots for maintainers. However, the current fast integration harness stubs the `mail send`, `mail check`, and `mail reply` realm-controller commands with canned JSON results. That means successful automated scenarios can leave behind a bootstrapped mailbox layout without canonical message Markdown documents, projection symlinks, or mailbox-local unread state that matches the reported roundtrip.

This change is intentionally narrower than turning the demo into a fully live end-to-end CAO/tmux smoke test. The repo already has a real filesystem mailbox delivery stack plus existing test patterns that stage canonical Markdown documents and commit them with `deliver_message()`. The design goal is to reuse that real mailbox mutation path inside the hermetic automation harness so maintainers can inspect actual mailbox content under `<demo-output-dir>/shared-mailbox/` after automated runs.

## Goals / Non-Goals

**Goals:**

- Make successful mailbox roundtrip demo automation leave real canonical send and reply message documents in the selected demo mailbox root.
- Keep the existing scenario-runner and integration-test workflow hermetic and fast by reusing the managed filesystem mailbox delivery stack instead of requiring live remote services.
- Add automated assertions that the canonical send and reply bodies match the tracked tutorial input Markdown files and preserve correct thread linkage.
- Preserve the sanitized expected-report contract so snapshot refreshes remain stable and do not capture raw message body content.

**Non-Goals:**

- Replacing the fast fake-tool harness with a full live CAO/tmux/agent execution path.
- Changing mailbox protocol semantics, canonical message layout, or managed delivery scripts themselves.
- Turning the expected report snapshot into a golden copy of raw mailbox message bodies.
- Introducing a second demo output location for “real mailbox evidence”; the selected demo root remains the source of truth.

## Decisions

### 1. The fake integration harness will perform real filesystem-mailbox delivery for `mail send` and `mail reply`

The integration harness in `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_runner.py` should continue intercepting `pixi run python -m houmao.agents.realm_controller`, but its `mail send` and `mail reply` branches should stop returning canned success payloads without side effects. Instead, the harness should stage canonical Markdown documents from the actual `--body-file` inputs and commit them into the selected mailbox root with the managed delivery stack.

This keeps the test environment hermetic while making the mailbox root truthful: successful automation will now create canonical message files under `messages/<YYYY-MM-DD>/`, projection symlinks under `mailboxes/<address>/inbox|sent`, and shared/local SQLite state that corresponds to the reported roundtrip.

`mail check` should likewise derive its unread count from real mailbox-local state rather than a hard-coded number so the success path remains internally consistent.

Alternatives considered:

- Run the full demo against live agents and real backend control paths.
  Rejected because it would make the routine automation suite slower, more fragile, and harder to run in hermetic CI.
- Keep the current JSON-only stubs and add separate manual guidance for inspecting mail.
  Rejected because it does not solve the maintainer requirement: successful automated runs still would not leave inspectable mailbox content.

### 2. Real mailbox content assertions will live in tests and scenario evidence, not in the sanitized expected report

The pack-local scenario runner and its integration tests should inspect the mailbox root directly after successful scenarios. They should parse the canonical message Markdown documents, verify the send and reply bodies against the tracked `initial_message.md` and `reply_message.md` files, and assert that the reply threads back to the first message.

Machine-readable scenario outputs may record stable evidence such as canonical message paths, thread/message IDs, or boolean content-match checks, but they should not store entire raw message bodies unless there is a specific debugging need.

Alternatives considered:

- Add raw message bodies to `report.json` and the sanitized expected report.
  Rejected because it would blur the line between stable verification contract and inspectable runtime artifacts, and it would make snapshot updates noisy.
- Assert only message IDs or unread counts.
  Rejected because those values can be fabricated by a stub and do not prove that canonical mailbox content exists on disk.

### 3. Demo verification remains sanitized, while the demo mailbox root remains the inspectable truth

The mailbox roundtrip demo should continue using the sanitized report contract for `verify` and `--snapshot-report`. If the raw report needs additional mailbox-evidence fields, they should be limited to stable structural evidence that can be sanitized cleanly, such as placeholder-ready paths or booleans indicating presence.

The raw canonical send and reply bodies should remain inspectable in `<demo-output-dir>/shared-mailbox/` after successful `auto` or stepwise runs, including after `stop`. Fresh `start` or `auto` runs may still refresh the mailbox root before creating a new roundtrip, so inspection is tied to the completed demo root from that run.

Alternatives considered:

- Preserve previous mailbox content across successive fresh runs so evidence accumulates over time.
  Rejected because it would complicate rerun isolation and make scenario outcomes harder to reason about.

## Risks / Trade-offs

- [Harness realism grows and becomes harder to maintain] → Reuse the existing managed delivery helpers and shared mailbox parsing utilities instead of inventing mailbox mutations inside the test file by hand.
- [Unread-state expectations could drift from the real mailbox implementation] → Have the fake `mail check` path read mailbox-local SQLite state or equivalent mailbox-derived evidence rather than returning a fixed unread count.
- [Scenario outputs become noisy if they include too much mailbox data] → Record paths, IDs, and boolean matches; keep full bodies in the canonical mailbox files only.
- [Maintainers may inspect a mailbox root after a subsequent rerun has refreshed it] → Keep the selected demo output directory as the canonical inspection target and document that fresh `start`/`auto` runs replace mailbox content for that demo root.

## Migration Plan

No runtime migration or compatibility bridge is needed. Implementation should update the demo integration harness, scenario assertions, and any helper utilities in place. Existing expected-report snapshots should remain sanitized; if additional stable fields are introduced, refresh them through the existing verify flow.

## Open Questions

- None at proposal time. The main technical direction is to reuse managed mailbox delivery inside the hermetic harness rather than widening scope to live-agent execution.
