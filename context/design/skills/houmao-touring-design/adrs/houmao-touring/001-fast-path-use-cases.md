# Houmao Touring Fast Path Use Cases

`houmao-touring` will define three fast path use cases: **Single Agent Full Run**, **Operator-Controlled Agent Team**, and **Pro Agent Loop**. These fast paths should lead outcome-focused users into progressively discovering Houmao by doing useful work, rather than by browsing a catalog of packaged skills.

## Status

accepted

## Decision

The touring skill will treat fast paths as use cases, not as small command aliases or branch shortcuts.

The three fast path use cases are:

1. **Single Agent Full Run**: create and operate one fully functional managed agent. This covers project overlay readiness, tool and credential readiness, specialist or profile setup as needed, foreground-first launch, gateway posture, mailbox setup or binding, first prompt, inspection, memo or pages, mailbox send or read, gateway mail-notifier readiness, and reminders.
2. **Operator-Controlled Agent Team**: create multiple fully functional managed agents and control them manually as the operator. This covers multiple specialists or launches, per-agent gateway and mailbox readiness, direct prompts, operator-origin mail, inter-agent mailbox messages, notifier setup, inspection, memo or pages, reminders, and lifecycle follow-up.
3. **Pro Agent Loop**: define and construct an agent loop through `houmao-agent-loop-pro`. This covers loop intent, participant roles, `tree-loop` or `generic-loop` topology choice, mailbox and runtime contracts, isolated workspace preparation when needed, generated artifact validation, participant launch, and generated loop operation.

The progression is:

```text
single fully functional agent
  -> operator-controlled team
  -> generated pro loop
```

## Rationale

This keeps the touring skill focused on progressively useful outcomes. A user who is not yet familiar with Houmao can learn by creating and operating one complete agent, then by manually coordinating a small team, then by moving to generated loop orchestration when manual control becomes too repetitive or structured.

The alternative was to expose many narrower fast paths such as `talk`, `inspect`, `mail`, `notify`, `coordinate`, `loop`, and `lifecycle`. That would make the tour feel like a feature catalog and would give agents too many entrypoint choices to present consistently.

## Consequences

- The single-agent fast path must exercise core Houmao surfaces, including gateway, mailbox, mail notification, inspection, memory, and reminders, not merely launch an agent.
- The multi-agent fast path stays operator-controlled and manual; it should not jump directly to generated loops unless the user asks for loop construction or repeated coordination becomes the stated goal.
- Advanced fast-path guidance centers on `houmao-agent-loop-pro`, including topology choice and generated loop construction, rather than presenting every advanced or utility skill.
- The packaged `houmao-touring` entrypoint should route users into these use cases through clear outcome language.
- At the end of each touring step, the touring skill should tell the user what can happen next. When more than one path is reasonable, it should present the next possible branches or actions so a new user can see the nearby Houmao feature surface without reading a catalog.
- Touring output should not use one rigid template for every step. It should stay compact by default, focus on operation result, critical current status, brief next-step choices, and required input, and let the user ask for `more detail` when they want fuller explanations or raw evidence.
- Touring output should prefer small Markdown tables over vertical lists for status, operation choices, and branch choices. Tables should stay scannable and use at most four columns.
