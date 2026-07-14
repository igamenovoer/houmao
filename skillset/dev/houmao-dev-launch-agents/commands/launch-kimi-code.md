# Launch Kimi Code

## Workflow

1. **Resolve common inputs** from [../references/common-launch.md](../references/common-launch.md).
2. **Resolve `command -v kimi`, falling back to `command -v kimi-code`.**
3. **Validate native auto credential posture** from [../references/credential-resolution.md](../references/credential-resolution.md) without login or secret output.
4. **Build the Kimi TUI command.** Add `--auto` for unattended launch and no permission flag for explicit `as_is`.
5. **Launch in a fresh tmux session and verify** process identity plus visible startup surface.
6. **Write non-secret launch metadata and return the attach command.**

If the request supplies a model, resume session, skills directory, or additional workspace directory, use the native planning tool to add only those explicit Kimi arguments while preserving the credential, `--auto`, tmux, and verification contracts.

## Guidance

Read this section as the Kimi-specific execution procedure. Follow it after common inputs are fixed.

1. **Resolve the executable.** Prefer `command -v kimi`; use `command -v kimi-code` only when `kimi` is absent. Run the selected command's `--version` probe.
2. **Validate auto credentials.** Resolve `KIMI_CODE_HOME` or the default native home, validate `config.toml` with `kimi doctor config` when present, and use `kimi provider list --json` as non-secret provider evidence. Accept a coherent inherited env-model lane without printing values.
3. **Build arguments.** Use `<kimi-launcher> --auto` for unattended launch and the bare launcher for explicit `as_is`. Append only user-provided model, resume, skills, or additional-directory arguments.
4. **Launch and verify.** Apply the common tmux workflow, then confirm a Kimi process and Kimi TUI surface remain live.

## Preferences

Read these preferences as defaults after hard checks.

- Prefer `kimi` over `kimi-code` when both resolve.
- Prefer native config/provider status over reading credential JSON.
- Prefer `--auto` for unattended operation (do not substitute `--yolo`, which is a different permission contract).

## Constraints

Read these constraints as hard validity boundaries.

- The workflow must not run `kimi login`, device authorization, or credential mutation.
- Credential JSON and API-key environment values must not be printed.
- Unattended launch must use `--auto`, not `--yolo`.
- Launch success must include a live Kimi child process and visible TUI evidence.

## Quality Gates

Read these gates after the session starts.

### Metrics

- Provider evidence completeness: configured model/provider checks available without secret access; more complete is better.
- Startup latency: time until a stable Kimi surface appears; lower is better.
- Confirmation prompts: permission or login prompts during unattended startup; lower is better and zero is expected.

### Checks

- Executable: the recorded path came from the declared `kimi` then `kimi-code` order.
- Credential: auto-credential proof succeeded without login or secret disclosure.
- Permission posture: unattended launch includes `--auto` and excludes `--yolo`.
- Runtime: the tmux pane contains a live Kimi process.
- Surface: visible output is a Kimi TUI, not a config, authentication, or shell error.
