## Why

The current managed `task-reminder` prompt section encourages agents to create a live gateway reminder for generic "potentially long-running work" and hardcodes a short default delay. Even though the section is default-disabled, enabling it currently nudges agents toward low-value ceremonial self-reminders that consume extra turns without doing meaningful supervision or finalization work.

## What Changes

- Narrow the managed `task-reminder` section so it only authorizes reminders for explicit self-reminding requests or concrete supervision/finalization goals.
- Remove the generic "create a reminder when work may run long" instruction and the fixed 10-second default delay from the managed prompt-header contract.
- Require the prompt text to bias agents toward local todo or working state when no concrete reminder target exists.
- Update the managed prompt-header reference docs so they describe the narrower reminder posture and explicitly distinguish useful supervision reminders from ceremonial self-pings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `managed-launch-prompt-header`: change the `task-reminder` section requirements so reminder creation is limited to explicit user-directed self-reminding or concrete supervision/finalization checks, and remove the fixed short default delay.
- `docs-managed-launch-prompt-header-reference`: update the reference-page requirements so documentation matches the narrower `task-reminder` behavior and warns against generic ceremonial self-reminders.

## Impact

- Affected code: `src/houmao/agents/managed_prompt_header.py`
- Affected docs: `docs/reference/run-phase/managed-prompt-header.md`
- Verification: prompt-header rendering tests or spec-aligned assertions for the `task-reminder` section text, plus documentation updates that mirror the new contract
