## Why

Houmao's ordinary users mostly work through the project/easy path, but the current CLI and docs still present project overlays as optional convenience state beside lower-level agent-definition concepts. This blurs user-facing project agent management with provider-aligned native launch material and makes ancestor `.houmao` discovery risky when global state also lives under `~/.houmao`.

## What Changes

- **BREAKING**: Make an active Houmao project a first-class prerequisite for ordinary maintained local Houmao workflows. Stateful project-backed commands fail clearly when no project is active, except explicit initialization and status/discovery flows.
- **BREAKING**: Remove the public `project easy` nesting by promoting the higher-level easy commands to ordinary project commands such as `project specialist ...`, `project profile ...`, and project-scoped managed-agent lifecycle commands.
- **BREAKING**: Move provider-aligned raw agent-definition operations out of `project agents ...` and into `houmao-mgr internals native-agent ...`.
- **BREAKING**: Rename internal low-level terminology so project concepts and native-provider concepts no longer collide:
  - raw agent definition / agent-def -> native agent / native-agent root,
  - launch profile -> launch dossier,
  - raw profile -> launch dossier or native launch dossier where disambiguation is needed.
- Keep the native-agent layer as an internal but supported compatibility/projection layer because Claude, Codex, Gemini, and related native CLI tools still understand provider launch material rather than Houmao specialists.
- Move the shared registry default from `~/.houmao/registry` to the platformdirs-backed user config root, expected as `~/.config/houmao/registry` on Linux, while preserving the existing `HOUMAO_GLOBAL_REGISTRY_DIR` override.
- Update packaged system skills, command templates, config drafts, docs, and tests to use the new project/native vocabulary and command shapes.

## Capabilities

### New Capabilities
- `houmao-mgr-native-agent-internals-cli`: internal provider-aligned native-agent management commands, including roles, recipes, launch dossiers, native-agent roots, and native build/launch escape hatches.

### Modified Capabilities
- `houmao-mgr-project-cli`: make project the first-class ordinary Houmao command family and expose promoted specialist/profile/managed-agent commands without `easy`.
- `houmao-mgr-project-easy-cli`: retire the public `project easy` command family by replacing it with promoted project command paths and terminology.
- `houmao-mgr-project-agent-tools`: move project agent tool/setup management into the native-agent internals surface.
- `houmao-mgr-project-agents-roles`: move low-level role management into the native-agent internals surface.
- `houmao-mgr-project-agents-presets`: move low-level recipe/preset management into the native-agent internals surface.
- `houmao-mgr-project-agents-launch-profiles`: move explicit recipe-backed launch profile management into native-agent launch dossiers.
- `project-aware-local-roots`: require an active project for ordinary local stateful commands instead of implicitly bootstrapping `<cwd>/.houmao` outside explicit initialization flows.
- `houmao-owned-dir-layout`: move global shared defaults from the legacy `~/.houmao` home anchor to the platformdirs user config anchor while keeping project-local state in the active overlay.
- `agent-discovery-registry`: change the default shared registry root to the platformdirs user config root while preserving env override behavior.
- `houmao-manage-agent-definition-skill`: update packaged skill guidance from agent-definition/easy/raw-profile language to specialist/profile/native-agent/launch-dossier language and command paths.
- `houmao-mgr-config-drafts`: rename draft families and generated guidance so project drafts target promoted project commands and native launch material is called launch dossiers.
- `houmao-mgr-command-template-renderer`: update maintained command-template ids and rendered argv shapes for the promoted project commands and native-agent internals.

## Impact

- CLI command tree and help text in `src/houmao/srv_ctrl/commands/`.
- Project overlay resolution and owned path helpers in `src/houmao/project/overlay.py` and `src/houmao/owned_paths.py`.
- Project catalog projection, launch-profile models, and compatibility native-agent materialization.
- Packaged system skills under `src/houmao/agents/assets/system_skills/`.
- OpenSpec specs and documentation for project workflows, registry roots, command templates, and config drafts.
- Tests covering CLI shape, path defaults, project discovery, registry discovery, system skills, command templates, and config drafts.
