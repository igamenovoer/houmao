## Why

Houmao-launched tmux sessions currently inherit caller terminal settings that can disable rich terminal color, and they do not enable mouse interaction for scrollback by default. Operators expect managed tmux sessions to have usable color and mouse behavior without requiring every workstation `~/.tmux.conf` to carry Houmao-specific settings.

## What Changes

- Add Houmao-owned tmux session configuration injection for launched tmux sessions.
- Enable mouse mode and rich color support for Houmao-created sessions while leaving unrelated user tmux configuration untouched.
- Overlay only the specific Houmao-managed tmux settings and terminal environment values needed for color and mouse behavior.
- Allow operators to disable this injection with `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`.
- Keep compatibility with existing user `~/.tmux.conf` values for all settings Houmao does not explicitly manage.

## Capabilities

### New Capabilities

### Modified Capabilities
- `tmux-integration-runtime`: Houmao-created tmux sessions gain scoped configuration injection for mouse mode and rich color behavior with an environment-variable opt-out.

## Impact

- Affects tmux session creation paths for managed-agent launches and other Houmao-owned tmux session startup surfaces.
- Affects terminal environment published into launched tmux sessions, including color-related values.
- Adds tests for default injection, opt-out behavior, and preservation of unrelated user tmux configuration.
