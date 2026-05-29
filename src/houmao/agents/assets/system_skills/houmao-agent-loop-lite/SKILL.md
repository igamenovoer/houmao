---
name: houmao-agent-loop-lite
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-lite` or an explicitly named lite loop operation to author or operate Markdown/direct-SQL generated loops with required typed Markdown templates and generated skills.
---

# Houmao Agent Loop Lite

## Activation

- Use this Houmao skill only after the user explicitly selects `houmao-agent-loop-lite` or names a supported lite loop operation.
- If the user invokes explicit help intent, answer from `## Help` before treating a no-operation invocation as `init` or asking for `<loop-dir>`.
- If the user invokes this skill without another operation or prompt:
  - treat it as `init`;
  - ask for the output `<loop-dir>`;
  - do not create files until the user provides it.
- Do not auto-route generic loop requests here when the user did not explicitly select lite.
- Use `houmao-agent-loop-pro` instead when the user explicitly asks for the schema-rich, topology-heavy generated-execplan path with pro validation and run-control surfaces.

## Help

When the user asks `$houmao-agent-loop-lite help`, `help for houmao-agent-loop-lite`, `usage for houmao-agent-loop-lite`, `available functionality for houmao-agent-loop-lite`, or what this skill can do, answer from this section before choosing an operation, requiring `<loop-dir>`, generating Markdown contracts, generating skills, touching SQLite state, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me create a lite loop", route to the matching workflow instead of stopping at generic help.

Purpose: author and operate lightweight generated loops that use Markdown contracts, typed Markdown templates, required generated skills, and direct SQLite state.

Available functionality:

- `init`, `clarify`, `generate-skills`, and `validate` a minimal lite loop package.
- Generate the default `intention/`, `execplan/`, `specs/`, `skills/`, `agents/`, and `runs/` spine.
- Enforce typed Markdown templates with `<placeholder ...>` tokens and Houmao envelope boundaries.
- Prepare and launch agents, start runs, inspect status, pause, resume, stop, and recover lite loops.
- Require generated shared and receiver skills for loop-local operation.

Common starting prompts:

- `$houmao-agent-loop-lite help`
- `$houmao-agent-loop-lite init <loop-dir>`
- `$houmao-agent-loop-lite generate-skills <loop-dir>`
- `$houmao-agent-loop-lite validate <loop-dir>`

Related skills and boundaries:

- Use `houmao-agent-loop-pro` for schema-rich topology-heavy execplans, JSON schemas, Jinja2 rendering, generated harness, or generated docs layers.
- Use `houmao-agent-definition`, `houmao-agent-instance`, `houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-messaging`, `houmao-agent-inspect`, and `houmao-utils-workspace-mgr` for maintained platform operations.
- Use `houmao-adv-usage-pattern` for elemental direct mailbox or gateway compositions outside generated loop packages.
- Do not auto-route generic loop requests here when the user did not explicitly select lite.

## Required Root

- Require one user-selected `<loop-dir>` before creating or changing files.
- Keep `<loop-dir>/intention/` as editable source material.
- Keep `<loop-dir>/execplan/` as generated operational material.
- Keep `<loop-dir>/runs/` as durable runtime artifacts.
- Use `execplan/specs/`, `execplan/skills/`, and `execplan/agents/` for lite concern areas.
- Do not generate `execplan/harness/` or `execplan/docs/`.

```text
<loop-dir>/
  intention/
  execplan/
    specs/
    skills/
    agents/
  runs/
```

## Operations

Meta:
- `help`: explain this skill's purpose, operations, default shape, common prompts, and related-skill boundaries without requiring `<loop-dir>` or doing default `init`.

Authoring:
- `init`: scaffold the smallest editable intention surface and a default generated lite package after the user selects `<loop-dir>`.
- `clarify`: scan intention and generated Markdown contracts, ask only high-impact questions, and record accepted answers back into Markdown source or generated specs.
- `generate-skills`: generate or refresh loop-local skills under `execplan/skills/` from the Markdown specs, typed templates, state contract, and participant bindings.
- `validate`: validate the lite package shape, typed templates, generated-skill coverage, forbidden directories, placeholder posture, and SQLite schema parseability.

Execution:
- `prepare-agents`: prepare participant profiles, generated skill bindings, and agent facts by routing agent-definition work through `houmao-agent-definition`.
- `launch-agents`: launch prepared agents through `houmao-agent-instance` after validation and before `start`.
- `start`: create or select one run under `runs/<run-id>/`, initialize SQLite when needed, and send the first loop trigger.
- `status`: inspect the run, participant posture, mailbox refs, and SQLite facts without mutation.
- `pause`: pause normal scheduling, notifier, or wakeup posture when the generated loop defines those controls.
- `resume`: resume a paused lite loop.
- `stop`: stop normal loop work and route live-agent lifecycle actions through maintained Houmao skills.
- `recover`: restore a consistent run posture after interruption, failed setup, partial dispatch, or conflicting state.

## Default Generated Package

Generate the smallest complete package for the selected loop. Optional files and directories are absent by default; absence means the concern is not part of the generated lite loop.

Default shape:

```text
<loop-dir>/
  intention/
    README.md
    loop-overview.md
  execplan/
    README.md
    manifest.md
    specs/
      README.md
      objective.md
      organization.md
      process.md
      communication.md
      templates/
        task-request.md
        task-result.md
      state/
        README.md
        schema.sql
    skills/
      README.md
      <loop-slug>-shared-guide/
        SKILL.md
      <generated-receiver-skill>/
        SKILL.md
    agents/
      README.md
      bindings.md
  runs/
```

Optional material appears only when selected by the generated loop process:
- `execplan/specs/workspace.md`
- `execplan/specs/run-artifacts.md`
- `execplan/specs/state/seed.sql`
- `execplan/specs/state/queries.md`
- notifier prompts
- concrete profile definitions
- generated tick skills
- generated operator-control skills

## Markdown Contracts

- Use Markdown as the authority for the manifest, objective, organization, process, communication, generated skill index, and agent bindings.
- Do not create parallel TOML contract registries for lite.
- Do not create JSON schemas, Jinja2 renderers, generated harness commands, or generated docs as normal lite outputs.
- Store operational instructions in required README files only when agents must read them to operate the generated package.
- Keep generated Markdown direct and editable. Prefer explicit headings, tables, and bullet lists over hidden machinery.

## Communication Templates

- Every lite execplan has at least one communication template under `execplan/specs/templates/`.
- Each template is plain Markdown.
- Each template begins with a body-local prologue containing `Loop-Template-Type` and `Loop-Template-Version`.
- The prologue ends at the first blank line.
- Template bodies use literal `<placeholder ...>` tokens for content that must be filled.
- Do not use conditionals, loops, filters, or expression language in templates.
- Do not duplicate Houmao mail envelope fields in template bodies. Sender, receiver, subject, message id, thread id, timestamps, reply refs, and system headers belong to Houmao mailbox metadata.

Example:

```markdown
Loop-Template-Type: task-request
Loop-Template-Version: 1

# Task Request

Work item: <placeholder work_item_id>
Goal: <placeholder task_goal>
Required output: <placeholder expected_result>
State ref: <placeholder state_ref>
Artifact ref: <placeholder artifact_ref>
```

## Generated Skills

- A lite execplan is incomplete without generated skills under `execplan/skills/`.
- Always generate one shared guidance skill. It states common read order, placeholder replacement, direct SQLite usage, Houmao envelope metadata boundaries, and bounded-turn behavior.
- For every required `Loop-Template-Type`, generate at least one receiver skill whose trigger names that exact type, for example `Loop-Template-Type: task-request`.
- Generated receiver skills read Houmao mail envelope facts from mailbox metadata and read loop-local type facts from the body prologue.
- Generated sender skills require agents to check outbound bodies for unresolved `<placeholder` tokens before sending. If any remain, fill them or abort the send.
- Generate role, event, tick, and operator skills only when the loop process requires them.

## Direct SQLite State

- Use `execplan/specs/state/schema.sql` as the SQLite schema authority.
- Use `execplan/specs/state/README.md` as the direct-use contract for initialization, reads, writes, validation, and recovery.
- Store runtime databases under `runs/<run-id>/state.sqlite3` unless `execplan/manifest.md` records an explicit equivalent location.
- Generated skills manipulate SQLite directly according to the state README.
- Use short transactions, preferably `BEGIN IMMEDIATE` for writer sections that must be serialized.
- Record compact facts and refs: run id, participant id, work item id, owner, status, mail ref, thread ref, artifact path, decision id, timestamp, and event type.
- Do not store full mail bodies, rendered Markdown, long rationale, or detailed analysis in SQLite unless the generated loop explicitly defines a compact extraction field.
- Include audit or event rows when a state mutation affects dispatch, ownership, completion, recovery, or stop behavior.

## Validation

For `validate`, check:

- required root spine: `intention/`, `execplan/`, and `runs/`;
- required Markdown files for the generated package;
- at least one template in `execplan/specs/templates/`;
- each template starts with `Loop-Template-Type` and `Loop-Template-Version`;
- template types are unique unless the generated communication spec explicitly defines aliases;
- generated shared guidance skill exists;
- each required template type has at least one generated receiver skill naming it;
- no `execplan/harness/` or `execplan/docs/` directory exists;
- generated outbound templates and sender instructions do not contain unresolved `<placeholder` tokens where a concrete send is about to happen;
- `execplan/specs/state/schema.sql` parses with SQLite when durable state is required;
- required generated skills route platform mechanics to maintained Houmao skills.

Lite validation does not require pro-only schemas, TOML contracts, renderers, harness command registries, or harness scripts.

## Platform Boundaries

- Route ordinary mailbox sends, replies, reads, and archive behavior through `houmao-agent-email-comms` or supported mailbox CLI surfaces.
- Route notifier and gateway lifecycle work through `houmao-agent-gateway`.
- Route prompt, interrupt, and managed-agent control messages through `houmao-agent-messaging`.
- Route participant definition and profile preparation through `houmao-agent-definition`.
- Route workspace planning, creation, validation, or summaries through `houmao-utils-workspace-mgr` when the generated lite process needs explicit workspace setup or readiness evidence.
- Route live launch, join, stop, and relaunch actions through `houmao-agent-instance`.
- Route liveness, mailbox posture, logs, and runtime inspection through `houmao-agent-inspect`.
- Do not duplicate maintained Houmao platform-operation contracts inside lite specs or generated skills.

## Bounded Turns

- Model event and tick work as prompt-triggered bounded turns.
- Do not tell agents to sleep, poll, tail logs, or wait in-chat for future work.
- After one recognized mail event or tick action, complete required mail, state, and artifact updates, then end the turn.
- If the next action depends on future mail or external completion, record the waiting state in SQLite and stop.
