# Issue 001: Shadow Mailbox Sentinel Prompt-Echo False Positive

## Priority
P0 — Mailbox turns fail intermittently in production.

## Status
Known. OpenSpec change exists: `openspec/changes/fix-shadow-mailbox-sentinel-prompt-echo/`.

## Review Reference
Code review sections: 2.3, 4.4

## Summary

The mailbox-specific shadow completion observer and the final mailbox result parser use different detection logic for sentinel-delimited result blocks. The provisional gate treats arbitrary `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` substrings anywhere in the surface as sufficient evidence, while the final parser expects standalone delimiter lines around valid JSON.

When the runtime-owned mailbox prompt echoes sentinel names in prose and in the appended `response_contract` JSON fields, the observer declares "contract reached" prematurely. The final parser then rejects the surface because it contains multiple sentinel-name occurrences rather than one actual sentinel-delimited result block.

## Root Cause

Two independent detection paths (loose `str.find()` substring gate vs. strict block parser) applied to the same text surface, with no shared contract.

## Affected Code

- `src/houmao/agents/realm_controller/mail_commands.py` — `_contains_complete_mail_result_payload()`, `shadow_mail_result_contract_reached()`, `parse_mail_result()` / `_parse_mail_result_text()`
- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_build_mail_shadow_completion_observer()`

## Fix Direction

Replace the dual-path sentinel detection with a single `extract_sentinel_blocks()` function:
1. Scan for sentinel-on-own-line patterns (not substrings)
2. Return zero or more `SentinelBlock(begin_line, end_line, payload_text)` candidates
3. Share this function between BOTH the provisional completion observer AND the final parser

The provisional gate becomes: "Does `extract_sentinel_blocks()` return at least one candidate?" The final parser validates the candidate(s) against the active request contract.

## Connections

- Amplified by problem 2.6 (fresh-environment TUI noise adds extra text that contains echoed sentinels)
- HTT worktree cascade layer 4 (see issue-005)
- Already tracked in `openspec/changes/fix-shadow-mailbox-sentinel-prompt-echo/`
