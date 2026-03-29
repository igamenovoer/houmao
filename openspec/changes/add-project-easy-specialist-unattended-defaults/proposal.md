## Why

`houmao-mgr project easy` is supposed to be the higher-level, low-friction operator path, but easy-created Claude specialists currently launch with interactive startup prompts because the generated preset omits `launch.prompt_mode`. That is the wrong default now that Houmao already supports unattended TUI startup through the versioned launch-policy path.

The startup posture belongs to the reusable specialist definition, not to one concrete instance launch. Storing that posture on the specialist keeps launch behavior honest across first launch, relaunch, and inspection, while still allowing an explicit opt-out when an operator wants normal interactive startup.

## What Changes

- Make `houmao-mgr project easy specialist create` persist unattended startup posture by default for supported easy-launch tools instead of omitting launch prompt mode.
- Add `--no-unattended` to `houmao-mgr project easy specialist create` as the explicit opt-out for operators who want interactive startup prompts.
- Keep the default/opt-out as specialist configuration by writing canonical `launch.prompt_mode` into the generated preset and catalog-backed specialist metadata.
- Keep `houmao-mgr project easy instance launch` as a thin runtime wrapper that honors the stored specialist launch posture instead of injecting its own prompt-mode policy.
- Fail closed through existing launch-policy resolution when a stored unattended specialist posture is not supported for the resolved tool/backend/version pair.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: easy specialist creation persists unattended startup posture by default for supported tools, exposes `--no-unattended` as the opt-out, and easy instance launch honors the stored specialist launch payload without additional prompt-mode injection.

## Impact

- Affected code:
  `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/project/catalog.py`, and any projection/rendering helpers that surface specialist launch payload.
- Affected tests:
  project easy CLI tests for specialist creation, specialist get/list projection, and instance launch/build request forwarding.
- Affected operator surfaces:
  `houmao-mgr project easy specialist create`, generated `.houmao/agents/roles/<role>/presets/<tool>/default.yaml`, and `houmao-mgr project easy instance launch`.
- Affected persisted/runtime-visible state:
  specialist catalog `launch_payload`, rendered preset `launch.prompt_mode`, built brain manifest `launch_policy.operator_prompt_mode`, and session launch-policy provenance on unattended launches.
- Dependencies and systems:
  project-easy catalog/projection flow, launch-policy resolution, and existing unattended TUI support for maintained tool/backend pairs.
