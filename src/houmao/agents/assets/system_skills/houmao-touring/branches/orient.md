# Orient On Current Houmao State

Use this branch first when the user explicitly wants the `houmao-touring` experience.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Start with maintained status and list surfaces instead of assuming the user is at the beginning of setup:
   - `houmao-mgr project status`
   - `houmao-mgr project easy specialist list` or `houmao-mgr project easy specialist get --name <name>` when the user already named a specialist or the next branch depends on one
   - `houmao-mgr project easy profile list` or `houmao-mgr project easy profile get --name <name>` when the user already named a reusable profile or the next branch depends on one
   - `houmao-mgr agents list`
3. If the user already mentioned a reusable specialist, easy profile, or live managed agent, preserve that context.
4. When the next branch depends on live capabilities, inspect them only as needed:
   - `houmao-mgr agents state --agent-name <name>`
   - `houmao-mgr agents gateway status --agent-name <name>`
   - `houmao-mgr agents mail resolve-live --agent-name <name>`
5. Explain the current posture in plain language.
6. Offer the next likely branches based on that posture, for example:
   - initialize or inspect the project overlay
   - set up the optional project mailbox
   - create another specialist
   - create an optional profile
   - launch another agent
   - prompt or watch a running agent
   - send mailbox work
   - create reminders
   - explore advanced pairwise agent-loop creation
   - stop, relaunch, or clean up a managed agent

## Guardrails

- Do not treat missing project state as a reason to hide the later branches; explain that those branches become more useful after setup.
- Do not assume the tour is complete after one launch or one prompt.
- Do not inspect deeper live state than the selected next branch actually needs.
- Do not replace the maintained `project easy ...` inspection commands with guessed top-level aliases or direct `.houmao/easy/` filesystem probing.
