# Houmao Touring Domain Language

This language file defines terms for the `houmao-touring` guided-tour system skill. Use these terms when describing the skill's scope, entry behavior, branch selection, audience, and user-facing guidance.

## Language

**Touring skill**:
The high-level Houmao-owned guide for users who are not yet familiar with Houmao, including first-run users, re-orienting operators, and developers who want to inspect the system's working logic. It orients from current state, teaches nearby concepts, and routes selected work to owning skills.
_Avoid_: command owner, catalog, manager

**Direct-operation skill**:
A Houmao-owned skill that owns a concrete operation such as project setup, credential work, agent definition, messaging, gateway work, mailbox work, memory, inspection, lifecycle, loop operation, or workspace preparation.
_Avoid_: sub-feature, command family when referring to the skill itself

**Stage**:
One learning level in the guided tour: beginner, intermediate, or advanced.
_Avoid_: install set, category, module

**Branch**:
One guided path inside the tour, such as quickstart, project and mailbox setup, author and launch, live operations, advanced usage, or lifecycle follow-up.
_Avoid_: feature category, menu item

**Current-state orientation**:
The initial inspection step that determines the project overlay, reusable specialist, reusable profile, running managed-agent, mailbox, gateway, memory, and lifecycle posture needed for the current request.
_Avoid_: onboarding reset, setup wizard

**No-prompt entrypoint**:
A bare `houmao-touring` invocation where the user gives no task beyond activating the tour. The tour treats this as an orientation request, scans for existing Houmao project state, infers likely user intent from that state, and presents an introduction plus next-step instructions.
_Avoid_: empty greeting, activation acknowledgement, passive waiting state

**Intent guess**:
A low-risk inferred starting intent based on inspected Houmao state, such as setup from a blank workspace, operate from a running agent, coordinate from multiple running agents, or inspect subsystems when the user appears component-minded. The guess is an offer with alternatives, not a hidden automatic action.
_Avoid_: silent automation, forced path, random recommendation

**Stage-aware next action**:
A suggested next step that matches the inspected state and current learning stage.
_Avoid_: generic recommendation, full catalog entry

**Fast path**:
A shortcut route for a user who wants a concrete Houmao outcome with minimal explanation.
_Avoid_: default path, silent automation

**Subsystem exploration**:
A developer-minded touring section that explains Houmao by component area, such as project overlay, agent definition, managed runtime, gateway, messaging, mailbox, memory, inspection, workspace, and loop orchestration.
_Avoid_: default tour, fast path, complete skill catalog

**Presentation example**:
An illustrative response shape packaged with the touring skill or one of its loaded branch files. It shows agents how to present result, current posture, next choices, and required input concisely without becoming a mandatory universal template.
_Avoid_: fixed template, transcript, command recipe

**Intent-first routing**:
The touring behavior of naming what the user wants to accomplish, then routing concrete work to the owning direct-operation skill instead of copying command syntax, option catalogs, or validation rules into the tour.
_Avoid_: command duplication, full workflow copy

**Progressive discovery**:
The tour's teaching style: introduce Houmao concepts when the user's inspected state or requested outcome makes them useful.
_Avoid_: full upfront tutorial, exhaustive catalog

**Outcome request**:
A touring request that asks for a concrete result, such as creating the first agent, talking to a running agent, inspecting what is running, or coordinating multiple agents.
_Avoid_: generic tour request

**Orientation request**:
A touring request that asks to start, orient, or understand the current project without selecting a concrete outcome yet.
_Avoid_: quickstart request

## Relationships

- The **touring skill** performs **current-state orientation** before selecting a **branch**.
- A **no-prompt entrypoint** performs **current-state orientation**, makes an **intent guess**, and presents next-step instructions instead of asking a generic open question.
- A **branch** belongs to a **stage**, but the tour remains non-linear; users can move between nearby branches as state changes.
- A **stage-aware next action** is an offer, not a mandate.
- An **intent guess** can choose the most likely next path to present first, but the response must still show nearby alternatives.
- A **fast path** is a kind of **outcome request** and still requires minimal orientation for safety.
- **Subsystem exploration** is a browsing and learning mode for component-minded users, not the default outcome path.
- A **presentation example** guides response shape but does not override the rule that each branch may use a different compact form.
- **Intent-first routing** keeps concrete execution owned by the relevant **direct-operation skill**.
- A **direct-operation skill** owns execution after the **touring skill** has routed the selected work.

## Flagged Ambiguities

- "Tour" can mean either an orientation-only request or a concrete guided outcome. Use **orientation request** when the user only wants to understand state, and **outcome request** when the user asks for a result.
- "Guess user intent" means infer likely next paths from inspected Houmao state. Do not perform a concrete operation without user confirmation.
- "Advanced" should mean generated loops, topology choices, and isolated workspaces. Do not use it as a catch-all for every packaged Houmao skill.
- "Quickstart" should mean the fastest path to one useful managed agent. Do not use it for generic help or full feature browsing.
- "Subsystem exploration" should mean a guided component map. Do not use it as permission to list every packaged skill or every low-level command.
- "Template" should mean **presentation example** unless a requirement explicitly says fixed template. Do not make one response shape mandatory for every touring step.
