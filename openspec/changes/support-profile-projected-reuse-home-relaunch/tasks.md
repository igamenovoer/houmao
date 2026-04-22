## 1. CLI Reuse-Home Contract

- [x] 1.1 Update `houmao-mgr agents launch` and `houmao-mgr project easy instance launch` so `--reuse-home` resolves only stopped compatible preserved-home continuity records and rejects fresh live-owner replacement for this workflow.
- [x] 1.2 Carry stopped-record continuity metadata through the reused-home launch path, including prior tmux session name, without requiring separate registry cleanup before restart.

## 2. Reprojection And Runtime Restart

- [x] 2.1 Ensure reused-home restart reprojects the current launch inputs onto the preserved home, with profile-backed or specialist-backed restart using the current stored configuration plus stronger direct CLI overrides.
- [x] 2.2 Update tmux-backed runtime startup so reused-home restart defaults to the prior tmux session name when available and no explicit `--session-name` override was supplied.
- [x] 2.3 Fail reused-home restart clearly when the preserved tmux session name is still occupied by another live tmux session instead of silently generating a new session name.
- [x] 2.4 Key preserved-home compatibility to the same CLI tool type rather than unchanged specialist or profile settings.

## 3. Regression Coverage

- [x] 3.1 Add CLI and unit coverage showing profile-backed `--reuse-home` restart uses a stopped preserved home and does not require manual registry cleanup first.
- [x] 3.2 Add coverage showing updated stored launch-profile, easy-profile, or specialist-backed inputs are reprojected onto the preserved home during reused-home restart when the CLI tool type stays the same.
- [x] 3.3 Add coverage showing `--reuse-home` rejects live-owner replacement, restores the prior tmux session name by default, and honors an explicit `--session-name` override when supplied.
