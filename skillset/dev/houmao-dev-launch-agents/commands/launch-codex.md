# Launch Codex

## Workflow

1. **Resolve common inputs** from [../references/common-launch.md](../references/common-launch.md).
2. **Resolve `command -v codex` and native auto credential posture** from [../references/credential-resolution.md](../references/credential-resolution.md).
3. **Inspect the proxy environment** and preserve its existing proxy settings for the Codex child process without exposing their values.
4. **Build the Codex TUI command.** Use unattended bypass by default or omit it for explicit `as_is`.
5. **Launch in a fresh tmux session and verify** process identity plus visible startup surface.
6. **Write non-secret launch metadata and return the attach command.**

If the request needs a custom Codex model, profile, resume target, or writable directory set, use the native planning tool to add only user-supplied provider arguments while preserving auto credential, environment-derived proxy, tmux, and secret-hygiene gates.

## Guidance

Read this section as the Codex-specific execution procedure. Follow it after common inputs are fixed.

1. **Resolve the executable.** Capture the path from `command -v codex` and run `codex --version`.
2. **Validate auto credentials.** Run `codex login status` without printing native auth files. Block when neither login status nor a recognized inherited credential lane is usable.
3. **Resolve proxy posture.** Inspect `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and their lowercase equivalents in the inherited environment. Preserve the variables that are already set for the Codex child process. Do not invent, override, or hard-code a proxy server.
4. **Build arguments.** Use `codex --dangerously-bypass-approvals-and-sandbox -C <workdir>` for unattended launch. Use `codex -C <workdir>` for explicit `as_is`. Append only user-provided model, profile, search, image, resume, or directory arguments.
5. **Launch and verify.** Apply the common tmux workflow, then confirm a Codex process and Codex TUI surface remain live.

## Preferences

Read these preferences as defaults after the workflow's hard checks.

- Prefer `codex login status` as auto-credential proof (if an explicit inherited API-key lane is selected, record only the variable name).
- Prefer the proxy settings already present in the environment. Record only the variable names that Codex inherits, not their values.
- Prefer unattended launch for automated testing (if the user asks to observe approval behavior, use `as_is`).

## Constraints

Read these constraints as hard validity boundaries.

- The workflow must not run `codex login` or `codex logout`.
- The command must not print or embed `auth.json`, API keys, or access tokens.
- Unattended launch must use the current Codex bypass flag, not a stale approval-mode approximation.
- Launch success must include a live Codex child process and visible TUI evidence.

## Quality Gates

Read these gates after the session starts.

### Metrics

- Auto-credential confidence: strength of non-secret provider status evidence; stronger is better.
- Startup latency: time until a stable Codex surface appears; lower is better.
- Confirmation prompts: approval or migration prompts during unattended startup; lower is better and zero is expected.

### Checks

- Executable: the recorded path matches `command -v codex`.
- Credential: auto-credential proof succeeded without auth mutation.
- Proxy: inherited proxy variables were inspected and their names were recorded without values.
- Runtime: the tmux pane contains a live Codex process.
- Surface: visible output is a Codex TUI, not an authentication, migration, or shell error.
