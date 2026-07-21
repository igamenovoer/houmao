# Guided Paths

Load only the selected path. Teach the sequence and current posture, but keep welcome read only. When the user asks to perform a step, finish welcome and use the listed `$houmao-admin-entrypoint` handoff with all confirmed facts.

## Single Agent Full Run

Use this path to reach and operate one complete managed agent.

Teaching sequence:

1. Explain that a Houmao project overlay owns definitions, credentials, mailbox state, and managed memory without replacing the user's working tree.
2. Check tool readiness without choosing for the user: `command -v claude`, `command -v codex`, and `command -v kimi || command -v kimi-code`. Houmao supports tool adapters for `claude`, `codex`, and `kimi`.
3. Explain specialist, optional project profile, credential lane, working directory, prompt mode, and managed `agent` pack defaults.
4. Explain that launch produces a tmux-backed managed agent with identity, optional gateway, mailbox binding, and memory.
5. Introduce first follow-up choices: inspect status, send a prompt, read or append memory, send mail, enable the gateway notifier, stop, or relaunch.

Before handoff, recover the explicit project path, tool, credential name, role or specialist intent, workdir, launch posture, and any mailbox choice. Do not inspect credential values.

Execution handoff:

```text
$houmao-admin-entrypoint agent-definition create-agent-fast-forward
Selected guided path: Single Agent Full Run
Explicit project target: <path>
Tool and credential: <tool>, <credential-name>
Definition and launch choices: <facts>
Unresolved required inputs: <items-or-none>
```

If the agent already exists, hand off to `agent-inspect`, `agent-messaging`, `memory-mgr`, `agent-email-comms`, `agent-gateway`, or `agent-instance` instead of recreating it.

## Operator-Controlled Agent Team

Use this path when a human operator wants several agents and remains outside their execution loop.

Teaching sequence:

1. Inventory the intended roles, tools, credentials, and repository access boundaries.
2. Explain when agents may share one working directory and when `utils-workspace-mgr` should prepare isolated worktrees or knowledge directories.
3. Explain that each agent keeps its own verified identity, runtime home, gateway posture, mailbox binding, and managed memory.
4. Compare direct gateway prompts, operator mail, peer mail, notifier wakeups, and explicit inspection.
5. Explain lifecycle follow-up per target: status, stop, relaunch, and cleanup remain separate operations.

Before handoff, require the explicit project path and target agent names or proposed definitions. Preserve the operator's control objective and workspace constraints.

Typical planning handoff:

```text
$houmao-admin-entrypoint utils-workspace-mgr plan
Selected guided path: Operator-Controlled Agent Team
Explicit project target: <path>
Proposed agents and roles: <facts>
Workspace and communication constraints: <facts>
Unresolved required inputs: <items-or-none>
```

Typical dispatch handoff after targets exist:

```text
$houmao-admin-entrypoint operator-messaging clarify
Explicit managed-agent targets: <ids>
Requested outcome: <operator request>
```

## Pro Agent Loop

Use this path for a generated, schema-rich multi-agent loop. Explain that `tree-loop` and `generic-loop` are topology modes inside the same protected `agent-loop-pro` route.

Teaching sequence:

1. Clarify the loop objective, completion rule, participants, responsibilities, artifacts, and failure policy.
2. Compare `tree-loop` local-close ownership with `generic-loop` graphs that may contain cycles or relay lanes.
3. Explain the intention and execplan stages, including mail families, process contracts, graph validation, generated skills, harness behavior, state, and agent bindings.
4. Explain that agent definitions, mailbox/gateway posture, and workspace readiness are prepared and validated before launch.
5. Introduce run controls: start, status, pause, resume, recover, and stop.

Before handoff, require an explicit loop directory and project context. Preserve the objective and any known participant or topology facts.

Execution handoff:

```text
$houmao-admin-entrypoint agent-loop-pro init
Selected guided path: Pro Agent Loop
Explicit loop target: <directory>
Explicit project target: <path>
Objective and known topology facts: <facts>
Unresolved required inputs: <items-or-none>
```

Offer `agent-loop-lite` instead when the user explicitly wants a smaller Markdown/direct-SQL loop without generated schemas or harness code.

## Subsystem Exploration

Use this read-only path when the user wants the system's working logic before choosing an operation.

Offer these areas:

| Area | Explain |
|---|---|
| Project and definitions | Overlay ownership, credentials, specialists, profiles, recipes, and managed pack policy |
| Runtime and control | Managed identity, tmux sessions, lifecycle, gateway, messaging, inspection, and memory |
| Communication | Mailbox roots, accounts, peer mail, operator mail, notifier rounds, and reminders |
| Team structure | Workspace isolation, lite/pro loops, AG-UI interop, and graphing |

Load [concepts.md](concepts.md) for vocabulary. Explain internal ownership with an entrypoint-qualified route trace, never a standalone `$houmao-<routine>` prompt. If the user then requests work, select the eligible admin route and use [admin-handoff.md](admin-handoff.md).

## Existing Project Reorientation

Use this path when `.houmao/` already exists or the user returns to an unfamiliar project.

Read-only sequence:

1. Summarize project status and overlay location.
2. Summarize specialist and profile names without exposing credential contents.
3. Summarize managed-agent lifecycle posture and identify explicit ids for possible follow-up.
4. Summarize mailbox, gateway, memory, workspace, and loop evidence only where it exists or affects the next choice.
5. Recommend one next public admin-entrypoint invocation and offer `more detail` or another path.

Do not restart from project initialization when an overlay already exists. Build the next handoff from observed state, for example:

```text
$houmao-admin-entrypoint agent-inspect discover for <agent-id>
Selected guided path: Existing Project Reorientation
Explicit project target: <path>
Read-only observations: <facts>
```
