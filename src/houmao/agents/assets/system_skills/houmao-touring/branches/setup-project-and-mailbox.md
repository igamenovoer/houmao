# Project And Mailbox Setup Branch

Use this beginner branch when the user wants project overlay setup, project explanation, or project-local mailbox subsystem basics.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Route project overlay lifecycle and project explanation to `houmao-project-mgr`.
3. Teach mailbox subsystem basics without turning this into a mailbox reference page:
   - explain what project-local mailbox work enables
   - distinguish mailbox-root bootstrap from mailbox-account creation before asking for mailbox identity values
   - explain that the common first mailbox step is initializing the shared mailbox root, not necessarily preregistering one mailbox account per future agent
   - when the user plans to launch specialist-backed easy instances with ordinary addresses such as `<agent-name>@houmao.localhost`, explain that launch-time mailbox bootstrap can own those per-agent addresses later
   - when the user instead wants one shared or manually named mailbox account, recommend address `research@houmao.localhost` plus principal id `HOUMAO-research`
   - explain that mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals
   - offer a skip-for-now path when the user does not need mailbox work yet
4. Route mailbox administration to `houmao-mailbox-mgr`.
5. After the setup branch, summarize what now exists and offer beginner next actions:
   - choose a tool and prepare credentials
   - create a specialist
   - create an optional project profile
   - launch an agent
   - send the first prompt after launch
   - return later for mailbox account setup if skipped

## Typical Questions

- “Do you want to initialize the project overlay here?”
- “Do you want to initialize the project mailbox root now or skip mailbox setup for the moment?”
- “Are you preparing shared mailbox accounts now, or do you want future easy-instance launches to own the per-agent mailbox addresses?”
- “If you want a shared mailbox account now, what mailbox address and principal id should it use?”

## Guardrails

- Do not present project mailbox setup as mandatory for every Houmao project.
- Do not collapse mailbox-root bootstrap, manual mailbox-account registration, and launch-owned per-agent mailbox binding into one vague setup step.
- Do not hand-edit `.houmao/` or mailbox directories when the maintained project or mailbox skills already own those steps.
- Do not bury the fact that mailbox setup can be revisited later.
- Do not present inter-agent mail, notifier rounds, or prompt injection through mail as beginner prerequisites; those belong to the intermediate stage after an agent exists.
