# Launch Agent Instance

Use this action only when the user wants to create one new managed-agent instance from a predefined source. This remains the canonical general lifecycle launch action even though `houmao-manage-specialist` may also front specialist-scoped launch requests.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine which launch lane the request actually needs:
   - direct managed launch from a predefined role or preset
   - explicit launch-profile-backed managed launch
   - specialist-backed managed launch from an existing easy specialist
3. Recover the required launch inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the source lane or required target inputs are still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the intended lane and exactly which required fields are still missing.
5. If the request depends on direct mailbox flags such as `--mail-transport`, `--mail-root`, or `--mail-account-dir`, stop and explain that manual mailbox-enabled launch is outside this skill's scope.
6. Run the correct launch command.
7. Report the managed-agent identity and launch result returned by the command.

## Command Selection

### Direct Managed Launch From Role Or Preset

Use this lane when the user wants to launch from a predefined role or preset through the canonical managed-agent lifecycle surface.

Use:

```text
<resolved houmao-mgr launcher> agents launch --agents <selector> --provider <provider> ...
```

Required inputs:

- `--agents`
- `--provider`

Common optional inputs:

- `--agent-name`
- `--agent-id`
- `--auth`
- `--session-name`
- `--headless`
- `--workdir`

Behavior note:

- `--workdir` changes only the launched agent runtime cwd.
- When the selected role or preset resolves from a Houmao project source, source-project overlay resolution stays pinned to that source instead of following `--workdir`.

### Explicit Launch-Profile-Backed Managed Launch

Use this lane when the user wants to launch through an existing explicit project launch profile.

Use:

```text
<resolved houmao-mgr launcher> agents launch --launch-profile <profile> ...
```

Required inputs:

- `--launch-profile`

Common optional inputs:

- `--agent-name`
- `--agent-id`
- `--auth`
- `--session-name`
- `--headless`
- `--workdir`
- `--provider` only when it matches the provider resolved from the stored launch profile

Behavior note:

- `--launch-profile` and `--agents` are mutually exclusive.
- The stored launch profile resolves the source recipe and contributes birth-time defaults before direct CLI overrides.
- Stored launch-profile defaults may already include gateway posture, prompt overlay, durable env records, and declared mailbox configuration.
- Direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` apply to one launch only and do not rewrite the stored launch profile.
- After launch, follow-up prompting or outgoing mailbox work should go through `houmao-agent-messaging`, which will discover any live gateway and prefer it when available.

### Specialist-Backed Managed Launch

Use this lane when the user wants to launch from an existing easy specialist.

Use:

```text
<resolved houmao-mgr launcher> project easy instance launch --specialist <specialist> --name <instance> ...
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

Behavior note:

- `--workdir` changes only the launched agent runtime cwd.
- The selected easy-project overlay and specialist source stay authoritative even when `--workdir` points outside that project.

If the selected specialist is known to use Gemini, the launch must be headless.

## Guardrails

- Do not guess whether the source should be `agents launch --agents`, `agents launch --launch-profile`, or `project easy instance launch`.
- Do not invent role selectors, launch profile names, specialist names, provider ids, or instance names.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through `agents launch`.
- Do not route explicit launch-profile-backed launch through `project easy instance launch`.
- Do not route role/preset launch through `project easy instance launch`.
- Do not describe `--workdir` as changing the source project, preset owner, selected overlay, runtime root, jobs root, or mailbox root.
- Do not include direct mailbox launch flags in this skill; manual mailbox-enabled launch is out of scope here.
- Do not reject the launch-profile lane just because the stored profile carries mailbox or gateway defaults.
- Do not treat prompt submission or gateway attach as part of launch completion for this skill.
