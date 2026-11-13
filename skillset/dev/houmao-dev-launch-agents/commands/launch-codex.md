# Launch Codex

## Workflow

1. **Resolve raw TUI inputs** from [../references/common-launch.md](../references/common-launch.md), including any exact workdir/session and permission posture.
2. **Resolve the selected credential route** through [../references/credential-resolution.md](../references/credential-resolution.md). Use `configure-fixtures` for missing local inputs.
3. **Resolve `codex` and its version**, preserving inherited proxy settings without exposing their values.
4. **Prepare `--client codex --surface raw --mode tui`** with the selected API case or imported native bundle.
5. **Launch through the common helper or exact-workdir adapter** and verify the Codex process, actual workdir, and visible TUI.
6. **Return safe launch evidence**, the verified session/pane, attach command, and owner-specific cleanup command.

If the request needs additional Codex arguments, use the native planning tool to check the selected executable's supported options, then apply only explicitly selected arguments through the common adapter without changing credential routing or mode.

## Provider Rules

API cases use the prepared Responses provider, explicit model, and private key projection. A DeepSeek API launch does not require `codex login status` or a saved `auth.json`. Native login instead uses an explicitly imported bundle, with no API-case env injection. Never run login/logout or fall back to personal home/profile settings.

The helper builds unattended TUI arguments with `--dangerously-bypass-approvals-and-sandbox`. Explicit `as_is` uses the common adapter to remove that flag. Respect the actual working directory; avoid adding a conflicting `-C`. User-selected resume, profile, search, image, or directory options require validation against the prepared routing and requested test.

Keep `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase equivalents when inherited. Record only variable names; do not invent a proxy or print credential-bearing URLs. Record explicit context/reasoning settings from the selected configuration rather than historical model defaults.

## Success Gate

Require a live Codex process and a visible Codex TUI in the captured pane, with no unattended approval, authentication, migration, or shell failure. Preserve failed-start diagnostics privately. Startup alone does not qualify a model response or token usage.
