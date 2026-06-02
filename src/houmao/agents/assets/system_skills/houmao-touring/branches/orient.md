# Orient On Current Houmao State

Use this branch first when the user explicitly wants the `houmao-touring` experience.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Start with maintained status and list surfaces instead of assuming the user is at the beginning of setup:
   - `houmao-mgr project status`
   - `houmao-mgr project specialist list` or `houmao-mgr project specialist get --name <name>` when the user already named a specialist or the next action depends on one
   - `houmao-mgr project profile list` or `houmao-mgr project profile get --name <name>` when the user already named a reusable profile or the next action depends on one
   - `houmao-mgr agents list`
3. If the user already mentioned a reusable specialist, project profile, live managed agent, mailbox account, memo, loop, or workspace goal, preserve that context.
4. When the next action depends on live capabilities, inspect them only as needed:
   - `houmao-mgr agents state --agent-name <name>`
   - `houmao-mgr agents gateway status --agent-name <name>`
   - `houmao-mgr agents mail resolve-live --agent-name <name>`
   - `houmao-mgr agents memory status --agent-name <name>` when memo or pages context is relevant
5. Classify the inspected workspace posture using the posture-to-action routing table below. That table is the source of truth for deciding which stage-aware next actions to offer.
6. Explain the current posture in plain language and offer the actions named for that posture. The offered actions are offers, not mandates; the user can always choose a different supported branch.

## Posture-To-Action Routing Table

Use this table to map inspected workspace posture to the set of stage-aware next touring actions. Do not force the user into exactly one row entry when more than one is reasonable for the inspected posture.

| Inspected posture | Stage | Offered next actions |
| --- | --- | --- |
| no project overlay, no reusable specialists, no running managed agents | beginner | `quickstart` to create one usable agent; `setup-project-and-mailbox` for explicit project and mailbox basics |
| project overlay exists, no reusable specialists | beginner | `author-and-launch` to create the first specialist; `setup-project-and-mailbox` for mailbox basics; `quickstart` when the user wants minimum decisions |
| reusable specialists exist, no running managed agents | beginner | `author-and-launch` to create an optional project profile or launch; `setup-project-and-mailbox` for mailbox follow-up |
| one running managed agent | intermediate | `live-operations` to talk, inspect, use memo, send mail, enable notifier, process a notifier round, or create reminders; `author-and-launch` to launch a second agent; `lifecycle-follow-up` for stop/relaunch/cleanup |
| running managed agent with live gateway and mailbox accounts ready | intermediate | `live-operations` with explicit mailbox, mail-notifier, notifier-round, reminder, memo, and inspection actions; `author-and-launch` to launch another agent |
| stopped or relaunchable managed agents | intermediate | `lifecycle-follow-up` to inspect, relaunch, or clean up stopped-session artifacts; `author-and-launch` to launch replacement agents |
| more than one running managed agent or explicit team-coordination intent | intermediate or advanced | `live-operations` for manual prompt/mailbox coordination; `advanced-usage` for loop-lite, loop-pro, or isolated workspace management; `lifecycle-follow-up` for session maintenance |
| explicit loop, topology, generated execplan, or isolated workspace intent | advanced | `advanced-usage` for loop-lite, loop-pro tree/generic mode, or `houmao-utils-workspace-mgr` routing |

## Offer Guidance

- Present beginner, intermediate, or advanced as learning stages, not as install sets or complete function categories.
- When the table offers more than one action for the current posture, present all relevant actions. Do not silently prefer one over the others.
- When the quickstart branch is offered, describe it as a beginner minimum-viable-launch path that detects available host tool CLIs; describe the explicit setup branch as the path that initializes the project overlay and explains mailbox basics.
- When a running agent exists, prefer intermediate actions before advanced actions unless the user already asked for loops, generated coordination, or isolated workspaces.
- When the advanced-usage branch is offered, describe it as advanced orchestration: loop-lite, loop-pro tree/generic modes, and isolated workspace management. Do not preview or enumerate the full packaged skill catalog in the orient branch.
- When the user explicitly asks for a branch that is not the offered default for the inspected posture, route to that branch anyway. The routing table informs offers, not restrictions.

## Guardrails

- Do not treat missing project state as a reason to hide later stages; explain that intermediate and advanced actions become useful after setup.
- Do not assume the tour is complete after one launch or one prompt.
- Do not inspect deeper live state than the selected next action actually needs.
- Do not replace the maintained `project ...` inspection commands with guessed top-level aliases or direct `.houmao/easy/` filesystem probing.
- Do not re-derive the offered actions in free prose when the posture-to-action routing table already covers the inspected posture.
- Do not treat the routing table as a mandate; the offered actions remain offers, and the user may choose any supported branch from the top-level `SKILL.md` branches list.
