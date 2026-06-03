## Context

`houmao-touring` currently works as a branching guided learning skill, but much of its behavior is expressed as broad scope and branch lists. The top-level workflow still frames the skill primarily as a first-time guided tour, and it does not give agents a crisp enough contract for choosing between orientation, outcome-driven fast paths, and component-oriented subsystem exploration.

The design notes under `docs/design/` introduce durable terminology and decisions for this revision:

- the touring skill is for users not yet familiar with Houmao, including first-run users, re-orienting operators, and developers inspecting system logic;
- the tour has two coverage lanes: fast path use cases and subsystem exploration;
- fast paths are three outcome use cases, not many small command aliases;
- every step should stay compact and end with nearby next choices.

The packaged skill content must remain self-contained under `src/houmao/agents/assets/system_skills/houmao-touring/`. Development-only docs can guide this change but cannot be cited by installed skill content.

## Goals / Non-Goals

**Goals:**

- Make the top-level `houmao-touring` entry behavior deterministic enough for different agents to produce similar first-turn output.
- Reframe the audience from strictly first-time users to users not yet familiar with Houmao.
- Add explicit fast path use cases:
  - Single Agent Full Run,
  - Operator-Controlled Agent Team,
  - Pro Agent Loop.
- Add a subsystem-exploration path for component-minded users.
- Keep the tour compact by default and put expanded detail behind `more detail`.
- Include concise presentation examples in packaged skill content so agents have adaptable response shapes.
- Preserve execution ownership on direct-operation skills.

**Non-Goals:**

- Do not add new Houmao runtime commands or direct-operation semantics.
- Do not make `houmao-touring` the default router for ordinary narrow requests.
- Do not turn subsystem exploration into a full packaged skill catalog or command reference.
- Do not add a third advanced-operation guide lane in this change.

## Decisions

### Decision: Use Two Coverage Lanes

The revised touring skill will present two coverage lanes:

| Lane | Role |
| --- | --- |
| Fast path use cases | Outcome-driven routes for users who want Houmao to do useful work quickly. |
| Subsystem exploration | Component-oriented routes for users who want to understand how Houmao works. |

This separates user momentum from system comprehension. The previous broad beginner/intermediate/advanced branch model remains useful inside fast path progress and next-action suggestions, but it should not be the only way to enter the tour.

Alternative considered: keep a single staged learning path. That keeps the current structure smaller, but it does not serve developer-minded users who want to inspect component logic without walking through a first-agent setup sequence.

### Decision: Make Fast Paths Use Cases

The revised skill will expose three fast path use cases:

| Use Case | Purpose |
| --- | --- |
| Single Agent Full Run | Create and operate one fully functional managed agent across project, launch, gateway, mailbox, notifier, memory, inspection, and reminders. |
| Operator-Controlled Agent Team | Create multiple fully functional agents and manually control them through prompts, mail, notifier posture, inspection, memory, reminders, and lifecycle follow-up. |
| Pro Agent Loop | Define and construct a generated loop through `houmao-agent-loop-pro`, including topology choice, participant roles, workspace preparation when needed, validation, launch, and operation. |

This avoids a long list of micro fast paths such as `talk`, `inspect`, `mail`, and `notify`. Those remain operations available inside a use case or through direct-operation skills.

### Decision: Add a Subsystem-Exploration Branch

The revised skill will add a branch page for subsystem exploration and route explicit component-exploration requests there. The branch will present a compact component map and then let the user choose a subsystem to inspect.

The accepted subsystem map is:

| Subsystem | Scope |
| --- | --- |
| Project overlay | Project state, catalogs, credentials, mailbox, memory, and runtime metadata. |
| Agent definition | Roles, recipes, credentials, specialists, profiles, and launch defaults. |
| Managed runtime | Tmux-backed managed sessions and lifecycle state. |
| Gateway | Sidecar live control, state, watch, reminders, and mail-notifier. |
| Messaging | Direct prompt, interrupt, raw input, queue, and mailbox-routed work. |
| Mailbox | Mailbox roots, accounts, operator-origin mail, inter-agent mail, and notifier rounds. |
| Memory | Memo and pages. |
| Inspection | State, screen posture, logs, turn evidence, mailbox posture, and artifacts. |
| Workspace | Isolated multi-agent working directories. |
| Loop orchestration | Pro loops, topology, contracts, validation, launch, and operation. |

Passive server and deeper TUI tracking internals can appear only through `more detail` or explicit advanced-internals requests; they should not be primary subsystem-exploration entries.

### Decision: Prefer Compact Step Output Over a Universal Template

The touring skill should not force one response template onto every branch. Each step should report only the critical operation result, current status, next choices, and required input. It should prefer small Markdown tables for status and choices, with at most four columns, when a table is clearer than a list.

Packaged skill content should include one or more presentation template examples. These examples are scaffolding for consistent agent behavior, not a universal response contract. They should use concise language, focus on the user's intent and current posture, and show how to present next choices and required input. They should not teach low-level command invocation unless the user asks for `more detail`.

The tour should invite `more detail` for expanded concept explanations, command examples, raw inspection output, or deeper architecture detail. This prevents ordinary tour steps from becoming reference pages.

### Decision: Route by Intent, Do Not Duplicate Owner Skills

The touring skill should name the user's intent and route concrete work to the maintained direct-operation skill where possible. It should not copy detailed workflows, command syntax, option catalogs, or validation rules from owner skills into touring content.

This keeps touring stable as the command-owning skills evolve. It also keeps the tour focused on what the user is trying to do, what Houmao state matters now, and what decision the user needs to make next.

### Decision: Keep Implementation Self-Contained

All installed touring content must remain inside the packaged skill asset directory. The implementation may add branch or reference files under that directory, but `SKILL.md` and branch pages must not link to `docs/design/`, `openspec/`, or other source-repository-only paths.

## Risks / Trade-offs

- [Risk] The touring skill becomes too broad again after adding subsystem exploration. → Keep subsystem exploration explicitly component-oriented and prohibit broad skill catalog output.
- [Risk] Fast paths duplicate direct-operation skill workflows. → Make fast paths describe goals and routing only; leave concrete command ownership to direct-operation skills.
- [Risk] Compact output hides useful detail from new users. → Use the `more detail` expansion path and always offer next choices.
- [Risk] Existing tests only assert broad content anchors and miss entry-contract regressions. → Add tests for new anchors such as the two coverage lanes, fast path use-case names, subsystem-exploration branch, `more detail`, and table column guidance.
