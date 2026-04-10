## 1. Clarify touring and mailbox-admin lane ownership

- [x] 1.1 Update `houmao-touring` mailbox-setup branch and question-style guidance so project mailbox root bootstrap is distinguished from manual mailbox-account registration and from launch-owned per-agent mailbox binding.
- [x] 1.2 Update `houmao-mailbox-mgr` top-level routing and `actions/register.md` guidance so manual mailbox registration is explicitly separated from existing-agent late binding and specialist-backed easy launch mailbox bootstrap.

## 2. Clarify specialist-backed launch mailbox guidance

- [x] 2.1 Update `houmao-specialist-mgr/actions/launch.md` to distinguish profile-create declarative mailbox fields from launch-time filesystem mailbox flags and to explain default mailbox identity derivation from the managed-agent instance name.
- [x] 2.2 Add concise collision guidance for `--mail-account-dir` placement and preregistered same-address mailbox conflicts in the relevant specialist-manager action or reference pages.

## 3. Validate packaged skill behavior

- [x] 3.1 Update `tests/unit/agents/test_system_skills.py` assertions to cover the new touring, mailbox-manager, and specialist-manager mailbox guidance.
- [x] 3.2 Run focused validation for the packaged system-skill content and confirm the revised wording no longer teaches preregister-before-launch or in-root `--mail-account-dir` misuse as the common filesystem mailbox flow.
