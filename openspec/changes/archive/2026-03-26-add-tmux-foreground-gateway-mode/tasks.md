## 1. CLI and gateway model plumbing

- [x] 1.1 Add a foreground attach option to `houmao-mgr agents gateway attach` and thread the requested execution-mode preference into managed runtime gateway attach.
- [x] 1.2 Extend gateway desired-config and live status/current-instance models to carry execution mode and foreground tmux window metadata.
- [x] 1.3 Update CLI attach/status payload rendering and help text so operators can see the foreground gateway execution mode and actual tmux window index.

## 2. Runtime foreground attach behavior

- [x] 2.1 Generalize the existing `tmux_auxiliary_window` gateway path so runtime-owned tmux-backed managed sessions can use it when foreground mode is requested.
- [x] 2.2 Persist and validate the authoritative tmux window/pane handle for same-session foreground gateways, including the invariant that the gateway window index must not be `0`.
- [x] 2.3 Ensure detach, restart, and crash cleanup use the authoritative auxiliary tmux surface for foreground gateways and continue teeing console output into durable gateway logs.

## 3. Validation and operator coverage

- [x] 3.1 Add focused tests for foreground attach on runtime-owned tmux-backed sessions, including attach-later, status metadata, and tmux window index `>=1`.
- [x] 3.2 Add regression tests for detach and stale-instance cleanup of same-session foreground gateways so window `0` is never targeted.
- [x] 3.3 Update any affected docs or workflow notes covering `houmao-mgr agents gateway attach/status` so foreground mode and gateway tmux-window discovery are documented.
