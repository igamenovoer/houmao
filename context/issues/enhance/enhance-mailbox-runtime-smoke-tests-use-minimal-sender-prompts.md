# Enhancement Proposal: Mailbox Runtime Smoke Tests Should Use Minimal Sender Prompts

## Status
Proposed

## Summary

The current real-agent mailbox tutorial/smoke path sends a runtime-owned prompt that asks the sender to do too much for a narrow runtime-contract test.

Today the sender prompt combines:

- mailbox skill discovery,
- shared-rule discovery,
- helper/requirements discovery,
- mailbox operation execution,
- mailbox configuration summarization,
- reply-oriented tutorial framing.

That is a poor fit for a simple `mail send` runtime smoke test. In practice it gives Claude and Codex many valid opportunities to explore the environment before doing the one thing the test actually needs: emit one valid mailbox result block for a small mailbox operation.

For smoke tests, the prompt should be much smaller and the test matrix should be split into narrow operations.

## Why

The March 18, 2026 real-agent HTT runs made the mismatch obvious.

The sender prompt was nominally testing mailbox send completion, but the live sender spent time on:

- searching for the mailbox skill,
- searching for rules and env context,
- inspecting unrelated local paths,
- trying to infer setup details before acting.

That behavior is not irrational. The prompt currently invites it.

For a runtime smoke test, this creates the wrong contract:

```text
test goal:
  prove one runtime-owned mailbox command can complete

current prompt:
  understand mailbox environment + inspect rules + inspect helper requirements
  + perform send + summarize mailbox config + preserve tutorial semantics

result:
  agent reasoning dominates the test instead of the mailbox runtime contract
```

The runtime bug surface becomes harder to diagnose because failures can come from:

- prompt complexity,
- exploration drift,
- mailbox tool use,
- parser/runtime behavior,
- or actual mailbox transport logic.

## Proposed Direction

### 1. Add a minimal sender-only smoke prompt shape

For `mail send` smoke tests, prefer a much smaller runtime-owned prompt such as:

```text
Send one mailbox message using the filesystem mailbox already configured for this session.

Do not search the repo for additional docs or skills.
Use the mailbox bindings already present in the session.

To: AGENTSYS-mailbox-receiver@agents.localhost
Subject: ping
Body:
ping

Return exactly one JSON object between AGENTSYS_MAIL_RESULT_BEGIN and AGENTSYS_MAIL_RESULT_END.
```

The intent is:

- one small mailbox action,
- one small expected result,
- minimal room for exploratory interpretation.

### 2. Shrink the structured request payload for smoke mode

Smoke-mode mailbox prompts should carry only the fields needed for the operation, for example:

```json
{
  "operation": "send",
  "request_id": "mailreq-...",
  "to": ["AGENTSYS-mailbox-receiver@agents.localhost"],
  "subject": "ping",
  "body_content": "ping"
}
```

Avoid tutorial-oriented extras unless the test explicitly needs them.

### 3. Split the live test matrix by mailbox operation

Instead of making one tutorial roundtrip carry all concerns, add distinct live/runtime tests such as:

1. sender `mail send` smoke only
2. receiver `mail check` smoke only
3. receiver `mail reply` smoke only
4. full tutorial roundtrip, only where higher-level behavior is intentionally under test

That separation lets failures identify the narrow broken layer more quickly.

### 4. Keep richer tutorial prompts only for tutorial coverage

The current richer prompt is still reasonable for:

- tutorial/demo UX coverage,
- proving a more realistic agent-guided mailbox workflow,
- end-to-end documentation-oriented demos.

But that richer prompt should not be the default pass path for the narrowest real-agent smoke contract.

### 5. Make the narrow prompt explicit in docs and fixtures

The repository should distinguish between:

- `smoke` mailbox prompts: minimal, operation-specific, runtime-contract focused
- `tutorial` mailbox prompts: richer, explanatory, workflow-oriented

That distinction should be visible in:

- test fixtures,
- demo helpers,
- and mailbox-runtime docs.

## Acceptance Criteria

1. The repo has a narrow real-agent `mail send` smoke path that uses a minimal sender prompt instead of the current tutorial-style prompt.
2. Smoke-mode prompts explicitly discourage repo/skill discovery unless required by the operation.
3. Smoke-mode request payloads are reduced to the minimum fields needed for the mailbox operation.
4. Live smoke coverage is split so `send`, `check`, and `reply` can be exercised independently.
5. The richer tutorial roundtrip path remains available for tutorial/demo coverage but is no longer the only real-agent mailbox path.
6. Docs explain when to use minimal smoke prompts versus richer tutorial prompts.

## Likely Touch Points

- `src/houmao/agents/realm_controller/mail_commands.py`
- `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`
- `scripts/demo/mailbox-roundtrip-tutorial-pack/README.md`
- live mailbox/demo tests under `tests/integration/demo/`
- mailbox runtime contract tests under `tests/integration/agents/realm_controller/`

## Non-Goals

- No requirement to remove the current tutorial-style prompt entirely.
- No requirement to weaken mailbox safety checks for non-smoke flows.
- No requirement to redesign the mailbox result schema itself.
- No requirement to solve all live-agent drift purely through prompt simplification.

## Suggested Follow-Up

1. Add a dedicated smoke-mode prompt builder for mailbox operations.
2. Introduce operation-specific real-agent tests for `send`, `check`, and `reply`.
3. Keep the current tutorial pack as a separate higher-level workflow test.
4. Decide whether smoke mode should bypass skill/rules narration entirely or keep one short reference to session-provided mailbox bindings.
