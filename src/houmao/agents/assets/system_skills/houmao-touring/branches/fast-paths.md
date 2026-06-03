# Fast Path Use Cases

Use this branch when the user wants an outcome now and explicitly invoked `houmao-touring`. Fast paths are use cases, not command aliases. They keep explanation short, inspect enough state for safety, and route concrete work to the maintained owning skills.

Precondition: a Houmao project overlay must exist before presenting fast path use cases as available choices. If no project overlay exists, do not continue into this branch's use-case menu. Offer only `Create Houmao Project`, `Subsystem Exploration`, and `Inspect`; after project setup, return to fast path selection.

## Selection

| Use Case | Select When | Primary Owner Routes |
| --- | --- | --- |
| Single Agent Full Run | The user wants one complete agent experience. | `houmao-project-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-memory-mgr`, `houmao-agent-inspect`, `houmao-agent-instance`. |
| Operator-Controlled Agent Team | The user wants multiple agents but wants to stay in manual control. | Same single-agent owners, repeated per agent, plus manual prompt/mail coordination through `houmao-agent-messaging` and `houmao-agent-email-comms`. |
| Pro Agent Loop | The user wants a generated loop, topology, execplan, participant roles, or loop operation. | `houmao-agent-loop-pro`; use `houmao-utils-workspace-mgr` when isolated workspace preparation is needed. |

Do not split these into separate micro fast paths for talk, mail, inspect, notify, or stop. Those are operations inside a use case and belong to their owning skills.

## Single Agent Full Run

Goal: create and operate one fully functional managed agent across the useful Houmao surfaces, not merely launch a process.

| Phase | First Choice | Secondary Routes |
| --- | --- | --- |
| Create Agent | Route first to `houmao-agent-definition create-agent-fast-forward` so the owning skill creates or selects the specialist, creates or updates the project profile, prepares mailbox-backed launch defaults, and prints the launch command. | Use `houmao-project-mgr`, `houmao-credential-mgr`, `houmao-agent-definition specialists`, or `houmao-agent-definition profiles` only when fast-forward reports missing input, missing project state, credential blockers, or the user asks for manual control. |
| Launch | Launch from the fast-forward profile command and start one visible managed agent with foreground-first gateway posture unless the user asked otherwise. | Route gateway posture changes to `houmao-agent-gateway` only when needed. |
| Operate | Send first prompt, inspect live state, use memo/pages, use mailbox, enable or inspect mail-notifier, create reminders. | Route to `houmao-agent-messaging`, `houmao-agent-inspect`, `houmao-memory-mgr`, `houmao-agent-email-comms`, and `houmao-agent-gateway`. |
| Follow Up | Stop, relaunch, or clean up only when the user chooses lifecycle work. | Route to `houmao-agent-instance`. |

For Single Agent Full Run, do not start by separately walking the user through credential setup, specialist creation, and profile creation. Try `create-agent-fast-forward` first, then repair only the blockers it reports.

After each phase, summarize the result and offer two to four nearby next choices. Do not dump command syntax; if the user asks for `more detail`, route command examples to the owning skill or show only the narrow command needed for the current decision.

Typical next-choice shape:

| Choice | Intent | Route |
| --- | --- | --- |
| Prompt | Talk to the running agent. | `houmao-agent-messaging`. |
| Inspect | See state, screen, logs, or mailbox posture. | `houmao-agent-inspect`. |
| Notify | Let gateway mail-notifier wake the agent for open mail. | `houmao-agent-gateway`. |
| Remember | Add or read memo/pages context. | `houmao-memory-mgr`. |

## Operator-Controlled Agent Team

Goal: create multiple fully functional managed agents and control them manually as the operator. Keep the operator in control unless the user asks for generated loop construction.

| Phase | Intent | Route |
| --- | --- | --- |
| Team Foundation | Confirm each agent has definition, credential, launch posture, gateway, and mailbox readiness. | `houmao-agent-definition`, `houmao-credential-mgr`, `houmao-agent-gateway`, `houmao-mailbox-mgr`. |
| Launch Team | Launch each managed agent, preferably with visible tour posture for first-time operation. | `houmao-agent-definition`. |
| Manual Control | Send direct prompts, operator-origin mail, and inter-agent mail; inspect responses. | `houmao-agent-messaging`, `houmao-agent-email-comms`, `houmao-agent-inspect`. |
| Team Posture | Enable notifier where gateway and mailbox are ready, add reminders, update memo/pages, handle lifecycle follow-up. | `houmao-agent-gateway`, `houmao-memory-mgr`, `houmao-agent-instance`. |

When more than one coordination style is reasonable, ask by intent:

| Choice | Best When | Route |
| --- | --- | --- |
| Direct prompts | The operator wants immediate steering. | `houmao-agent-messaging`. |
| Operator-origin mail | Work should enter the mailbox as operator-authored mail. | `houmao-agent-email-comms`. |
| Inter-agent mail | One managed agent should receive work from another mailbox identity. | `houmao-agent-email-comms`. |
| Pro loop | The user wants generated topology or repeated loop operation. | `houmao-agent-loop-pro`. |

## Pro Agent Loop

Goal: define and construct a generated loop through `houmao-agent-loop-pro`. Use this when the request is schema-rich, topology-heavy, generated-execplan oriented, or explicitly asks for an agent loop.

| Phase | Intent | Route |
| --- | --- | --- |
| Clarify | Capture loop intent, participant roles, expected handoffs, and whether topology is `tree-loop` or `generic-loop`. | `houmao-agent-loop-pro`. |
| Prepare | Establish mailbox and runtime contracts; prepare isolated workspace only when the loop needs one. | `houmao-agent-loop-pro`, `houmao-utils-workspace-mgr`. |
| Generate | Create and validate generated execplan artifacts. | `houmao-agent-loop-pro`. |
| Operate | Launch participants and run or inspect the generated loop. | `houmao-agent-loop-pro`. |

Topology prompt shape:

| Topology | Use When | Owner |
| --- | --- | --- |
| `tree-loop` | Work flows through a local-close tree and results return to immediate upstream owners. | `houmao-agent-loop-pro`. |
| `generic-loop` | The graph may contain cycles, relay lanes, or task-specific predecessor-context forwarding. | `houmao-agent-loop-pro`. |

Do not duplicate pro-loop schemas, generated artifact layouts, run-control rules, topology contracts, or validation rules here. Route to `houmao-agent-loop-pro` and let that skill own the details.

## Completion Style

Close each fast-path step with a compact result and next choices.

| Area | Say |
| --- | --- |
| Result | What changed or what was learned. |
| Status | The state facts that matter for the next decision. |
| Next | Two to four nearby choices by intent. |
| Need | Required input if the next action cannot proceed. |

Use `more detail` for command examples, raw evidence, longer concept explanation, passive server context, or deeper runtime internals.
