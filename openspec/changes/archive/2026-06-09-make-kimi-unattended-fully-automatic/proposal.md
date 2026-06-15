## Why

Kimi Code local-interactive launches can currently be configured as `as_is`, while maintained unattended behavior is declared only for the `kimi_headless` backend. Operators expect `launch.prompt_mode: unattended` to mean no permission dialogs, no user questions, and no manual intervention, including for visible Kimi TUI agents.

## What Changes

- Extend maintained Kimi unattended launch policy so Kimi Code `raw_launch` / `local_interactive` startup is covered in addition to `kimi_headless`.
- Make Kimi unattended startup force the provider into Kimi `auto` permission mode, which auto-approves tools and disables user questions, while preserving Kimi's native hard-deny behavior for explicit deny rules or hard policy blocks.
- Ensure Kimi TUI relaunch and resumed-session paths do not regress into manual approval prompts, without combining Kimi's forbidden `--auto` flag with `--continue` or `--session`.
- Keep `as_is` Kimi TUI posture unchanged: no automatic permission override is applied when the operator explicitly opts out of unattended mode.
- Update docs and tests so `unattended` is the supported Houmao-facing control and `--yolo` is not reintroduced as a user-facing launch option.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-launch-policy-registry`: Kimi unattended strategy coverage expands from headless-only to include the raw launch surface used by local-interactive TUI startup.
- `brain-launch-runtime`: Runtime startup and relaunch behavior must keep Kimi unattended local-interactive sessions in automatic no-question mode.
- `houmao-mgr-project-easy-cli`: Project-backed Kimi launches that resolve to unattended posture must delegate to the maintained Kimi no-prompt policy, while `as_is` remains manual.
- `docs-launch-policy-reference`: Launch-policy docs must describe Kimi's maintained unattended ownership for both headless prompt mode and TUI auto permission mode.
- `docs-run-phase-reference`: Run-phase docs must describe the Kimi TUI unattended behavior and resumed-startup constraints.
- `docs-cli-reference`: CLI docs must point operators at `launch.prompt_mode: unattended` for Kimi automation without documenting `--yolo` as a supported launch control.

## Impact

Affected areas include the Kimi launch-policy registry, provider hooks, launch-policy TOML mutation support, local-interactive Kimi startup/relaunch handling, project specialist/profile launch posture flows, Kimi writer-team demo defaults where applicable, launch-policy tests, local-interactive runtime tests, project launch tests, and docs under `docs/reference`.
