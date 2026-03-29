## Why

`houmao-mgr project easy instance launch` currently has no first-class way to add extra environment variables, so operators fall back to ambient shell state or abuse auth bundles for non-credential launch tweaks. That is the wrong split: some env belongs only to one concrete launch, while some env belongs to the reusable specialist and should survive later relaunch because it is part of that specialist's launch posture.

This change needs to separate those two intents explicitly instead of persisting one-off launch-time env through runtime relaunch metadata or mixing durable non-credential launch env into credential env files.

## What Changes

- Add repeatable one-off `--env-set <env-spec>` to `houmao-mgr project easy instance launch`.
- Make `project easy instance launch --env-set` live-session-only: it applies to the current started session but does not survive later relaunch.
- Add persistent specialist-owned env records as a separate specialist launch-config concept.
- Extend `project easy specialist create` to accept repeatable `--env-set NAME=value` for persistent specialist-owned env records.
- Extend specialist inspection to report env records separately from the credential bundle and its auth env.
- Extend the existing specialist launch schema, which already carries launch posture like `launch.prompt_mode`, with a dedicated `launch.env_records` section instead of folding persistent env into auth env files.
- Keep credential env and specialist env records distinct:
  - credential env remains tool-auth-owned input
  - specialist env records remain non-credential specialist launch config
- Compose runtime env with explicit precedence so specialist env survives relaunch through normal rebuild while one-off instance env does not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-project-easy-cli`: `project easy specialist create|get` gains persistent `--env-set` handling, and `project easy instance launch` gains one-off additional `--env-set` that does not survive relaunch.
- `component-agent-construction`: preset launch schema and brain-manifest env contract gain specialist-owned `launch.env_records` as a separate channel from auth-bundle env.
- `brain-launch-runtime`: runtime env composition distinguishes persistent specialist env from live-session-only one-off launch env, and relaunch rebuild keeps only the persistent specialist channel.

## Impact

- Affected code:
  `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/definition_parser.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/launch_plan.py`, and project catalog/projection helpers.
- Affected tests:
  project easy specialist and instance CLI coverage, preset parsing tests, brain-builder env-contract tests, and tmux-backed relaunch tests.
- Affected operator surfaces:
  `houmao-mgr project easy specialist create|get` and `houmao-mgr project easy instance launch`.
- Affected persisted/runtime-visible state:
  project-local specialist launch config, projected preset YAML, built brain manifests, and live-session launch-plan env.
- Dependencies and systems:
  project catalog-backed specialist storage, compatibility preset projection, brain construction, and tmux-backed relaunch.
