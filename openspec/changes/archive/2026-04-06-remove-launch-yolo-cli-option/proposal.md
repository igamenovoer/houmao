## Why

Houmao currently exposes a launch-time `--yolo` flag on managed-agent launch surfaces even though provider startup autonomy is already modeled through `launch.prompt_mode`. That extra Houmao-owned trust prompt creates a second control plane, makes `project easy instance launch` fail unless the caller remembers a redundant flag, and blurs the contract between `unattended` and `as_is`.

## What Changes

- **BREAKING** Remove the user-facing `--yolo` option from `houmao-mgr agents launch`.
- **BREAKING** Remove the user-facing `--yolo` option from `houmao-mgr project easy instance launch`.
- Remove Houmao's own pre-launch workspace trust confirmation from managed local launch paths.
- Clarify that launch-time provider autonomy is owned by the resolved prompt mode:
- `unattended` may apply maintained no-prompt or full-autonomy provider posture when the launch-policy strategy owns that surface.
- `as_is` does not inject provider-owned YOLO, approval, sandbox, or equivalent no-prompt launch posture and leaves that control to the operator or provider defaults.
- Update docs, skills, demos, and tests that currently instruct users or scripts to pass `--yolo` on Houmao launch commands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-launch`: remove the public `--yolo` launch option and the Houmao-managed workspace trust confirmation, while keeping launch behavior aligned with preserved `launch.prompt_mode`.
- `houmao-mgr-project-easy-cli`: clarify that `project easy instance launch` does not expose a separate launch-time trust override and instead delegates provider startup posture to the stored specialist prompt mode.

## Impact

- Affected code:
- `src/houmao/srv_ctrl/commands/agents/core.py`
- `src/houmao/srv_ctrl/commands/project.py`
- Affected docs and guidance:
- `docs/getting-started/quickstart.md`
- `docs/getting-started/easy-specialists.md`
- `docs/reference/mailbox/quickstart.md`
- `docs/reference/claude-vendor-login-files.md`
- `src/houmao/agents/assets/system_skills/houmao-manage-agent-instance/actions/launch.md`
- Affected validation:
- unit and integration launch CLI tests
- demo and manual smoke flows that currently append `--yolo`
