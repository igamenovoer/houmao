---
name: houmao-touring
description: Use Houmao's manual guided touring skill to orient first-time or re-orienting users through beginner, intermediate, and advanced Houmao learning stages.
license: MIT
---

# Houmao Touring

Use this Houmao skill only when the user explicitly asks for `houmao-touring` or clearly asks for a first-time guided Houmao tour. This is a manual learning-path skill, not the default entrypoint for ordinary direct-operation requests and not a full catalog browser for every packaged Houmao function.

`houmao-touring` is intentionally above the direct-operation skills. It inspects current Houmao state, explains the current posture in plain language, offers stage-aware next actions, and routes selected work to the maintained Houmao-owned skill that owns that surface.

The trigger word `houmao` is intentional. Use the `houmao-touring` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-touring help`, `help for houmao-touring`, `usage for houmao-touring`, `available functionality for houmao-touring`, or what this skill can do, answer from this section. Present this help before the welcome, state inspection, branch selection, skill routing, command execution, or missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me tour this Houmao project", route to the guided tour instead of stopping at generic help.

Purpose: provide a manual guided Houmao tour that starts from current state, teaches the system in beginner, intermediate, and advanced stages, and routes selected work to maintained owning skills.

Available functionality:

- Orient from current project, specialist, profile, managed-agent, mailbox, gateway, and memory-relevant state.
- Guide the beginner stage: tool selection, credentials, project/mailbox basics, specialists, optional project profiles, launch, and first conversation.
- Guide the intermediate stage: memo/pages, direct prompts, inter-agent mailbox messaging, operator-origin mail or prompt injection through mail, notifier rounds, reminders, and inspection.
- Guide the advanced stage: loop-lite, loop-pro tree/generic modes, and isolated multi-agent workspace management.
- Explain likely next actions in first-time-user-friendly language.
- Route actual work to the Houmao skill that owns the selected surface.

Common starting prompts:

- `$houmao-touring help`
- `$houmao-touring start a guided tour`
- `$houmao-touring orient me in this project`
- `$houmao-touring help me create and talk to my first agent`
- `$houmao-touring show intermediate agent communication options`
- `$houmao-touring show advanced loop and workspace options`

Related skills and boundaries:

- Use direct-operation skills such as `houmao-project-mgr`, `houmao-agent-definition`, `houmao-mailbox-mgr`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-inspect`, `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, `houmao-memory-mgr`, and `houmao-agent-instance` for ordinary narrow tasks.
- Use `houmao-agent-loop-lite` or `houmao-agent-loop-pro` for current loop authoring and generated loop operation.
- Use `houmao-utils-workspace-mgr` for isolated multi-agent workspace planning, creation, validation, or summaries.
- Use `houmao-adv-usage-pattern` for elemental multi-skill mailbox or gateway patterns when the user asks for those patterns before generated loops.
- Do not use this skill as the default entrypoint when the user did not ask for a guided tour.
- Do not use this skill as the normal place to discover unrelated utility workflows; direct skill help and system-skills reference docs own that reference posture.

## Learning Stages

### Beginner

Beginner guidance teaches the path to one useful managed agent and a first conversation:

1. Inspect or create the project overlay.
2. Choose an available tool CLI such as `claude`, `codex`, or `gemini`.
3. Prepare or select credentials for that tool.
4. Understand mailbox basics: mailbox root setup is distinct from per-agent mailbox account ownership.
5. Create a specialist.
6. Optionally create a project profile for reusable launch defaults.
7. Launch one managed agent with foreground-first tour posture.
8. Talk to the agent through the maintained prompt/messaging surface.

### Intermediate

Intermediate guidance teaches live operation and manual coordination once at least one managed agent exists:

1. Inspect what the agent is doing through supported read-only surfaces.
2. Use memo and pages for durable managed-agent context.
3. Choose between direct prompt, mailbox message, and operator-origin mail.
4. Use mail as a prompt-injection channel when the task is intentionally mailbox-driven.
5. Configure or inspect gateway mail-notifier posture when mailbox accounts and a live gateway are ready.
6. Process one notifier-reported open-mail round through the gateway when the prompt provides the gateway base URL.
7. Create reminders or coordinate more than one running agent manually.

### Advanced

Advanced guidance teaches composed multi-agent systems:

1. Use `houmao-agent-loop-lite` for lightweight Markdown/direct-SQL generated loops.
2. Use `houmao-agent-loop-pro` for schema-rich generated loops.
3. Choose `tree-loop` or `generic-loop` as topology modes inside pro.
4. Use `houmao-utils-workspace-mgr` for isolated multi-agent workspace planning, creation, validation, or summaries before launches or loop runs.

## Welcome Message

When the user starts the guided tour, present a welcome message that adapts to the inspected current Houmao state. Keep the welcome user-facing and never imply that the user must restart from the beginning when Houmao state already exists. Do not repeat the welcome on every turn; if the recent conversation already covered it, skip it and proceed with the current-state orientation.

### Full Welcome (Blank-Slate Workspace)

Present the full welcome only when the workspace has no project overlay, no reusable specialists, and no running managed agents. Use the following baseline:

Welcome to Houmao. Houmao is a framework and CLI toolkit for orchestrating teams of loosely coupled CLI-based AI agents such as Claude, Codex, and Gemini. Each agent is a real CLI process with its own disk state, memory, native TUI, mailbox posture, and optional gateway sidecar. The tour starts with beginner setup so you can create one agent and talk to it, then opens intermediate live-operation guidance and advanced loop/workspace guidance when those concepts become useful.

A typical beginner setup path is:

1. Create or inspect a Houmao project and understand the mailbox root.
2. Choose an available tool CLI and prepare credentials.
3. Create a specialist: customize its system prompt, choose the provider/tooling posture, and select credentials.
4. Create an optional project profile when reusable launch defaults matter.
5. Launch the agent. The default tour posture is a visible TUI managed agent with a foreground gateway sidecar.
6. Talk to the agent through the maintained messaging surface, then decide whether to inspect state, use memo/mailbox, launch a second agent, or move toward advanced coordination.

Start by checking what already exists here, then suggest stage-aware next actions instead of restarting from scratch.

### Short Acknowledgement (Workspace Already Has State)

Present a short one-to-two-sentence acknowledgement in place of the full welcome whenever the inspected workspace already has any of: a project overlay, one or more reusable specialists, one or more running managed agents. Follow it immediately with the current-state orientation and the stage-aware offered next actions from the orient branch's posture-to-action matrix. Do not push the user back into the full initial setup sequence in that case.

## Scope

This packaged skill covers a branching guided learning path for:

- current-state orientation
- beginner project overlay setup or inspection
- beginner mailbox subsystem basics
- beginner tool selection and credential readiness
- beginner specialist creation
- beginner optional project-profile creation
- beginner easy-instance launch
- beginner first prompt or conversation
- intermediate managed-agent memo and pages orientation
- intermediate post-launch prompt entry
- intermediate ordinary mailbox send, read, reply, post, or archive entry
- intermediate operator-origin mail or prompt injection through mail
- intermediate gateway mail-notifier follow-up when a live gateway and mailbox are both ready
- intermediate notifier-reported open-mail round processing
- intermediate read-only inspection, screen watching, logs, turn-state evidence, and mailbox posture
- intermediate reminders and manual multi-agent coordination
- advanced loop creation or generated-loop operation through `houmao-agent-loop-lite` or `houmao-agent-loop-pro`
- advanced isolated multi-agent workspace planning, creation, validation, or summaries through `houmao-utils-workspace-mgr`
- managed-agent inspection, stop, relaunch, join/adopt, and cleanup follow-up

This packaged skill does not cover:

- ordinary direct-operation requests that the user did not ask to route through the tour
- low-level command ownership for project, mailbox, specialist, messaging, gateway, memory, loop-planning, workspace, or lifecycle actions
- unrelated packaged utility workflows that are not part of first-user agent creation, live operation, manual coordination, loop authoring, or isolated workspace management
- ad hoc filesystem editing under `.houmao/`, runtime, workspace, memory, or mailbox paths
- destructive cleanup as an automatic side effect of stop

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Confirm that the user explicitly wants the guided touring experience instead of one narrow direct-operation task.
2. Present the welcome message, including the typical beginner setup path, unless the recent conversation already covered it.
3. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
4. Start from current-state orientation rather than assuming the tour begins at project initialization:
   - inspect project posture through `houmao-mgr project status`
   - inspect reusable specialists through `houmao-mgr project specialist list` or `houmao-mgr project specialist get --name <name>` when the branch needs them
   - inspect reusable profiles through `houmao-mgr project profile list` or `houmao-mgr project profile get --name <name>` when the branch needs them
   - inspect running managed agents through `houmao-mgr agents global list`
   - inspect one live managed agent through `houmao-mgr agents single --agent-name <name> state`, `houmao-mgr agents single --agent-name <name> gateway status`, or `houmao-mgr agents single --agent-name <name> mail resolve-live` when the branch needs live capability
   - inspect managed-agent memory posture through `houmao-mgr agents single --agent-name <name> memory status` only when the selected branch needs memo or pages context
5. Explain the current posture in plain language and offer stage-aware next actions.
6. Load exactly one branch page for the next selected tour branch:
   - `branches/orient.md`
   - `branches/quickstart.md`
   - `branches/setup-project-and-mailbox.md`
   - `branches/author-and-launch.md`
   - `branches/live-operations.md`
   - `branches/advanced-usage.md`
   - `branches/lifecycle-follow-up.md`
7. Route execution to the maintained Houmao-owned skill that owns the selected branch.
8. After that branch completes, summarize the new current state and offer stage-aware next actions again.

## Branches

- Read [branches/orient.md](branches/orient.md) to inspect current Houmao posture and present stage-aware next touring actions from the posture-to-action routing table.
- Read [branches/quickstart.md](branches/quickstart.md) for the beginner minimum-viable path to one running managed agent; the branch detects available host tool CLIs and routes authoring, credential selection, and launch through the maintained skills.
- Read [branches/setup-project-and-mailbox.md](branches/setup-project-and-mailbox.md) for beginner project overlay setup or mailbox subsystem basics.
- Read [branches/author-and-launch.md](branches/author-and-launch.md) for beginner specialist/profile authoring or launching another agent.
- Read [branches/live-operations.md](branches/live-operations.md) for intermediate prompt, memo, mailbox, notifier-round, gateway, reminder, inspection, or manual coordination work against running agents.
- Read [branches/advanced-usage.md](branches/advanced-usage.md) for advanced loop-lite, loop-pro tree/generic mode, and isolated workspace guidance.
- Read [branches/lifecycle-follow-up.md](branches/lifecycle-follow-up.md) for intermediate lifecycle inspection, stop, relaunch, join/adopt, or cleanup follow-up.

## References

- Read [references/question-style.md](references/question-style.md) when the tour needs to ask for user input in a first-time-user-friendly way with explanations, examples, and recommended defaults or skip options.
- Read [references/concepts.md](references/concepts.md) when the tour needs a compact self-contained glossary for the vocabulary used across branches. That reference covers: specialist, project profile, launch profile, managed agent, recipe, tool adapter, gateway, gateway sidecar, mailbox root, mailbox account, principal id, prompt injection through mail, notifier round, user agent, master, loop plan, lite loop, pro loop, tree-loop, generic-loop, isolated workspace, relaunch, and cleanup.

## Routing Guidance

- Route project overlay setup or explanation to `houmao-project-mgr`.
- Route mailbox root, account, registration, or late-binding administration to `houmao-mailbox-mgr`.
- Route credential readiness and credential content work to `houmao-credential-mgr` when credential mutation or inspection is needed.
- Route specialist, project profile, launch dossier, `create-agent-fast-forward`, and easy-instance launch work to `houmao-agent-definition`.
- Route generic managed-agent inspection, live screen watching, mailbox-posture inspection, logs, turn-state evidence, and runtime artifact inspection to `houmao-agent-inspect`.
- Route ordinary prompt, interrupt, raw input, or mailbox-routing entry for running agents to `houmao-agent-messaging`.
- Route gateway lifecycle, gateway watch, gateway mail-notifier, and reminder work to `houmao-agent-gateway`.
- Route ordinary mailbox send, read, reply, post, or archive follow-up to `houmao-agent-email-comms`.
- Route one gateway-notified open-mail processing round with prompt-provided gateway base URL to `houmao-process-emails-via-gateway`.
- Route managed-agent memo, pages, or launch-profile memo-seed work to `houmao-memory-mgr`.
- Route lightweight Markdown/direct-SQL loop authoring, validation, and generated loop execution to `houmao-agent-loop-lite`.
- Route schema-rich loop authoring, generated execplan validation, topology-heavy planning, and generated loop execution to `houmao-agent-loop-pro`.
- Present tree-loop and generic-loop as topology choices inside `houmao-agent-loop-pro`, not as separate skill packages.
- Route isolated multi-agent workspace planning, creation, validation, or summaries to `houmao-utils-workspace-mgr`.
- Route elemental immediate driver-worker edge protocol details to `houmao-adv-usage-pattern`, not to the touring skill.
- Route stop, relaunch, join/adopt, list, and cleanup follow-up to `houmao-agent-instance`.

## Guardrails

- Do not activate `houmao-touring` unless the user explicitly asked for the guided tour experience.
- Keep the tour focused; do not turn it into a full catalog of every packaged Houmao system skill.
- Never force a linear step order or restart the user from project initialization when current Houmao state already exists.
- Do not claim ownership of the direct-operation command shapes that belong to the maintained Houmao skill families.
- Avoid inventing top-level `houmao-mgr easy ...` or `houmao-mgr specialists ...` commands; reusable specialist and profile inspection lives under `houmao-mgr project ...`.
- Keep stop, relaunch, and cleanup as separate actions rather than collapsing them into one vague "manage agent" action.
- Do not ask terse operator-style missing-input questions when the tour needs first-time-user guidance; use the question-style reference instead.
- Route current loop planning and generated loop run-control requests only to the maintained loop packages.
- Keep composed tree/generic loop topology, run-control details, typed-template rules, direct-SQL state rules, isolated workspace creation or validation rules, and elemental local-close edge-loop protocol on their owning skills. Route generated loop planning to `houmao-agent-loop-lite` or `houmao-agent-loop-pro`. Route workspace preparation to `houmao-utils-workspace-mgr` and elemental patterns to `houmao-adv-usage-pattern`.
- Never auto-run cleanup after stop or treat cleanup as safe for a live session.
- Do not reference paths outside `src/houmao/agents/assets/system_skills/houmao-touring/` from any touring content. The packaged touring skill ships through pypi as part of the Houmao distribution. Paths under `examples/`, `docs/`, `magic-context/`, `openspec/`, or any other development-repository-only location are not reachable after `pip install`. They SHALL NOT be cited by `SKILL.md`, any file under `branches/`, any file under `references/`, or any future file added to the packaged asset directory.
