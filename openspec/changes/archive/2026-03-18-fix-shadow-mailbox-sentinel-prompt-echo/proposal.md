## Why

The current `shadow_only` mailbox completion gate can still treat prompt-echo text as if it were evidence that a sentinel-delimited mailbox result is present. In live sender runs, the echoed mailbox prompt itself contains the sentinel names in both prose and the appended JSON request contract, which lets the runtime exit provisional polling too early and then fail with a misleading multi-sentinel parse error.

## What Changes

- Tighten mailbox-specific shadow completion gating so prompt-echo surfaces do not count as mailbox-result evidence by themselves.
- Make mailbox result detection require an actually valid active-request result block, not just any `BEGIN`/`END` pair appearing in the same projected surface.
- Align mailbox parsing and mailbox completion gating around the same active-request contract so provisional completion does not hand off known-invalid surfaces to the exact parser.
- Add regression coverage for the live prompt-echo case where the shadow surface repeats the request contract before any real mailbox result is emitted.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `brain-launch-runtime`: `shadow_only` mailbox completion gating SHALL ignore prompt-echo sentinel mentions and continue polling until exactly one valid mailbox result payload for the active request is visible or an existing bounded failure policy fires.

## Impact

- Affected code: `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/mail_commands.py`, and any mailbox result extraction helpers shared by the shadow completion observer.
- Affected tests: mailbox runtime contract tests, mailbox parsing unit tests, and live/demo regression coverage for the sender `mail send` path.
- Affected behavior: `shadow_only` runtime mailbox commands using sentinel-delimited JSON results, especially Claude/Codex flows that echo the mailbox request contract before producing the final mailbox result block.
