## Why

The packaged Houmao system skills currently teach agents to search for `houmao-mgr` by walking multiple development-only launcher options before trying the ordinary installed command. That behavior is slow, inconsistent with the documented end-user installation path, and causes agents to probe `.venv`, Pixi, and project-local uv state even when `houmao-mgr` is already available on `PATH`.

## What Changes

- Change the packaged system-skill launcher contract to prefer `command -v houmao-mgr` as the default first step.
- Make uv the default fallback when `command -v houmao-mgr` fails, reflecting the documented official installation path for Houmao.
- Move development-environment launchers such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, and project-local `uv run houmao-mgr` behind the PATH-first and uv-fallback defaults.
- Require the skills to honor an explicit user request for a specific launcher family even when the default order would choose a different launcher.
- Revise the top-level skill routers, shared launcher reference text, and downstream action pages so they no longer imply the old development-hint-first search order.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mailbox-mgr-skill`: update the mailbox-admin skill launcher contract to use `command -v houmao-mgr` first, uv fallback second, and development launchers only after that or when the user explicitly requests them.
- `houmao-manage-credentials-skill`: update auth-bundle skill launcher selection to the new PATH-first, uv-second default and explicit user-override behavior.
- `houmao-create-specialist-skill`: update the specialist-management skill launcher requirement, even though the packaged skill name is now `houmao-manage-specialist`.
- `houmao-manage-agent-definition-skill`: update low-level definition-management launcher selection to the new default order and explicit override rules.
- `houmao-manage-agent-instance-skill`: update managed-agent lifecycle launcher selection to the new default order and explicit override rules.
- `houmao-agent-messaging-skill`: update managed-agent messaging launcher selection to the new default order and explicit override rules.
- `houmao-agent-gateway-skill`: update gateway-skill launcher selection to the new default order and explicit override rules.

## Impact

- Affected packaged skill assets under `src/houmao/agents/assets/system_skills/`, especially the seven top-level `SKILL.md` routers, the shared mailbox launcher reference, and action pages that currently refer to a separately "resolved" launcher.
- Affected OpenSpec capability specs for those seven skills.
- Affected unit tests that currently assert the older `uv run houmao-mgr` development-lane wording in installed skill text.
