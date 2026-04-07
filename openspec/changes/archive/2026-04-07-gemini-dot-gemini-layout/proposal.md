## Why

Houmao currently splits managed Gemini home content between `<home>/.gemini` for setup and auth material and `<home>/.agents/skills` for installed skills. That exposes Houmao-managed Gemini skills through a generic `.agents` surface that other CLI tools may discover, and it diverges from Gemini CLI's native `.gemini` layout.

## What Changes

- **BREAKING** Move Houmao-managed Gemini skill projection from `.agents/skills` to `.gemini/skills` for managed brain construction, runtime-owned mailbox skill projection, managed join auto-install, and `houmao-mgr system-skills`.
- Keep Gemini effective home-root semantics unchanged: `GEMINI_CLI_HOME` and omitted-home Gemini CLI flows still resolve the home root itself, but managed skill content lands under `<home>/.gemini/skills`.
- Migrate previously Houmao-owned Gemini system-skill installs from `.agents/skills` to `.gemini/skills` during reinstall or auto-install instead of keeping `.agents/skills` as the maintained contract.
- Update Gemini-facing CLI and runtime documentation to describe `.gemini/skills` as the maintained managed skill surface instead of `.agents/skills`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `brain-launch-runtime`: Gemini managed homes and joined Gemini sessions use `.gemini/skills` as the active Houmao-managed skill root.
- `houmao-system-skill-installation`: Shared Houmao system-skill installation projects Gemini skills under `.gemini/skills` and migrates previously owned `.agents/skills` paths.
- `houmao-system-skill-families`: Flat Gemini Houmao-owned system-skill families use `.gemini/skills` instead of `.agents/skills`.
- `houmao-mgr-system-skills-cli`: `houmao-mgr system-skills install` and `status` for Gemini keep `<cwd>` as the default home root while installing and reporting skills under `.gemini/skills`.
- `agent-mailbox-system-skills`: Gemini runtime-owned mailbox skills project into `.gemini/skills` through top-level Houmao-owned skill directories.
- `docs-cli-reference`: CLI reference pages document `.gemini/skills` as the maintained Gemini managed skill surface.

## Impact

- Affected code: Gemini tool adapter metadata, managed brain construction, runtime mailbox skill projection, shared system-skill installation, and Gemini-specific tests.
- Affected CLI surface: `houmao-mgr system-skills install|status --tool gemini`.
- Affected docs: Gemini system-skills CLI reference and Gemini managed-skill path references.
