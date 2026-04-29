## 1. Shared Tmux Injection Helpers

- [x] 1.1 Add a shared helper that treats tmux configuration injection as enabled unless `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`.
- [x] 1.2 Add a shared helper that overlays the managed tmux color environment with `TERM=tmux-256color`, `COLORTERM=truecolor`, and no `NO_COLOR` when injection is enabled.
- [x] 1.3 Add a shared helper that applies the Houmao tmux overlay after session creation, including mouse mode and rich-color terminal capability settings.
- [x] 1.4 Make injection failure errors identify the tmux configuration injection step and mention `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` as the opt-out.

## 2. Runtime Integration

- [x] 2.1 Invoke the tmux overlay from maintained Houmao tmux session creation paths after successful `new-session`.
- [x] 2.2 Clean up a newly-created tmux session when enabled injection fails before the launch becomes active.
- [x] 2.3 Apply the color environment overlay before publishing managed tmux session environment values for launched provider processes.
- [x] 2.4 Preserve unrelated user tmux options and unrelated inherited environment variables.
- [x] 2.5 Ensure the compatibility tmux launch path used by maintained server/control code follows the same injection and opt-out policy.

## 3. Tests

- [x] 3.1 Add unit coverage that default tmux session creation applies mouse and rich-color injection commands.
- [x] 3.2 Add unit coverage that `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` skips tmux option injection and color environment normalization.
- [x] 3.3 Add unit coverage that inherited `NO_COLOR` is removed and `TERM`/`COLORTERM` are set when injection is enabled.
- [x] 3.4 Add unit coverage that unrelated environment values are preserved.
- [x] 3.5 Add unit coverage that injection failures surface opt-out guidance and clean up the created session where practical.

## 4. Verification

- [x] 4.1 Run focused tmux runtime and managed launch unit tests.
- [x] 4.2 Run `pixi run lint`.
- [x] 4.3 Run `pixi run typecheck`.
