# Enhancement Proposal: Mail Subcommands Should Remove `--instruction` and Require Explicit Body Inputs

## Status
Resolved on 2026-03-17.

## Resolution Summary
The mail CLI now requires explicit body inputs through `--body-file` or `--body-content`, and the runtime-owned mailbox request payload no longer depends on `instruction` for send or reply body creation.

## Summary
Tighten the runtime mailbox CLI so `mail send` and `mail reply` do not accept `--instruction` and instead require explicit mail content inputs such as:
- `--body-file <path>`
- `--body-content <string>`

The goal is to keep the mail surface about structured mailbox operations and avoid overlapping with the repo's existing prompt-oriented subcommands such as `send-prompt`.

## Why
Current behavior mixes two different concerns:
- mailbox transport operations (`mail send`, `mail reply`, `mail check`)
- generic agent prompting (`send-prompt` and related runtime control)

Today, `mail send --instruction "..."` means "ask the live agent to compose and send a message with this intent." That is flexible, but it creates overlap and ambiguity:
- the mail command becomes a prompt channel instead of a pure mailbox command,
- operator intent and final message content are conflated,
- it is harder to reason about what exact mail content is being sent,
- mailbox UX starts to depend on prompt-style freeform composition rather than explicit message payloads,
- the contract becomes less stable for automation, tests, and future non-agent mail producers.

If the mail subcommand is meant to be a mailbox operation surface, it should accept explicit mail body content, not prompt-like instructions that ask the agent to improvise the final message body.

## Requested Enhancement
1. Remove `--instruction` from `mail send` and `mail reply`.
2. Require explicit content input instead, with at least:
   - `--body-file <path>`
   - `--body-content <string>`
3. Keep `--subject`, `--to`, `--cc`, `--message-id`, and attachment args as mailbox-operation fields, but make body input explicit rather than intent-driven.
4. Ensure the runtime-owned mailbox request payload carries explicit body content instead of an instruction string.
5. Reserve prompt-like composition flows for existing prompt-oriented commands such as `send-prompt`, not the mailbox CLI surface.
6. Update docs, examples, and help text so the mail contract is clearly "explicit mailbox content in, mailbox action out."

## Acceptance Criteria
1. `mail send --instruction "..."` fails with a clear error or is no longer accepted.
2. `mail reply --instruction "..."` fails with a clear error or is no longer accepted.
3. `mail send` accepts explicit content through `--body-file` and `--body-content`.
4. `mail reply` accepts explicit content through `--body-file` and `--body-content`.
5. Runtime mailbox request payloads no longer depend on an `instruction` field for send or reply body creation.
6. Docs and examples use explicit body inputs for mail commands.
7. Tests cover both accepted explicit-body flows and rejected `--instruction` usage.

## Non-Goals
- No requirement to remove agent-mediated mailbox execution entirely.
- No requirement to redesign the `mail check` command.
- No requirement to eliminate richer future composition helpers, as long as they do not overload the mailbox CLI with generic prompting semantics.
- No requirement to solve recipient-address validation in the same enhancement, though it aligns well with stricter mail contracts.

## Suggested Follow-Up
- Pair this with `context/issues/enhance/enhance-mail-send-requires-full-mailbox-address.md` so the mail CLI becomes stricter on both recipient identity and body-content semantics.
- Decide whether `--body-content` should accept plain text, Markdown only, or both.
- Consider whether a future higher-level helper should compose draft content first and then call `mail send` with explicit body content, rather than making `mail send` itself a composition prompt surface.
