# Launch Kimi Code

## Workflow

1. **Resolve raw TUI inputs** from [../references/common-launch.md](../references/common-launch.md), including any exact workdir/session and permission posture.
2. **Resolve the selected credential route** through [../references/credential-resolution.md](../references/credential-resolution.md). Use `configure-fixtures` for missing local inputs.
3. **Resolve `kimi`, or `kimi-code` when `kimi` is absent**, and capture its version. Pass the resolved alternate path through `prepare --executable`.
4. **Prepare `--client kimi --surface raw --mode tui`** with the selected API case or imported native bundle.
5. **Launch through the common helper or exact-workdir adapter** and verify the Kimi process, actual workdir, and visible TUI.
6. **Return safe launch evidence**, the verified session/pane, attach command, and owner-specific cleanup command.

If the request needs additional Kimi arguments, use the native planning tool to check the selected executable's supported options, then apply only explicitly selected arguments through the common adapter without changing credential routing or mode.

## Provider Rules

API cases use a prepared Chat Completions model with an explicit context window. Set capabilities and any reasoning-content key only for the selected model. Do not infer image/thinking support from the client name or an old Qwen fixture. API launch needs no native Kimi login or provider-status command.

Native login uses supported credentials and matching config from the explicitly selected import, copied into the run-owned home. Do not run login/device authorization or mutate the source bundle.

Unattended TUI uses `--auto`, never `--yolo`. Explicit `as_is` uses the common adapter to remove `--auto`. Headless requests belong to `launch-fixture`; Kimi prompt mode omits `--auto` and uses `-p` plus stream JSON output. Do not add an unsupported `--print` option.

## Success Gate

Require a live Kimi process and a visible Kimi TUI in the captured pane, with no unattended authentication, permission, config, or shell failure. Preserve failed-start diagnostics privately. Startup alone does not qualify a model response or token usage.
