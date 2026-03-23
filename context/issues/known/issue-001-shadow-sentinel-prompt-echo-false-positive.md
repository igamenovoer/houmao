# Issue 001: Shadow Mailbox Sentinel Prompt-Echo False Positive

## Priority
P0 — Mailbox turns fail intermittently in production.

## Status
Fixed on `devel` as of 2026-03-18. Archived OpenSpec change: `openspec/changes/archive/2026-03-18-fix-shadow-mailbox-sentinel-prompt-echo/`.

## Review Reference
Code review sections: 2.3, 4.4

## Summary

The mailbox-specific shadow completion observer and the final mailbox result parser used different detection logic for sentinel-delimited result blocks. The provisional gate treated arbitrary `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` substrings anywhere in the surface as sufficient evidence, while the final parser expected standalone delimiter lines around valid JSON.

When the runtime-owned mailbox prompt echoed sentinel names in prose and in the appended `response_contract` JSON fields, the observer declared "contract reached" prematurely. The final parser then rejected the surface because it contained multiple sentinel-name occurrences rather than one actual sentinel-delimited result block.

## Root Cause

Two independent detection paths (loose `str.find()` substring gate vs. strict block parser) applied to the same text surface, with no shared contract.

## Affected Code

- `src/houmao/agents/realm_controller/mail_commands.py` — `extract_sentinel_blocks()`, `shadow_mail_result_contract_reached()`, `parse_mail_result()` / `_parse_mail_result_text()`
- `src/houmao/agents/realm_controller/backends/cao_rest.py` — `_build_mail_shadow_completion_observer()`

## Fix Applied

Replaced the dual-path sentinel detection with a single `extract_sentinel_blocks()` function:
1. Scans for sentinel-on-own-line patterns (not substrings)
2. Returns zero or more `SentinelBlock(begin_line, end_line, payload_text)` candidates
3. Shared between BOTH the provisional completion observer AND the final parser

The provisional gate becomes: "Does `extract_sentinel_blocks()` return at least one candidate?" The final parser validates the candidate(s) against the active request contract.

Regression coverage added in `tests/unit/agents/realm_controller/test_mail_commands.py`.

## Connections

- Amplified by problem 2.6 (fresh-environment TUI noise adds extra text that contains echoed sentinels)
- Companion fix to issue-007 (observer gated behind generic completion). Together these two fixes close the mailbox shadow completion reliability gap:
  - issue-001 fixed the false positive (observer too loose)
  - issue-007 fixed the false negative (observer gated too late)
