## 1. Shared mailbox result selection

- [x] 1.1 Add shared mailbox-result extraction helpers that identify real standalone sentinel-delimited result blocks while ignoring prompt-echo sentinel mentions.
- [x] 1.2 Update mailbox result parsing to use the shared selector for active-request validation instead of relying on whole-surface sentinel substring counts.

## 2. Shadow completion integration

- [x] 2.1 Update the `shadow_only` mailbox completion observer in `cao_rest.py` to use the shared mailbox-result selector for provisional completion gating.
- [x] 2.2 Preserve explicit malformed-result failures for real standalone sentinel blocks while keeping prompt-echo-only surfaces in provisional polling.

## 3. Regression coverage

- [x] 3.1 Add unit tests in `tests/unit/agents/realm_controller/test_mail_commands.py` for prompt-echo sentinel mentions that must not count as mailbox-result evidence.
- [x] 3.2 Add runtime/integration regression coverage for a `shadow_only` mailbox turn that echoes the request contract before emitting the real mailbox result block.
- [x] 3.3 Run the targeted mailbox parser/runtime test slices and confirm the prompt-echo regression is covered without changing non-mail shadow completion behavior.
