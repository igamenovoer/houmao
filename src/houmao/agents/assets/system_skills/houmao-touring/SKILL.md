---
name: houmao-touring
description: Use Houmao's manual guided touring skill for users not yet familiar with Houmao.
license: MIT
---

# Houmao Touring

`houmao-touring` is the Houmao-owned guide for users who are not yet familiar with Houmao. That includes first-run users, re-orienting operators, and developers inspecting system logic.

Use this skill only when the user explicitly asks for:

| Trigger | Meaning |
| --- | --- |
| `$houmao-touring` | No-prompt orientation entrypoint. |
| A Houmao guided tour | Start the guided tour. |
| Houmao subsystem/component exploration | Explain Houmao by component area. |

A bare invocation such as `$houmao-touring` means "start orientation now".

No-prompt behavior:

| Do | Do Not |
| --- | --- |
| scan for existing Houmao project state. | Say only "the skill is now active." |
| infer the user's likely starting intent from that state. | Ask "how can I help?" |
| introduce Houmao in context. | Use any other empty open-ended greeting. |
| provide next-step instructions. | Wait for the user to know Houmao vocabulary. |

Never answer a bare invocation with only a generic activation acknowledgement.

This skill teaches and routes. It does not own direct-operation command behavior.

## Help

When the user asks `$houmao-touring help`, `help for houmao-touring`, `usage for houmao-touring`, `available functionality for houmao-touring`, or what this skill can do, answer from this section and stop.

This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state.

Available functionality:

| Lane | Best For | What It Covers |
| --- | --- | --- |
| Fast path use cases | Outcome-focused users | Learn Houmao by doing one useful end-to-end use case. |
| Subsystem exploration | Developer-minded users | Inspect Houmao by component area and owning route. |

Fast path use cases:

| Use Case | Intent | Main Route |
| --- | --- | --- |
| Single Agent Full Run | Create and operate one fully functional managed agent. | Setup, definition, launch, gateway, mailbox, memory, inspection, and lifecycle work route to owning skills. |
| Operator-Controlled Agent Team | Create multiple fully functional agents and control them manually. | Multi-agent setup and live operations route to owning skills. |
| Pro Agent Loop | Define and construct a generated loop. | Generated loop construction routes through `houmao-agent-loop-pro`. |

Common starting prompts:

| Prompt | Intent |
| --- | --- |
| `$houmao-touring help` | Read-only help. |
| `$houmao-touring` | Orientation request. |
| `$houmao-touring start a guided tour` | Orientation request. |
| `$houmao-touring orient me in this project` | Orientation request. |
| `$houmao-touring help me find the right starting path` | Orientation request. |
| `$houmao-touring create and operate one complete agent` | Single Agent Full Run. |
| `$houmao-touring create a manually controlled agent team` | Operator-Controlled Agent Team. |
| `$houmao-touring define a pro agent loop` | Pro Agent Loop. |
| `$houmao-touring explore Houmao by subsystem` | Subsystem exploration. |

Related skills and boundaries:

| Boundary | Rule |
| --- | --- |
| Tour scope | Orient, teach nearby concepts, infer likely next path, and route. |
| Direct work | Route project, credential, definition, runtime, gateway, mailbox, memory, inspection, lifecycle, workspace, and loop work to owning skills. |
| Non-goal | Do not use touring as a broad skill catalog or default router for ordinary narrow requests. |

## Entry Contract

Classify the request before command execution.

| Intent | Trigger Shape | First Action |
| --- | --- | --- |
| Help intent | User asks for help, usage, or available functionality. | Answer `## Help` and stop. |
| Orientation request | User invokes `$houmao-touring` or asks to start/orient. | Inspect current state, infer likely intent, offer best path plus alternatives. |
| Outcome request | User asks for one complete agent, a manual agent team, or a generated loop. | Inspect only safety-relevant state, then load `branches/fast-paths.md`. |
| Subsystem-exploration request | User asks for subsystem, component, internal, or working-logic exploration. | Load `branches/subsystem-exploration.md`. |
| Ordinary direct-operation request | User asks to create, launch, prompt, mail, inspect, stop, or clean up without asking for touring. | Do not activate touring; route to the owning skill. |

For orientation and outcome requests, inspect current state before choosing a welcome shape or branch. For subsystem exploration, do not start the first-agent setup path by default.

## No-Prompt Entrypoint

Bare `$houmao-touring` is the system entrypoint for a user who may know nothing about Houmao.

Required sequence:

| Step | Action |
| --- | --- |
| 1 | Scan for existing Houmao project state. |
| 2 | Infer likely user intent from inspected state. |
| 3 | Introduce Houmao in the context of that state. |
| 4 | Present current posture, likely intent, next choices, and required input. |
| 5 | Wait for the user to confirm a path. |

Scan:

| Area | Inspection |
| --- | --- |
| Project | `houmao-mgr project status` |
| Definitions | `houmao-mgr project specialist list`; `houmao-mgr project profile list` when project state exists |
| Runtime | `houmao-mgr agents global list` |
| Live control | gateway, mailbox, and memory posture only when the selected next path needs them |

### Intent Guess Matrix

| Inspected State | Likely Intent | First Choice |
| --- | --- | --- |
| No project overlay | The user needs project foundation before agent workflows. | Create Houmao Project. |
| Project overlay exists, no specialists | The user is ready to define a launchable agent. | Single Agent Full Run, starting at agent definition. |
| Specialists or profiles exist, no running agents | The user is likely ready to launch and operate. | Single Agent Full Run, starting at launch readiness. |
| One running agent | The user likely wants to operate or inspect it. | Live operation choices inside Single Agent Full Run. |
| Multiple running agents | The user may want manual coordination. | Operator-Controlled Agent Team. |
| Existing loop artifacts or topology hints | The user may want generated orchestration. | Pro Agent Loop. |
| Component/internal/working-logic wording | The user wants component understanding. | Subsystem Exploration. |

The guess orders choices. It must not execute concrete setup, launch, prompt, mail, gateway, memory, lifecycle, workspace, or loop work without user confirmation.

Fast paths are project-ready choices. If no Houmao project overlay exists, do not present `Single Agent Full Run`, `Operator-Controlled Agent Team`, or `Pro Agent Loop` as selectable no-prompt choices. Say those choices become available after project creation.

### No-Prompt Response Shape

Use a compact response with these parts:

| Part | Content |
| --- | --- |
| Intro | One sentence: Houmao creates, runs, inspects, and coordinates CLI-based AI agents with managed runtime, gateway, mailbox, memory, and loop support. |
| Current Posture | Compact project/definition/runtime/live-control status. |
| Likely Intent | The inferred path and why it fits. |
| Next Choices | Use the state-specific menu below. Without a project overlay, show exactly the three blank-workspace choices. With a project overlay, include the guessed path and `Subsystem Exploration` by name. |
| Required Input | Ask the user to pick a path, say `inspect first`, or say `more detail`. |

If inspection cannot run, report current posture as unknown and offer `inspect first` as the first choice.

### No-Prompt Choice Menu

For bare `$houmao-touring`, choose the menu from project posture. Adapt wording to the inspected state, but do not hide or rename `Subsystem Exploration`.

Blank workspace, no Houmao project overlay:

| Choice | Intent | User Can Say | Route |
| --- | --- | --- | --- |
| Create Houmao Project | Initialize the foundation required by agent workflows. | `create project` | `houmao-project-mgr` |
| Subsystem Exploration | Understand Houmao by component area before creating state. | `subsystems` or a subsystem name | `branches/subsystem-exploration.md` |
| Inspect | Show current directory, project, and runtime evidence without mutation. | `inspect` | Read-only inspection |

In this state, show only these three choices. Do not show `Fast Path Use Cases`, `Single Agent Full Run`, `Operator-Controlled Agent Team`, or `Pro Agent Loop` until a Houmao project overlay exists.

Project-ready workspace, Houmao project overlay exists:

| Choice | Best For | User Can Say |
| --- | --- | --- |
| Continue Likely Path | Follow the state-based guess. | `continue` |
| Fast Path Use Cases | Build useful Houmao workflows quickly. | `single agent`, `team`, or `pro loop` |
| Subsystem Exploration | Understand Houmao by component area. | `subsystems` or a subsystem name |
| Inspect First | See evidence before choosing. | `inspect first` |

Do not collapse the project-ready menu into only fast path choices. If space is tight, keep the guessed path, `Subsystem Exploration`, and `inspect first`.

### Subsystem Exploration Choices

When the no-prompt entrypoint offers `Subsystem Exploration`, include a compact preview of component choices. Load `branches/subsystem-exploration.md` only after the user selects this path or names one subsystem.

| Choice | Subsystems | Best For |
| --- | --- | --- |
| Project State | Project overlay, Agent definition | Where Houmao state lives and how agents become launchable. |
| Runtime Control | Managed runtime, Gateway | How agents run, expose live control, and report lifecycle. |
| Communication | Messaging, Mailbox | How prompts, operator mail, inter-agent mail, and notifier work connect. |
| Context and Evidence | Memory, Inspection | How durable context and read-only evidence guide decisions. |
| Multi-Agent Structure | Workspace, Loop orchestration | How isolated work areas and generated loops organize teams. |

Keep this preview short. Use `more detail` or the branch page before expanding any subsystem.

## Coverage Model

| Lane | Purpose | Branch |
| --- | --- | --- |
| Fast path use cases | Outcome-driven routes for useful end-to-end work. | `branches/fast-paths.md` |
| Subsystem exploration | Component-oriented explanation for system understanding. | `branches/subsystem-exploration.md` |

Fast paths:

Precondition: a Houmao project overlay must exist. If missing, route `Create Houmao Project` through `houmao-project-mgr`, then return to fast-path selection after project setup.

| Use Case | Coverage |
| --- | --- |
| Single Agent Full Run | Project overlay, tool/credential readiness, specialist/profile setup, foreground-first launch, gateway, mailbox, notification, prompt, inspection, memory, reminders, lifecycle follow-up. |
| Operator-Controlled Agent Team | Multiple agents, per-agent gateway/mailbox, prompts, mail, notifier, inspection, memory, reminders, lifecycle. |
| Pro Agent Loop | `houmao-agent-loop-pro`, loop intent, roles, `tree-loop`/`generic-loop`, mailbox/runtime contracts, workspace preparation when needed, validation, launch, operation. |

Stages are posture labels, not a fixed route:

| Stage | Typical Nearby Work |
| --- | --- |
| Beginner | Project overlay, mailbox basics, tool/credential readiness, specialist/profile setup, launch, first prompt. |
| Intermediate | Prompt, inspect, memo/pages, mailbox, gateway mail-notifier, reminders, manual coordination, lifecycle. |
| Advanced | Pro loop, lite loop, topology choice, isolated workspace, generated loop operation. |

## Presentation Rules

| Rule | Instruction |
| --- | --- |
| Compact by default | Report only result, critical status, next choices, and required input. |
| Tables | Prefer small Markdown tables for status and choices. Keep tables at four columns or fewer. |
| Language | Use concise language. Focus on intent and current posture. |
| Detail | Use `more detail` for command examples, raw evidence, passive server context, deeper TUI tracking behavior, or architecture detail. |
| Ownership | Route by user intent. Do not duplicate detailed behavior, command syntax, options, or validation rules owned by other Houmao skills. |

### Presentation Examples

Operation result:

| Area | Example Content |
| --- | --- |
| Result | What changed or what was learned. |
| Status | The one or two state facts that matter now. |
| Next | Nearby choices, routed by intent. |
| Need | Input needed to continue, if any. |

Blank-workspace branch choices:

| Choice | Intent | Route |
| --- | --- | --- |
| Create Houmao Project | Create the project foundation needed by later agent workflows. | `houmao-project-mgr` |
| Subsystem Exploration | Inspect Houmao by component area. | Load `branches/subsystem-exploration.md`. |
| Inspect | Show current evidence without mutation. | Read-only inspection. |

Project-ready branch choices:

| Choice | Intent | Route |
| --- | --- | --- |
| Single Agent Full Run | Build and operate one complete agent. | Tour guides; concrete setup, launch, gateway, mail, memory, inspection, and lifecycle work route to owning skills. |
| Operator-Controlled Agent Team | Build and manually control multiple complete agents. | Tour guides; per-agent setup and live operations route to owning skills. |
| Pro Agent Loop | Generate a loop from roles and topology. | Route generated loop construction to `houmao-agent-loop-pro`. |
| Subsystem Exploration | Inspect Houmao by component area. | Load `branches/subsystem-exploration.md`. |

## Welcome and Orientation

| State | Welcome Shape |
| --- | --- |
| Blank slate | Short Houmao intro, current posture, likely Create Houmao Project path, Subsystem Exploration, and Inspect. |
| Existing state | One short acknowledgement, current posture, state-aware next choices. |
| Recent welcome already given | Skip welcome; continue from current posture. |

Full blank-slate intro:

```text
Welcome to Houmao. Houmao creates, runs, inspects, and coordinates CLI-based AI agents with managed runtime, gateway, mailbox, memory, and loop support.
```

## Workflow

Before workflow, answer explicit skill-help intent from `## Help` and stop.

| Step | Action |
| --- | --- |
| 1 | Confirm the user asked for the guided touring experience. |
| 2 | Choose one `houmao-mgr` launcher. |
| 3 | Inspect current state for orientation/outcome requests. |
| 4 | Infer likely path from state and request intent. |
| 5 | Present compact posture, likely intent, choices, and required input. |
| 6 | Load exactly one branch page when the user selects a path. |
| 7 | Route concrete work to owning Houmao skills. |
| 8 | After each completed branch step, summarize state and offer next choices. |

Launcher order:

| Order | Launcher |
| --- | --- |
| 1 | `houmao-mgr` on `PATH` |
| 2 | `uv tool run --from houmao houmao-mgr` |
| 3 | Development launcher only if the first two do not satisfy the turn |
| User override | Follow an explicitly requested launcher |

## Branches

| Branch | Use |
| --- | --- |
| `branches/orient.md` | Current posture and stage-aware action table. |
| `branches/fast-paths.md` | Single Agent Full Run, Operator-Controlled Agent Team, Pro Agent Loop. |
| `branches/subsystem-exploration.md` | Component-minded subsystem exploration. |
| `branches/quickstart.md` | Old quickstart wording; prefer Single Agent Full Run for complete fast path. |
| `branches/setup-project-and-mailbox.md` | Project overlay or mailbox basics. |
| `branches/author-and-launch.md` | Specialist/profile authoring or launching another agent. |
| `branches/live-operations.md` | Prompt, memo, mailbox, notifier, gateway, reminder, inspection, manual coordination. |
| `branches/advanced-usage.md` | Loop-lite, loop-pro tree/generic mode, isolated workspace guidance. |
| `branches/lifecycle-follow-up.md` | Inspect, stop, relaunch, join/adopt, cleanup follow-up. |

## References

| Reference | Use |
| --- | --- |
| `references/question-style.md` | User-input questions with required/optional fields and examples. |
| `references/concepts.md` | Short vocabulary: specialist, profile, managed agent, gateway, mailbox, notifier round, memory, loop, workspace, relaunch, cleanup. |

## Routing Guidance

| Intent | Owning Skill |
| --- | --- |
| Project overlay setup/explanation | `houmao-project-mgr` |
| Mailbox root/account/admin | `houmao-mailbox-mgr` |
| Credential readiness/content | `houmao-credential-mgr` |
| Specialist/profile/launch dossier/easy launch | `houmao-agent-definition` |
| Runtime inspection/evidence | `houmao-agent-inspect` |
| Prompt/interrupt/raw input/mailbox-routing entry | `houmao-agent-messaging` |
| Gateway lifecycle/watch/mail-notifier/reminders | `houmao-agent-gateway` |
| Mail send/read/reply/post/archive | `houmao-agent-email-comms` |
| One gateway-notified open-mail round | `houmao-process-emails-via-gateway` |
| Memo/pages/memo seed | `houmao-memory-mgr` |
| Lite loop authoring/execution | `houmao-agent-loop-lite` |
| Pro loop authoring/topology/execution | `houmao-agent-loop-pro` |
| Isolated workspace planning/creation/validation | `houmao-utils-workspace-mgr` |
| Elemental coordination pattern | `houmao-adv-usage-pattern` |
| Stop/relaunch/join/adopt/list/cleanup | `houmao-agent-instance` |

Present `tree-loop` and `generic-loop` as topology choices inside `houmao-agent-loop-pro`, not as separate skill packages.

## Guardrails

| Guardrail | Rule |
| --- | --- |
| Activation | Do not activate unless the user explicitly asked for touring. |
| Catalog | Do not turn the tour into a full packaged-skill catalog. |
| State | Never restart from project initialization when current state exists. |
| Order | Inspect current state before welcome selection for orientation and outcome requests. |
| Ownership | Do not claim direct-operation command shapes. |
| Commands | Do not invent top-level `houmao-mgr easy ...` or `houmao-mgr specialists ...`; reusable definitions live under `houmao-mgr project ...`. |
| Lifecycle | Keep stop, relaunch, and cleanup separate; never auto-run cleanup after stop. |
| Loops/workspaces | Keep loop topology, run-control, direct-SQL, workspace, and elemental protocol details on owning skills. |
| Packaging | Keep packaged touring content self-contained; do not reference development-repository-only paths. |
