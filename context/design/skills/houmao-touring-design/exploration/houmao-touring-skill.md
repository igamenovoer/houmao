# Houmao Touring Skill Exploration

## Purpose

`houmao-touring` should be a state-aware guide for users who are not yet familiar with Houmao. That includes first-run users, re-orienting operators, and developers who want to inspect the system's working logic. It should not behave like a full feature catalog or a direct-operation command owner.

The core behavior is: inspect current Houmao state, explain the user's current posture in plain language, offer nearby next actions, and route selected work to the maintained Houmao skill that owns the concrete operation.

## Working Vocabulary

- **Touring skill**: the high-level guide and router. It teaches and routes, but it does not own concrete command semantics.
- **Direct-operation skill**: the owning skill for a concrete Houmao action, such as project setup, mailbox administration, agent launch, messaging, gateway work, memory, inspection, lifecycle, workspace preparation, or loop operation.
- **Stage**: one learning level in the guided tour: beginner, intermediate, or advanced.
- **Branch**: one guided path inside the tour, such as quickstart, project and mailbox setup, author and launch, live operations, advanced usage, or lifecycle follow-up.
- **Fast path**: a shortcut for users who want an outcome now with minimal explanation.
- **Progressive discovery**: reveal Houmao concepts when the user's current state makes those concepts useful.

## Coverage

The tour should have two coverage lanes:

| Lane | Audience | Purpose |
| --- | --- | --- |
| Fast path use cases | Outcome-focused or impatient users | Teach Houmao by doing useful work end to end. |
| Subsystem exploration | Developer-minded users | Explain how Houmao works by component area. |

Fast path coverage should be outcome-driven.

Beginner covers the path from a blank or minimally configured workspace to one useful managed agent:

```text
blank workspace
  -> project overlay
  -> tool and credential readiness
  -> specialist
  -> optional project profile
  -> launch one managed agent
  -> send first prompt
```

Intermediate covers work that becomes useful once at least one managed agent exists:

```text
running agent
  -> prompt it
  -> inspect it
  -> use memo or pages
  -> send or read mailbox work
  -> use gateway notifier or reminders
  -> coordinate two agents manually
  -> stop, relaunch, or clean up when needed
```

Advanced covers orchestration when the user has repeated coordination, team coordination, generated loop, topology, or isolated workspace intent:

```text
repeated or team coordination
  -> isolated workspaces
  -> lite loop
  -> pro loop
  -> tree-loop or generic-loop inside pro
  -> generated loop operation
```

The tour should avoid presenting every packaged Houmao skill as a normal learning step. If the user asks for ordinary project setup, mailbox administration, credentials, launch, messaging, gateway, memory, inspection, lifecycle, loop, or workspace work, the tour should route to the owning direct-operation skill.

## Subsystem Exploration

`houmao-touring` should also include a component-oriented section for users who want to understand Houmao as a system rather than immediately execute a fast path.

This section should be explicitly framed as subsystem exploration, not as the default outcome path and not as a full packaged skill catalog. It should help a developer-minded user see what the system is made of, what each component owns, what state it reads or writes, and where to go next.

Accepted subsystem map:

| Subsystem | What User Learns | Typical Drilldown |
| --- | --- | --- |
| Project overlay | How `.houmao/` anchors project state, catalogs, credentials, mailbox, memory, and runtime metadata. | What exists here? What gets created? |
| Agent definition | How roles, recipes, credentials, specialists, profiles, and launch defaults become launchable agents. | What input is needed before launch? |
| Managed runtime | How a launched agent runs as a managed tmux-backed session with lifecycle state. | What is running? What can be stopped, relaunched, adopted, or cleaned? |
| Gateway | How the sidecar exposes live control: prompt, state, watch, reminders, and mail-notifier. | Is the gateway up? Foreground or background? What can it do? |
| Messaging | How operator intent becomes direct prompt, interrupt, raw input, queue, or mailbox-routed work. | Which transport should I use? |
| Mailbox | How mailbox root, accounts, operator-origin mail, inter-agent mail, and notifier rounds work. | Who owns the account? What happens when mail arrives? |
| Memory | How memo and pages provide durable per-agent context. | What should live in memo versus mail versus prompt? |
| Inspection | How state, screen posture, logs, turn evidence, mailbox posture, and runtime artifacts are observed. | What evidence can I trust? |
| Workspace | How isolated multi-agent workspaces prepare safe working directories before launch or loops. | Where do agents work? What is shared? |
| Loop orchestration | How generated pro loops define participants, topology, contracts, validation, launch, and operation. | When does manual coordination become a loop? |

Subsystem exploration should present a compact component map first, then ask which subsystem the user wants to inspect. After each subsystem explanation, it should offer nearby next steps such as trying the subsystem in a single-agent run, comparing it to another subsystem, or routing to the owning skill for concrete operation.

The first subsystem-exploration response may group related subsystems to keep choices compact:

| Pick | Subsystems | Best For |
| --- | --- | --- |
| 1 | Project overlay | Understanding where Houmao state lives. |
| 2 | Agent definition | Understanding how agents are authored. |
| 3 | Managed runtime + Gateway | Understanding live control. |
| 4 | Messaging + Mailbox | Understanding agent communication. |
| 5 | Memory + Inspection | Understanding context and evidence. |
| 6 | Workspace + Loop orchestration | Understanding multi-agent orchestration. |

Each subsystem explanation should cover these parts without forcing a rigid template:

| Part | Purpose |
| --- | --- |
| What it owns | The subsystem boundary. |
| Required input | What the user or environment must provide. |
| Generated state | What Houmao creates or changes. |
| Operations | Main things the user can do. |
| Routes | Owning skill for concrete work. |
| Next choices | Nearby subsystem or use-case path. |

The section should not dump low-level command reference by default. Use `more detail` for command examples, raw status output, advanced internals, passive server, deeper TUI tracking behavior, or deeper architecture explanation.

## Progressive Discovery Model

The tour should lead with the current state and reveal concepts only when they are nearby.

```text
                          explicit team intent
                                 |
                                 v
Blank -> Foundation -> First Agent -> Live Operation -> Coordination -> Generated Loops
  |         |             |              |                |              |
setup    specialist     prompt        memo/mail        second agent     loop-pro
mailbox  profile        inspect       gateway          workspace        loop-lite
```

The first turn should not say "here is everything Houmao can do." It should orient the user and offer stage-aware choices.

Example blank-workspace shape:

```text
I will orient from current Houmao state first.

Current State:
- project overlay: not found
- specialists: none found
- running agents: none found

You are at the beginner setup stage.

Good next tour choices:
1. Quickstart: create one usable agent with the fewest decisions.
2. Project and mailbox setup: understand the project overlay and mailbox root first.

Your Pick:
Choose quickstart if you want momentum; choose setup if you want the pieces explained.
```

## Fast Paths

The skill should explicitly support impatient-user prompts. A fast path still does the minimum orientation needed for safety, then proceeds toward the selected outcome with compressed explanations.

The three accepted fast path use cases are:

| Use Case | Intent | Route Shape |
| --- | --- | --- |
| Single Agent Full Run | Create and operate one fully functional managed agent. | Orient state, fill missing foundation, route setup/definition/launch/work operations to owning skills, then keep the user in a live-operation loop. |
| Operator-Controlled Agent Team | Create multiple fully functional agents and control them manually. | Orient state, route each concrete setup and launch operation to owning skills, then guide operator prompts, mail, notification, inspection, memory, reminders, and lifecycle choices. |
| Pro Agent Loop | Define and construct a generated loop. | Clarify loop intent and topology, then route generated loop construction through `houmao-agent-loop-pro`. |

Fast path rule: explain concepts only when they affect the decision in front of the user. The tour should focus on user intent and current posture, then route concrete work to the owning skill instead of duplicating that skill's command syntax, option catalog, or validation rules.

## Entry Response Split

The top-level skill should distinguish orientation requests from outcome requests.

For no-prompt, `start`, or `orient` requests:

```text
inspect project state -> infer likely intent from state -> introduce Houmao in context -> offer branch choices -> stop for user pick
```

For concrete outcome requests:

```text
inspect state -> explain only what matters -> route into the selected branch
```

This split should reduce variation between agents. `$houmao-touring start a guided tour` should orient and offer choices rather than automatically launching into quickstart. `$houmao-touring help me create and talk to my first agent` may orient briefly and then route to quickstart because the user already selected the beginner outcome.

For a bare `$houmao-touring` invocation, the agent should not wait with "hello, how can I help?" or merely report that the skill is active. It should scan for existing Houmao project state and make a low-risk intent guess from that state. The guess is used to order and explain next choices, not to execute concrete operations without confirmation.

No-prompt intent-guess matrix:

| Inspected State | Likely Intent Guess | First Choice to Present |
| --- | --- | --- |
| No project overlay | The user needs foundation and a first useful agent. | Single Agent Full Run. |
| Project overlay exists, no specialists | The user is ready to define a launchable agent. | Single Agent Full Run, starting at agent definition. |
| Specialists or profiles exist, no running agents | The user is likely ready to launch and operate. | Single Agent Full Run, starting at launch readiness. |
| One running agent | The user likely wants to operate or inspect it. | Live operation choices inside Single Agent Full Run. |
| Multiple running agents | The user may want manual coordination. | Operator-Controlled Agent Team. |
| Existing loop artifacts or explicit topology hints | The user may want generated orchestration. | Pro Agent Loop. |
| User wording mentions components, internals, or working logic | The user wants component understanding. | Subsystem exploration. |

No-prompt response should contain enough information for a user with no Houmao knowledge:

| Part | Purpose |
| --- | --- |
| Context introduction | One short explanation of Houmao as managed CLI-agent orchestration. |
| Current posture | A compact table of discovered project, definition, runtime, and live-control state. |
| Intent guess | The likely next path and why it fits the inspected state. |
| Next choices | Two to four alternatives, including the guessed path and subsystem exploration. |
| Required input | Ask the user to pick a path or say `more detail`. |

## Operation Style

At the end of each touring step, the skill should tell the user what can happen next. When more than one path is reasonable, it should present the next possible branches or actions so a new user can see the nearby Houmao feature surface without reading a catalog.

This is the tour's main teaching mechanism: every completed step becomes a small orientation point. The skill should avoid ending with only "done"; it should end with the current state plus useful next options.

The tour should not force one universal response template onto every step. Different branches may need different presentation shapes, but each step should keep the user-facing output compact and focus on:

- the operation result,
- the most critical current status,
- a brief list of next steps or branches,
- any required input needed to continue.

Prefer Markdown tables over vertical lists when presenting status, operation choices, or branch choices. Keep tables small and scannable, with at most four columns. Use lists only when a table would make the content harder to read.

Do not provide deep explanations by default. If the user wants more background, command detail, raw inspection output, or a fuller concept explanation, let them ask for `more detail` and then expand the relevant section.

The packaged skill or a loaded branch/subskill file should contain concise presentation template examples. These examples are not a universal template for every response. They are anchors that tell agents how terse to be, how to emphasize intent over command invocation, and how to close each step with current posture, next choices, and required input.

Example operation-result shape:

| Area | Say |
| --- | --- |
| Result | What just changed or what was learned. |
| Status | The one or two state facts that matter now. |
| Next | Nearby choices, routed by intent. |
| Need | The input needed to continue, if any. |

Example branch-choice shape:

| Choice | Intent | Owning Route |
| --- | --- | --- |
| Single Agent Full Run | Build and operate one complete agent. | Tour guides; setup, launch, gateway, mail, memory, and inspection route to owning skills. |
| Operator-Controlled Agent Team | Build a manual multi-agent team. | Tour guides; each concrete operation routes to its owner. |
| Pro Agent Loop | Generate a loop from roles and topology. | Route generated loop construction to `houmao-agent-loop-pro`. |

## Suggested `SKILL.md` Structure

1. Mission: guided, state-aware, outcome-oriented tour.
2. Entry Response Contract: exact first-turn behavior and response shape.
3. Fast Paths: named impatient-user routes.
4. Progressive Discovery Model: beginner, intermediate, and advanced state ladder.
5. Coverage and Boundaries: what is in scope and what routes elsewhere.
6. Branch Selection Rules: when to load each branch.
7. Question Style: newcomer-friendly questions only when needed.
8. After Every Branch: summarize state and offer nearby next actions.
