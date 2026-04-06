## 1. Shared Installer And State

- [x] 1.1 Add explicit system-skill projection mode modeling in `src/houmao/agents/system_skills.py`, including per-record `projection_mode` state and normalization of pre-mode copy-only install-state records.
- [x] 1.2 Implement shared projection helpers for copied and absolute-symlink installs, including stable filesystem-backed packaged asset resolution and explicit failure when symlink projection is unavailable.
- [x] 1.3 Update install-time ownership checks and previous-owned-path cleanup so copy-to-symlink and symlink-to-copy reinstalls safely replace the owned in-home path without treating resolved symlink targets as inside-home content.

## 2. CLI Surface And Docs

- [x] 2.1 Add `--symlink` to `houmao-mgr system-skills install` and thread the selected projection mode through install result payloads.
- [x] 2.2 Extend `houmao-mgr system-skills status` JSON and plain-text output to report projection mode for each recorded installed skill while preserving current summary fields.
- [x] 2.3 Update the `system-skills` CLI documentation to describe copied vs symlink installs, absolute symlink targets, and the local-machine caveat for moved Python environments.

## 3. Verification

- [x] 3.1 Add unit coverage for explicit copy installs, explicit symlink installs, unsupported symlink-source failure, and reinstall mode switches in `tests/unit`.
- [x] 3.2 Add CLI tests for `system-skills install --symlink` and `system-skills status` projection-mode reporting.
- [x] 3.3 Run OpenSpec validation for `add-system-skills-symlink-install-mode` and the targeted unit test suites covering the installer and CLI.
