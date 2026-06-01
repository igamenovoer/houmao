# Prepare Agents

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Operator wants launchable Houmao easy profiles and prepared agent facts before workspace setup.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`

Use when present:
- generated profile definitions, prompt sources, notifier prompts, and memo seeds;
- generated workspace policy references that affect pending launch cwd or memo posture;
- current `validate-execplan` evidence.

## Actions

1. Read `execplan/manifest.toml` and generated agent bindings.
2. Resolve each participant's intended easy profile, definition source, generated skills, notifier prompt path, memo seed posture, launch interface mode (`tui` or `headless`), and pending launch cwd posture.
3. Register loop-generated or loop-private skills through maintained project-skill surfaces when project-local skill registration is needed.
4. Route persisted agent/profile preparation through `houmao-agent-definition`:
   - `create-agent-fast-forward`: default when a participant may need both specialist and easy profile preparation;
   - `profiles`: when the specialist already exists and only easy profile material changes;
   - `specialists`: when only specialist material changes and no profile preparation is needed;
   - `raw-profiles`: only when the execplan or operator explicitly requires raw profile control.
5. Treat `houmao-mgr project easy ...` as the underlying surface owned by `houmao-agent-definition`, not as loop-local preparation logic.
6. Attach generated skills, definitions, notifier prompt sources, memo seed posture, and pending cwd/memo mutation intent to the prepared profile material.
7. Rely on Houmao managed-agent creation to preinstall Houmao system skills into agents; do not enumerate or manually bind ordinary Houmao support skills, including maintained mail support skills such as `houmao-process-emails-via-gateway`, in generated profile guidance.
8. Resolve and record prepared agent facts:
   - concrete agent ids;
   - specialist names;
   - easy profile names, or raw launch profile names only when explicitly required;
   - stable workspace agent names;
   - selected tool and credential when reported by `houmao-agent-definition`;
   - launch interface mode, reporting whether the prepared profile is configured for TUI-backed or headless launch;
   - prompt or definition sources;
   - installed generated skills;
   - confirmation that Houmao system skills are preinstalled or will be preinstalled by managed-agent creation;
   - notifier prompt paths;
   - memo seed paths or pending memo posture;
   - launch cwd policy or pending launch cwd posture;
   - whether a matching live agent was observed without launching it.
9. Treat unknown, missing, or contradictory TUI/headless launch mode facts as preparation blockers unless the operator explicitly accepts a manual raw launch profile whose mode is documented outside the easy-profile facts.
10. Report prepared agent/easy-profile facts, installed generated skills, Houmao system-skill preinstall posture, notifier prompt posture, memo posture, pending workspace-dependent profile mutations, and blockers for `prepare-workspace`, `validate-loop`, or `launch-agents`.

## Report

Report:
- readiness result for agent preparation: ready, ready with warnings, or blocked;
- prepared agent/easy-profile facts checked;
- installed generated skills and Houmao system-skill preinstall posture;
- notifier prompt posture;
- memo posture;
- pending workspace-dependent profile mutations;
- blockers for `prepare-workspace`, `validate-loop`, or `launch-agents`;
- warnings that do not block the next stage.

End the report with one Markdown summary table that has one row for every required participant or prepared concrete agent:

| Agent | Participant | Launch mode | Credential | Skill groups | Workdir |
| --- | --- | --- | --- | --- | --- |
| `<agent-id or profile>` | `<participant or role>` | `tui` or `headless` | `<credential display name or unknown>` | `<generated/private skill group names>` | `<launch cwd or pending workspace policy>` |

Use `blocked` in the relevant cell when a required fact is missing or inconsistent, then list the blocking detail above the table.

## Constraints

- Do not perform workspace preparation here: do not call `prepare-workspace`, run `houmao-utils-workspace-mgr`, create worktrees, or create workspace scaffolding.
- Do not prepare mailbox, gateway, memory, inspection, harness state, run artifacts, or broad runtime readiness here; use `validate-loop` for pre-launch readiness.
- Do not launch live agents as normal preparation behavior; use `launch-agents`.
- Do not start loop work from this page; use `start`.
- Do not reimplement specialist creation, easy-profile mutation, raw-profile mutation, credential defaulting, or launcher selection; route to `houmao-agent-definition`.
- Do not install generated event or tick skills into the wrong participant profile.
- Do not invent profiles when the execplan or user did not provide enough information; prefer easy-profile creation/update before considering raw profile editing.
- Do not prepare agents to sleep, poll, tail logs, or wait in-chat for loop progress; mail notifier prompts and operator prompts are the wakeup mechanism.
