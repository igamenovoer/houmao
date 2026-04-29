## Context

Houmao creates tmux sessions for managed-agent launches and compatibility runtime surfaces. The current launch path relies on whatever tmux and process environment the caller already has. That preserves user configuration, but it also means a caller environment such as `NO_COLOR=1` or missing `COLORTERM` can make Rich and provider TUIs render with reduced or disabled color inside a Houmao-owned tmux session. Mouse support for scrolling is likewise dependent on the user's base tmux configuration.

The desired behavior is a small, predictable overlay: Houmao-created tmux sessions should have rich color and mouse support by default, while unrelated `~/.tmux.conf` settings continue to apply. Operators must be able to disable the overlay entirely with `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`.

## Goals / Non-Goals

**Goals:**

- Enable mouse mode for Houmao-launched tmux sessions by default.
- Enable rich terminal color for provider TUIs and Python Rich output inside Houmao-launched tmux sessions.
- Overlay only the Houmao-owned settings and environment variables needed for this behavior.
- Keep all unrelated user tmux configuration and launch environment values intact.
- Provide a single opt-out switch: `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`.
- Cover both the primary managed-agent tmux runtime and maintained compatibility launch surfaces that still create Houmao-owned tmux sessions.

**Non-Goals:**

- Replace or rewrite the user's `~/.tmux.conf`.
- Add a public CLI flag for this behavior.
- Guarantee rich color for terminals or tmux versions that do not support the required color capabilities.
- Preserve deprecated `houmao-cao-server` behavior beyond maintained compatibility paths still exercised by the repository.

## Decisions

1. Add a shared injection policy helper.

   The runtime should centralize the opt-out check and the color environment overlay rather than scattering ad hoc `os.environ` checks through launch code. The helper should treat injection as enabled unless `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is exactly `0` after trimming whitespace. This keeps the default convenient and makes disablement explicit.

   Alternative considered: expose a launch option. That adds CLI/API surface for behavior intended to be a default runtime quality improvement, and the environment variable already supports scripts and tests.

2. Apply tmux options after session creation.

   Houmao should let tmux load the user's normal configuration first, create the session normally, then apply the Houmao overlay to the created session/server as required by tmux. The overlay should set only the chosen values, such as mouse mode, default terminal identity, and true-color capability hints. It should not clear unrelated options or rewrite config files.

   Alternative considered: start tmux with a generated config file. That is more invasive and risks bypassing user configuration rather than overlaying it.

3. Normalize terminal color environment for launched panes.

   Tmux options alone do not repair process-level color suppression. When injection is enabled, Houmao should publish a launch environment that sets `TERM=tmux-256color`, sets `COLORTERM=truecolor`, and removes `NO_COLOR` from the managed tmux session environment. Other environment values should remain inherited and overlaid as they are today.

   Alternative considered: only set tmux `default-terminal`. That leaves Rich and similar libraries free to disable or downgrade color based on inherited environment.

4. Fail clearly if injection cannot be applied.

   If tmux session creation succeeds but the enabled injection fails, the launch should report a Houmao-specific error that names the opt-out escape hatch. The implementation should clean up the newly-created session where practical so a failed overlay does not leave an unmanaged live session behind.

   Alternative considered: silently continue without injection. That would make launches appear successful while preserving the exact degraded color/mouse behavior this change is meant to fix.

## Risks / Trade-offs

- Tmux option scope varies by tmux version and option type -> The implementation should use the narrowest supported scope and tests should assert that unrelated options and environment variables are not modified by Houmao code.
- Some terminals may still not support true color -> Houmao can set correct tmux and environment hints, but unsupported terminal emulators may still degrade output.
- Existing automation may rely on inherited `NO_COLOR=1` inside managed sessions -> The explicit opt-out variable disables Houmao's color environment normalization for those workflows.
- Injection failure can turn a previously degraded-but-running launch into a failed launch -> The error should explain `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` as the immediate workaround.
