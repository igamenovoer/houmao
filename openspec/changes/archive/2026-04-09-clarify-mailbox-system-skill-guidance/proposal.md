## Why

Houmao's mailbox-related system skills currently describe their own command surfaces in isolation but do not explain the interaction boundaries between touring, mailbox administration, and specialist-backed easy launch. That gap leads agents to compose technically valid commands into an invalid workflow, especially around project mailbox setup, launch-time mailbox ownership, and the meaning of `--mail-account-dir`.

## What Changes

- Clarify the guided touring mailbox branch so "project-local mailbox setup" distinguishes mailbox-root bootstrap from per-agent account registration and from easy-instance launch-time mailbox binding.
- Clarify the mailbox-manager skill so `project mailbox register` is framed as manual mailbox-account administration, not the default setup step for specialist-backed easy instances that will auto-register their own filesystem mailbox on launch.
- Clarify the specialist-manager launch guidance so it explicitly distinguishes profile-only declarative mailbox fields from launch-time mailbox flags, explains default mailbox identity derivation from the managed-agent instance name, and documents that `--mail-account-dir` is a private symlink-backed mailbox directory that must live outside the shared root.
- Add explicit cross-skill interaction guidance for the common collision cases:
  - manual `project mailbox register` before `project easy instance launch --mail-transport filesystem --mail-root ...` for the same address,
  - using `--mail-address` or `--mail-principal-id` on `project easy instance launch`,
  - pointing `--mail-account-dir` at a directory inside the shared mailbox root.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-touring-skill`: refine the guided mailbox-setup branch so it explains which mailbox setup steps are optional root bootstrap versus manual account registration versus launch-owned mailbox binding.
- `houmao-mailbox-mgr-skill`: define when manual mailbox registration is appropriate and when operators should instead use existing-agent late binding or launch-time filesystem mailbox bootstrap.
- `houmao-create-specialist-skill`: strengthen specialist-backed launch guidance for mailbox-enabled easy launch, including absent launch flags, default mailbox identity, and `--mail-account-dir` semantics.

## Impact

- System skill assets under `src/houmao/agents/assets/system_skills/`, especially the touring, mailbox-manager, and specialist-manager action pages and references.
- Mailbox-related operator behavior during guided setup and specialist-backed easy launch.
- Supporting tests or validation that assert the revised skill wording and routing boundaries.
