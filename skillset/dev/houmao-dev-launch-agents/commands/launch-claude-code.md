# Launch Claude Code

## Workflow

1. **Resolve raw TUI inputs** from [../references/common-launch.md](../references/common-launch.md), including any exact workdir/session and permission posture.
2. **Resolve the selected credential route** through [../references/credential-resolution.md](../references/credential-resolution.md). Use `configure-fixtures` for missing local inputs.
3. **Resolve `claude` and its version**, without searching personal wrappers or loading ambient `.env` files.
4. **Prepare `--client claude --surface raw --mode tui`** with the selected API case or imported native bundle.
5. **Launch through the common helper or exact-workdir adapter** and verify the Claude Code process, actual workdir, and visible TUI.
6. **Return safe launch evidence**, the verified session/pane, attach command, and owner-specific cleanup command.

If the request needs additional Claude arguments, use the native planning tool to check the selected executable's supported options, then apply only explicitly selected arguments through the common adapter without changing credential routing or mode.

## Provider Rules

API cases use the prepared Anthropic Messages endpoint, token, and model aliases. Claude expects the service's API root, without adding a trailing `/v1`. The fixture helper performs provider projection; do not remap dotenv values in a shell command. API launch does not require vendor OAuth or a successful native auth-status probe.

Native login uses the explicitly selected imported bundle and run-owned home. Do not run login, logout, or setup-token. Missing credentials stay blocked; the old `claude-kimi`, `claude-yunwu`, and sorted `claude-*` fallback chain is retired for fixture testing.

The helper builds unattended arguments with `--dangerously-skip-permissions`; explicit `as_is` uses the common adapter to remove it. Any selected resume, allowed-tools, or additional-directory arguments must preserve the prepared home/endpoint and selected posture.

## Success Gate

Require a live Claude Code process and a visible Claude Code TUI in the captured pane, with no unattended onboarding, authentication, permission, or shell failure. Preserve failed-start diagnostics privately. Startup alone does not qualify a model response or token usage.
