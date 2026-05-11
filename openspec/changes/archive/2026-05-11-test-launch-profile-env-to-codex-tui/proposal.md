## Why

GitHub issue #60 reports that `defaults.env` values stored on launch profiles do not reach the Codex TUI process started inside a Houmao-managed tmux session. This breaks practical Codex launches that need proxy environment variables such as `http_proxy` and `https_proxy`, and the current tests do not exercise the full easy-profile-to-Codex-TUI path.

## What Changes

- Add regression coverage that creates an easy launch profile with durable env records through `houmao-mgr project easy profile create --env-set`.
- Launch a Codex TUI managed agent from that profile through `houmao-mgr project easy instance launch --profile`.
- Verify the profile env records are visible from inside the launched tmux session, not only in catalog rows, projected YAML, brain manifests, or in-memory launch plans.
- Keep the test focused on non-secret env such as proxy variables and a sentinel feature flag.
- Document the expected env propagation boundary so future launch-profile, tmux, or Codex startup refactors cannot silently drop these records again.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: profile-backed Codex TUI launches must be covered by an end-to-end-style regression that starts from `project easy profile create --env-set` and launches through `project easy instance launch --profile`.
- `tmux-integration-runtime`: tmux-backed managed-agent sessions must preserve launch-profile-derived env records into the live provider pane environment.

## Impact

- Affected code: expected test targets include `tests/unit/srv_ctrl/test_project_commands.py`, `tests/unit/agents/realm_controller/`, or a focused runtime/tmux test module that can exercise the profile launch chain without requiring real OpenAI network access.
- Affected runtime path: project catalog launch-profile storage, profile-backed launch resolution, brain manifest env contract, `LaunchPlan.env`, tmux session environment publication, and local interactive Codex startup.
- Affected operator surface: `houmao-mgr project easy profile create --env-set` and `houmao-mgr project easy instance launch --profile`.
- External systems: no live OpenAI call should be required; the test can use a fake Codex executable or controlled tmux pane command to inspect the launched environment.
