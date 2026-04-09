# Project And Mailbox Setup Branch

Use this branch when the user wants project overlay setup, project explanation, or optional project-local mailbox setup.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Route project overlay lifecycle and project explanation to `houmao-project-mgr`.
3. Treat project-local mailbox setup as optional, not mandatory:
   - explain what project-local mailbox work enables
   - offer a skip-for-now path when the user does not need mailbox work yet
4. Route mailbox administration to `houmao-mailbox-mgr`.
5. After the setup branch, summarize what now exists and offer the next likely branches:
   - create a specialist
   - create an optional profile
   - launch an agent
   - return later for mailbox setup if skipped

## Typical Questions

- “Do you want to initialize the project overlay here?”
- “Do you want to set up a project-local mailbox now or skip it for now?”
- “What mailbox address and principal id should this project mailbox use?”

## Guardrails

- Do not present project mailbox setup as mandatory for every Houmao project.
- Do not hand-edit `.houmao/` or mailbox directories when the maintained project or mailbox skills already own those steps.
- Do not bury the fact that mailbox setup can be revisited later.
