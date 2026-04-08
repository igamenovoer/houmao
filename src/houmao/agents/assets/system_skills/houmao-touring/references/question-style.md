# Question Style

Use this reference when `houmao-touring` needs to ask the user for input during the guided tour.

## Rules

- Name the concept in plain language before asking for the value.
- Briefly explain why the value matters.
- Give one to three realistic examples.
- When the branch is optional, offer either a recommended default or a clear skip-for-now path.
- Keep the question helpful and readable for first-time users rather than terse for expert operators.

## Example Prompts

### Specialist Name

Use a shape like:

```text
What specialist name do you want?

A specialist is a reusable agent template that you can launch more than once later.

Examples:
- `researcher`
- `reviewer`
- `ops-helper`

If you do not care yet, `researcher` is a good first choice.
```

### Optional Project Mailbox Setup

Use a shape like:

```text
Do you want to set up a project-local mailbox now?

This lets managed agents in this project send and receive shared mail through the project mailbox.

Examples:
- address: `HOUMAO-research@agents.localhost`
- principal id: `HOUMAO-research`

You can skip this now and come back later.
```

### Optional Easy Profile

Use a shape like:

```text
Do you want to create an easy profile too?

An easy profile stores reusable launch defaults on top of a specialist. It is optional for a first launch.

Examples:
- `reviewer-default`
- `researcher-headless`

Recommended default: skip this for the first launch unless you already know you want repeated launch defaults.
```

### Live Operations Next Step

Use a shape like:

```text
Your agent is running. What do you want to try next?

Common first actions:
- send a normal prompt
- watch live gateway or TUI state
- send a mailbox message
- create a reminder
- create another specialist and launch a second agent
```

### Stop, Relaunch, Or Cleanup

Use a shape like:

```text
What do you want to do with this agent now?

- `stop`: end the live session
- `relaunch`: restart the managed session without treating it as a fresh launch
- `cleanup`: remove artifacts for a stopped session

Examples:
- stop `research`
- relaunch `reviewer-1`
- clean up logs for `research`

If you are not sure which agents exist, list current agents first.
```
