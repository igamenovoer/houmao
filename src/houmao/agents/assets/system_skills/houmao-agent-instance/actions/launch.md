# Launch Agent Instance

Use this action only when the user wants to create one new managed-agent instance from a project-scoped source.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine which launch lane the request actually needs:
   - project-profile-backed managed launch
   - specialist-backed managed launch from an existing project specialist
3. Recover the required launch inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the source lane or required target inputs are still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the intended lane and exactly which required fields are still missing.
5. If the request depends on direct mailbox flags such as `--mail-transport`, `--mail-root`, or `--mail-account-dir`, stop and explain that manual mailbox-enabled launch is outside this skill's scope.
6. Build the correct direct launch command, omitting `--headless` when launch posture is unspecified and TUI/local-interactive launch is supported.
7. Run the direct command only after required inputs are explicit and conflicts are resolved.
8. Report the managed-agent identity and launch result returned by the command.

## Default Launch Posture

When the user does not specify headless or TUI posture, prefer TUI/local-interactive launch when the selected tool or launch lane supports it.

Only add a one-shot `--headless` flag when the user explicitly asks for headless execution or the selected tool/lane is known to require headless. Do not infer headless from unattended prompt mode, gateway attachment, mailbox defaults, output rendering, or automation-oriented wording.

For Kimi automation, rely on stored `launch.prompt_mode: unattended` or project/profile prompt-mode controls. Do not add raw Kimi `--auto` or `--yolo` launch arguments, and do not force `--headless` just because Kimi should run without approval prompts.

## Command Selection

### Project-Profile-Backed Managed Launch

Use this lane when the user wants to launch through an existing project profile.

Run the direct project-profile launch command:

```bash
<chosen houmao-mgr launcher> project agents launch --profile <profile> [--name <agent-name>]
```

Required inputs:

- `--profile`

Common optional inputs:

- `--name`
- `--auth`
- `--session-name`
- `--headless`
- `--workdir`
- `--managed-header-section SECTION=enabled|disabled`
- `--provider` only when it matches the provider resolved from the stored launch profile

Behavior note:

- `--profile` and `--specialist` are mutually exclusive.
- The stored project profile resolves the source specialist and contributes birth-time defaults before direct CLI overrides.
- Stored project-profile defaults may already include gateway posture, prompt overlay, gateway mail-notifier appendix text, durable env records, and declared mailbox configuration.
- Preserve explicit stored launch-profile posture, but do not add a one-shot `--headless` override unless the user explicitly asks for it or the selected tool/lane requires it.
- Profile-owned mail-notifier appendix text is seeded into runtime gateway notifier state during launch, but it does not enable notifier polling by itself.
- Do not add one-shot background gateway overrides unless the user explicitly asks for background gateway execution. Stored launch-profile gateway posture owns launch-time defaults when present.
- `--managed-header-section` is a one-shot section override and does not rewrite stored launch-profile section policy.
- Direct CLI overrides such as `--name`, `--auth`, and `--workdir` apply to one launch only and do not rewrite the stored project profile.
- After launch, follow-up prompting or outgoing mailbox work should go through `houmao-agent-messaging`, which will discover any live gateway and prefer it when available.
- After launch, read-only state, screen, mailbox-posture, log, or artifact inspection should go through `houmao-agent-inspect`.

### Specialist-Backed Managed Launch

Use this lane when the user wants to launch from an existing specialist.

Run the direct specialist-backed launch command:

```bash
<chosen houmao-mgr launcher> project agents launch --specialist <specialist> --name <agent-name>
```

Required inputs:

- `--specialist`
- `--name`

Common optional inputs:

- `--auth`
- `--session-name`
- `--headless`
- `--workdir`
- `--env-set NAME=value|NAME`
- `--managed-header-section SECTION=enabled|disabled`

Behavior note:

- `--workdir` changes only the launched agent runtime cwd.
- When launch posture is unspecified and the selected specialist's tool supports TUI/local-interactive launch, omit `--headless`.
- The selected easy-project overlay and specialist source stay authoritative even when `--workdir` points outside that project.
- `--managed-header-section` is a one-shot section override for the launched instance.
- Do not add background gateway flags unless the user explicitly asks for background gateway execution; defer detailed specialist-backed launch-time gateway behavior to `houmao-agent-definition`.

If the selected specialist is known to use Gemini, the launch must be headless. Treat that as a selected-tool requirement, not as the default for omitted launch posture.

If the selected specialist is known to use Kimi, unattended prompt mode is compatible with omitted `--headless`; Houmao will delegate to the maintained Kimi TUI no-question posture.

## Guardrails

- Do not guess whether the source should be `project agents launch --specialist` or `project agents launch --profile`.
- Do not invent role selectors, launch profile names, specialist names, provider ids, or instance names.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through retired root-level managed-agent launch paths.
- Do not route project-profile-backed launch through retired root-level managed-agent launch paths.
- Do not route raw role/preset launch through the public `agents` family; use project sources or internal native-agent plumbing when explicitly required.
- Do not describe `--workdir` as changing the source project, preset owner, selected overlay, runtime root, jobs root, or mailbox root.
- Do not include direct mailbox launch flags in this skill; manual mailbox-enabled launch is out of scope here.
- Do not reject the launch-profile lane just because the stored profile carries mailbox or gateway defaults.
- Do not treat prompt submission or gateway attach as part of launch completion for this skill.
- Do not add `--headless` by default for TUI-capable tools or because prompt mode is unattended.
- Do not add raw Kimi `--auto` or `--yolo` launch flags to achieve managed unattended mode.
- Do not invent alternate launch command shapes; use the direct scoped commands shown in this action and maintained project/profile guidance.
- Do not add a background gateway override unless the user explicitly asks for detached background gateway execution.
