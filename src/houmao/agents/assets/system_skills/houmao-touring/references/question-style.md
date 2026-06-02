# Question Style

Use this reference when `houmao-touring` needs to ask the user for input during the guided tour.

## Rules

- Name the concept in plain language before asking for the value.
- Briefly explain why the value matters.
- Give one to three realistic examples.
- For Houmao system setup or lifecycle questions, label `Required` values separately from `Optional` defaults, modifiers, or skip paths.
- When the branch is optional, offer either a recommended default or a clear skip-for-now path.
- Keep the question helpful and readable for first-time users rather than terse for expert operators.
- Do not force `Required`/`Optional` labels onto user-task or domain-goal questions unless the question is about Houmao runtime behavior.

## Example Prompts

### Specialist Name

Use a shape like:

```text
What specialist name do you want?

A specialist is a reusable agent template that you can launch more than once later.

Required:
- specialist name

Optional:
- none for this step

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

The first decision is usually whether you only want to initialize the shared mailbox root now, or whether you also want to create one manually named mailbox account right away.

If you plan to launch specialist-backed agents with ordinary addresses such as `<agent-name>@houmao.localhost`, that per-agent mailbox can usually be created by the later launch step instead of by preregistering every agent address now.

Required if you choose mailbox setup:
- mailbox setup choice: root only, or root plus one manual account

Optional:
- manual mailbox address and principal id; skip them when you only want the shared root
- skip this branch for now

Examples:
- address: `research@houmao.localhost`
- principal id: `HOUMAO-research`

Mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals, so `HOUMAO-research@houmao.localhost` is not the ordinary managed-agent mailbox-address pattern.

Recommended default: initialize the mailbox root now, skip manual per-agent account registration unless you already know you need one shared or manually named mailbox account.

You can skip this now and come back later.
```

### Optional Project Profile

Use a shape like:

```text
Do you want to create an project profile too?

An project profile stores reusable launch defaults on top of a specialist. It is optional for a first launch.

Required if you choose this branch:
- project profile name

Optional:
- skip this branch for the first launch

Examples:
- `reviewer-default`
- `researcher-headless`

Recommended default: skip this for the first launch unless you already know you want repeated launch defaults.
```

### Live Operations Next Step

Use a shape like:

```text
Your agent is running. What do you want to try next?

Required:
- next Houmao operation

Optional:
- target agent name when only one agent is running
- skip live follow-up for now

Common first actions:
- send a normal prompt
- watch live gateway or TUI state
- send a mailbox message
- if the gateway is up and mailbox accounts are set up, enable automatic email notification so the agent can process open mail automatically
- create a reminder
- create another specialist and launch a second agent
```

### Stop, Relaunch, Or Cleanup

Use a shape like:

```text
What do you want to do with this agent now?

Required:
- lifecycle action
- target managed-agent name or id

Optional:
- list current agents first when the target is unclear
- cleanup scope or relaunch posture when relevant

- `stop`: end the live session
- `relaunch`: restart the managed session without treating it as a fresh launch
- `cleanup`: remove artifacts for a stopped session

Examples:
- stop `research`
- relaunch `reviewer-1`
- clean up logs for `research`

If you are not sure which agents exist, list current agents first.
```
