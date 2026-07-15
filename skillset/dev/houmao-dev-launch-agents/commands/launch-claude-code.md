# Launch Claude Code

## Workflow

1. **Resolve common inputs** from [../references/common-launch.md](../references/common-launch.md).
2. **Evaluate the Claude resolver in strict order:** `claude-kimi`, trusted `.env` Kimi pair, `claude-yunwu`, other `claude-*` launchers, then native Claude auto credential.
3. **Build the selected launcher command.** Invoke wrappers as-is; use a restricted helper for `.env`; add the native unattended flag only to direct `claude` routes.
4. **Launch in a fresh tmux session and verify** both the wrapper/provider process chain and visible Claude Code surface.
5. **Write non-secret resolution and launch metadata.** Include tried strategies and rejection reasons without values.
6. **Return the attach command or final credential blocker.**

If the request supplies a model, session resume, allowed tools, additional directories, or explicit permission posture, use the native planning tool to add only those arguments after the ordered resolver selects launch authority.

## Guidance

Read this section as the Claude-specific execution procedure. Resolver order is authoritative.

1. **Try `claude-kimi`.** Run `command -v claude-kimi`; when usable, select it and stop resolution.
2. **Try trusted `.env`.** Inspect the bounded workdir/repository `.env` files as data for a complete recognized Kimi endpoint/key pair. When found, create a mode-`0700` run-local helper that maps the pair to `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY`, then executes `claude`.
3. **Try `claude-yunwu`.** Run `command -v claude-yunwu`; when usable, select it and stop resolution.
4. **Try other `claude-*` launchers.** Enumerate sorted candidates, run `command -v` for each, and select the first bounded probe that identifies a usable Claude launcher.
5. **Try native auto credential.** Resolve `command -v claude` and require `claude auth status --json` or a coherent recognized inherited credential lane.
6. **Build arguments.** Invoke selected wrappers without adding duplicate permission flags. For the `.env` helper or native `claude`, add `--dangerously-skip-permissions` in unattended mode and omit it for explicit `as_is`.
7. **Launch and verify.** Apply the common tmux workflow and confirm the selected wrapper leads to a live Claude Code process and surface.

## Ordered Resolver

| Priority | Strategy | Launcher | Credential Authority |
| ---: | --- | --- | --- |
| 1 | `claude-kimi` | Resolved wrapper | Wrapper-owned environment/state |
| 2 | Trusted `.env` Kimi pair | Run-local helper → `claude` | Selected Kimi endpoint/key names |
| 3 | `claude-yunwu` | Resolved wrapper | Wrapper-owned environment/state |
| 4 | Other `claude-*` | First sorted usable wrapper | Wrapper-owned environment/state |
| 5 | Native auto credential | `claude` | Claude inherited environment/native home |

## Preferences

Read these preferences only after applying strict precedence.

- Prefer executing a wrapper over extracting its environment.
- Prefer the workdir `.env` over the repository-root `.env` when both are complete.
- Prefer `claude auth status --json` for final native-auto proof.
- Prefer unattended direct launch for automated testing (if permission behavior is under observation, use explicit `as_is`).

## Constraints

Read these constraints as hard validity boundaries.

- The resolver must not skip or reorder a strategy.
- Wrapper secrets and `.env` values must not appear in output or tmux command text.
- `.env` must be parsed as data and must not execute shell expressions.
- Selected wrappers must be invoked as the launcher without blindly appending duplicate unattended flags.
- The workflow must not run Claude login, logout, or setup-token commands.
- Launch success must include a live Claude Code process and visible TUI evidence.

## Quality Gates

Read these gates after resolution and startup.

### Metrics

- Resolver completeness: proportion of higher-priority strategies conclusively checked before selection; more complete is better and 100% is required.
- Secret exposure count: selected secret values appearing in artifacts or output; lower is better and zero is required.
- Startup latency: time until a stable Claude Code surface appears; lower is better.

### Checks

- Precedence: every strategy before the selected one has explicit unavailable or unusable evidence.
- Launcher: the selected command path was resolved through `command -v` or is the recorded run-local helper.
- Credential: the selected strategy has non-mutating usability evidence.
- Runtime: the tmux process tree reaches Claude Code.
- Surface: visible output is Claude Code rather than onboarding, authentication, or shell failure.
