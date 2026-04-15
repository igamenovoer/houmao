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
5. Classify the inspected workspace posture using the posture-to-branch routing table below. That table is the source of truth for deciding which next branches to offer.
6. Explain the current posture in plain language and offer the next branches named for that posture in the table. The offered branches are offers, not mandates; the user can always choose a different supported branch.

## Posture-To-Branch Routing Table

Use this table to map inspected workspace posture to the set of next-likely branches. Each row lists offers. Do not force the user into exactly one row entry when more than one is reasonable for the inspected posture.

| Inspected posture                                                              | Offered next branches                                                                             |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| no project overlay, no reusable specialists, no running managed agents         | `quickstart`, `setup-project-and-mailbox`                                                         |
| project overlay exists, no reusable specialists                                | `author-and-launch`, `setup-project-and-mailbox` (for optional mailbox), `quickstart` when desired |
| reusable specialists exist, no running managed agents                          | `author-and-launch` (launch), `setup-project-and-mailbox` (for optional mailbox follow-up)        |
| one or more running managed agents, single-agent workspace                     | `live-operations`, `lifecycle-follow-up`, `author-and-launch` to launch another agent             |
| more than one running managed agent (multi-agent workspace)                    | `live-operations`, `advanced-usage`, `lifecycle-follow-up`, `author-and-launch` for additional agents |
| running managed agents with live gateway attached and mailbox accounts ready   | `live-operations` (with explicit mail-notifier follow-up), `advanced-usage`, `lifecycle-follow-up` |

## Offer Guidance

- When the table offers more than one branch for the current posture, present all offered branches. Do not silently prefer one over the others.
- When the quickstart branch is offered, describe it as a minimum-viable-launch path that detects available host tool CLIs; describe the explicit setup branch as the path that initializes the project overlay and optionally the project-local mailbox.
- When the advanced-usage branch is offered, describe it as a flat enumeration of the broader advanced Houmao feature surface; do not preview the full list in the orient branch itself.
- When the user explicitly asks for a branch that is not the offered default for the inspected posture, route to that branch anyway. The routing table informs offers, not restrictions.

## Guardrails

- Do not treat missing project state as a reason to hide the later branches; explain that those branches become more useful after setup.
- Do not assume the tour is complete after one launch or one prompt.
- Do not inspect deeper live state than the selected next branch actually needs.
- Do not replace the maintained `project easy ...` inspection commands with guessed top-level aliases or direct `.houmao/easy/` filesystem probing.
- Do not re-derive the offered branches in free prose when the posture-to-branch routing table already covers the inspected posture.
- Do not treat the routing table as a mandate; the offered branches remain offers, and the user may choose any supported branch from the top-level `SKILL.md` branches list.
