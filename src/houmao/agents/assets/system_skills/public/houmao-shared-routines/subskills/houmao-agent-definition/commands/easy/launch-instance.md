---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Launch Project Managed Agent

Use this subskill only when the user wants to launch one project managed agent from an existing specialist or project profile.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
- Use this subskill for `project agents launch`, not for retired root-level managed-agent launch paths.

## Workflow

1. Determine launch source: `--specialist` or `--profile`.
2. Recover explicit launch inputs from the prompt and recent stated context.
3. For specialist launch, require specialist name and managed-agent name.
4. For profile launch, require profile name.
5. If profile launch lacks a managed-agent name, inspect the profile with `project profile get --name <profile>` to see whether it stores one.
6. Build the direct `project agents launch` command with only explicit source, identity, and one-shot override flags.
7. If required input is missing or explicit inputs conflict, recover that input before launching.
8. Run the direct command, omitting `--headless` when launch posture is unspecified and TUI/local-interactive launch is supported.
9. Report the launched instance identity and command output.
10. Tell the user that broader live-agent management now belongs to `houmao-shared-routines->houmao-agent-instance`.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shapes

```bash
<chosen houmao-mgr launcher> project agents launch --profile <profile> [--name <agent-name>]
<chosen houmao-mgr launcher> project agents launch --specialist <specialist> --name <agent-name>
```

Add optional flags only when the user supplied them explicitly or the selected tool/lane requires them.

## Common Options

- `--auth`
- `--session-name`
- `--headless`
- `--no-headless`
- `--no-gateway`
- `--gateway-port`
- `--gateway-background` only when the user explicitly requests detached background gateway execution
- gateway TUI timing overrides only when explicitly requested
- `--workdir`
- `--env-set NAME=value|NAME`
- `--mail-transport filesystem|email`
- `--mail-root`
- `--mail-account-dir`
- repeatable `--managed-header-section SECTION=enabled|disabled`

## Notes

- `--specialist` and `--profile` are mutually exclusive.
- Profile-backed launch applies stored profile defaults before direct CLI overrides.
- When the user does not specify headless or TUI posture, prefer TUI/local-interactive launch when the selected tool supports it.
- Add `--headless` only when the user explicitly asks for headless execution, when an existing selected profile stores headless posture, or when the selected tool/lane requires headless.
- Kimi supports TUI/local-interactive launch here when headless is omitted.
- `--prompt-mode unattended` and other stored automation defaults do not imply headless launch. For Kimi, unattended prompt mode is the supported managed no-question control; do not add raw `--auto` or `--yolo` launch flags.
- Profile-backed launch applies any stored memo seed before prompt composition and provider startup.
- Direct specialist-backed launch does not apply a stored memo seed because no reusable profile was selected.
- Launch-time gateway auto-attach is enabled by default unless `--no-gateway` or stored profile posture disables it.
- Default launch-time gateway auto-attach uses foreground same-session auxiliary-window execution when supported.
- A headless managed-agent launch does not by itself justify `--gateway-background`.
- Unlike `project profile create`, launch does not accept declarative mailbox fields such as `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url`.
- For launch-time filesystem mailbox support, use `--mail-transport filesystem`, `--mail-root <shared-root>`, and optional `--mail-account-dir <private-path>`.
- When launch derives the ordinary filesystem mailbox identity, `--name` seeds the managed-agent mailbox address and principal id.
- `--mail-account-dir` is a private filesystem mailbox directory outside the shared root that launch symlinks into the shared root.
- If the same ordinary address under the same root was preregistered manually already, launch-time safe registration can fail. For the common ordinary case, let launch own that per-agent address.

## Guardrails

- Do not guess whether the source is a specialist or profile.
- Do not guess specialist name, profile name, or instance name.
- Do not route specialist-backed launch through retired root-level managed-agent launch paths.
- Do not route profile-backed launch through retired root-level managed-agent launch paths.
- Do not add `--headless` by default for TUI-capable tools.
- Do not add raw Kimi `--auto` or `--yolo` launch flags to achieve managed unattended mode.
- Do not invent optional launch flags that the user did not request.
- Do not add `--gateway-background` unless the user explicitly requested background or detached gateway execution.
- Do not teach preregistering the same-root ordinary per-agent mailbox address as the default precursor to mailbox-enabled project launch.
- Do not describe `--workdir` as changing the source project, specialist source, selected overlay, runtime root, jobs root, or mailbox root.
