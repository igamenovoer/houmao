# Tasks

## 1. Save Reusable Display Settings

- [x] 1.1 Add the two display flags to `project profile create` and `set`, and add independent clear flags to `set`. Extend the shared posture mutation and update detection. Test valid values, display-only edits, omitted-field preservation, same-field set and clear rejection, and `create --yes` replacement.
- [x] 1.2 Verify `project profile get` and the YAML projection report the saved fields under `defaults.posture`, with absent values omitted. Add saved-profile and single-field clear examples to the profile guide, and check their command syntax against CLI help.

## 2. Resolve Display Settings at Launch

- [x] 2.1 Add optional one-shot flags to `project agents launch` and pass the independently resolved style and detail to the existing headless launch path. Test `--specialist`, profile inheritance, both per-field overrides, built-in defaults, and preservation of the saved profile.
- [x] 2.2 Validate authored values and the resolved mode before projection, build, or takeover. Test direct and inherited settings with TUI, service, and Web, explicit default values, a direct headless mode override, malformed stored values, and the execution owner's determinate rejection with the diagnostic visible to the caller.
- [x] 2.3 Document the launch flags, the override order, and headless mode validation in the manager reference. Explain the pane's style and detail, the manager print style, and `turn events --detail`. Verify the example commands and option descriptions against the implemented CLI and renderer.

## 3. Verify the Session and Pane

- [x] 3.1 Verify both fields in manifest metadata and in the bridge invocation. Use an isolated tmux fixture with deterministic provider events to check detailed plain output and a configured JSON or fancy style. Cover resume and relaunch after a profile edit, including fallback for a missing field in a supported manifest.
- [x] 3.2 Run the focused project command, execution routing, manifest, and headless rendering tests. Run `pixi run lint`, `pixi run typecheck`, `pixi run docs-build`, and `openspec validate configure-headless-launch-display --strict`.
