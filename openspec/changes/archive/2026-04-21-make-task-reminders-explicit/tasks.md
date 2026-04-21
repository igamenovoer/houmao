## 1. Prompt Contract Update

- [x] 1.1 Update `src/houmao/agents/managed_prompt_header.py` so the `task-reminder` section only authorizes explicit self-reminding requests or concrete supervision/finalization reminders.
- [x] 1.2 Remove the generic long-running-work trigger and fixed 10-second default delay from the rendered `task-reminder` text.
- [x] 1.3 Ensure the rendered `task-reminder` text tells agents to keep using local todo or working state when no concrete reminder target exists.

## 2. Documentation Alignment

- [x] 2.1 Update `docs/reference/run-phase/managed-prompt-header.md` so the `task-reminder` section description matches the narrowed contract.
- [x] 2.2 Make the reference docs explicitly distinguish useful supervision/finalization reminders from ceremonial self-pings.

## 3. Verification

- [x] 3.1 Add or update prompt-focused verification for the managed prompt header so `task-reminder` output no longer mentions generic long-running work or a fixed default delay.
- [x] 3.2 Run the relevant test or verification commands and confirm the changed prompt-header text and docs stay aligned with the new spec.
