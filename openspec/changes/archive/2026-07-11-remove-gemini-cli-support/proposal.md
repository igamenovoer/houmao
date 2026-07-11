## Why

Gemini CLI support is scheduled for removal, so retaining its TUI compatibility path, headless backend, credentials, schemas, demos, documentation, and system-skill guidance creates maintenance cost for a provider Houmao no longer intends to support. Removing the lane now keeps the actively developed provider surface limited to Claude Code, Codex, and Kimi Code.

## What Changes

- **BREAKING**: Remove Gemini CLI as a supported Houmao provider across TUI/local-interactive compatibility, headless execution, managed launch, join, resume, gateway, passive-server, server, and AG-UI runtime paths.
- **BREAKING**: Remove `gemini`, `gemini_cli`, and `gemini_headless` from public CLI choices, request models, manifests, registries, schemas, provider adapters, process recognition, and backend dispatch.
- **BREAKING**: Remove Gemini credential CRUD/import/login, project-specialist creation inputs, auth-profile handling, starter-agent assets, launch-policy strategies and hooks, model projection, and launch overrides.
- **BREAKING**: Stop installing, discovering, reporting, or uninstalling Houmao system skills through Gemini's `.gemini/skills` layout.
- Remove Gemini-specific source modules, tracked fixtures, demo lanes, tests, and dedicated current reference material. Regenerate the encrypted local auth fixture archive without Gemini fixture entries.
- Update all maintained documentation, repository guidance, context designs, CLI references, and packaged system skills so they teach only Claude, Codex, and Kimi provider workflows.
- Preserve archived OpenSpec changes and immutable historical investigation logs as historical records. Delete maintained Gemini issue, summary, and executable legacy-demo content.
- Delete the provider atomically. Do not add migration code, compatibility parsing, tombstone adapters, aliases, retirement messages, special Gemini error branches, or stale-path cleanup.

## Capabilities

### New Capabilities

- `native-cli-provider-support`: Define the maintained native CLI provider set as Claude Code, Codex, and Kimi Code, with no residual Gemini surface.

### Modified Capabilities

- `brain-launch-runtime`: Remove Gemini TUI/headless backend selection, launch, resume, manifest, gateway, and runtime dispatch contracts.
- `houmao-cao-control-core`: Remove the `gemini_cli` compatibility provider and its TUI command, status, and interrupt behavior.
- `passive-server-headless-management`: Remove Gemini from passive-server headless launch and recovery support.
- `houmao-mgr-project-easy-cli`: Remove Gemini specialist, credential-source, profile, and required-headless behavior from project-easy commands.
- `houmao-mgr-credentials-cli`: Remove the Gemini credential command family, login/import surfaces, and provider-specific auth validation.
- `houmao-mgr-native-agent-internals-cli`: Remove Gemini from native-agent tool, credential, recipe, build, and launch choices.
- `houmao-mgr-project-agent-tools`: Remove the Gemini tool subtree from project agent-tool inspection and setup administration.
- `agent-model-selection`: Remove Gemini settings projection and reasoning-policy targets.
- `recipe-launch-overrides`: Remove Gemini tool/backend validation and typed-parameter behavior.
- `versioned-launch-policy-registry`: Delete maintained Gemini strategy coverage and provider hooks from the registry contract.
- `headless-output-rendering`: Remove Gemini stream parsing and rendering behavior.
- `agent-mailbox-system-skills`: Remove Gemini runtime-home skill projection and Gemini mailbox-skill paths.
- `agent-gateway-mail-notifier`: Remove Gemini-specific installed-skill notifier prompt behavior.
- `single-agent-gateway-wakeup-headless-demo`: Reduce the maintained demo to Claude and Codex lanes.
- `houmao-create-specialist-credential-sources`: Remove Gemini credential sources from specialist creation.
- `houmao-create-specialist-skill`: Remove Gemini from agent-facing specialist creation guidance.
- `houmao-manage-agent-definition-skill`: Remove Gemini profiles, credentials, and launch guidance from the unified agent-definition skill.
- `houmao-manage-agent-instance-skill`: Remove Gemini instance-launch guidance and provider choices.
- `houmao-manage-credentials-skill`: Remove Gemini credential kinds, actions, references, and examples.
- `houmao-mgr-system-skills-cli`: Remove Gemini as a system-skill installation target.
- `houmao-system-skill-families`: Remove Gemini-native projection and discovery guidance from packaged skill families.
- `houmao-system-skill-installation`: Remove `.gemini/skills` installation, status, synchronization, and removal contracts.
- `official-tui-state-tracking`: Remove residual Gemini process/profile references from the maintained TUI tracking provider boundary.
- `docs-cli-reference`: Remove Gemini commands, options, examples, provider lists, and output contracts from maintained CLI documentation.
- `docs-getting-started`: Remove Gemini setup, launch, credential, and provider guidance from getting-started material.
- `docs-launch-policy-reference`: Remove Gemini unattended launch-policy documentation.
- `docs-run-phase-reference`: Remove Gemini backends, manifests, lifecycle, role injection, and runtime examples.
- `docs-system-skills-overview-guide`: Remove Gemini system-skill target and credential guidance.
- `readme-structure`: Remove Gemini from README provider lists and examples.

## Impact

- Runtime code under `src/houmao/agents/`, `src/houmao/server/`, `src/houmao/passive_server/`, `src/houmao/ag_ui/`, `src/houmao/shared_tui_tracking/`, and `src/houmao/srv_ctrl/` loses Gemini-specific branches, types, schemas, and modules.
- `src/houmao/project/assets/starter_agents/tools/gemini/`, `src/houmao/agents/launch_policy/registry/gemini.yaml`, and `src/houmao/agents/realm_controller/backends/gemini_headless.py` are deleted.
- Gemini provider values disappear from CLI/API validation and persisted schema enums. State produced by older releases is outside the next release's contract and requires no handling.
- The maintained headless gateway wake-up demo drops its Gemini lane. The dedicated legacy Gemini demo and current Gemini issue/knowledge material are deleted.
- Gemini fixtures under `tests/fixtures/plain-agent-def/` and `tests/fixtures/auth-bundles/` are removed, and provider-parametrized tests are updated to cover the remaining provider set.
- Packaged system skills delete Gemini-only credential references and remove Gemini guidance from agent definition, instance, credential, touring, and related active instruction files.
- Maintained docs, root guidance files, context designs, and current OpenSpec capability contracts are updated. Archived OpenSpec artifacts remain intact.
