## Why

Houmao currently treats a healthy vendor-supported Claude login as evidence that Claude works, but not as reusable auth that `project easy specialist create --tool claude` can actually import. That leaves operators stuck between Claude's supported credential lanes and Houmao's narrower Claude auth contract, especially when the machine is already logged in through `claude auth login`.

The current Claude docs and skill guidance also blur `claude_state.template.json` together with credential material, even though that file is optional runtime bootstrap state rather than a credential-providing method. That wording gap makes the Claude auth story harder to understand than it needs to be.

## What Changes

- Extend Claude project auth bundles and easy-specialist creation so Houmao can represent two maintained vendor-supported Claude lanes in addition to the existing API-key and `ANTHROPIC_AUTH_TOKEN` inputs:
- a reusable Claude login-state lane based on vendor-owned files under `CLAUDE_CONFIG_DIR` such as `.credentials.json` and `.claude.json`,
- a reusable explicit OAuth-token lane based on `CLAUDE_CODE_OAUTH_TOKEN`.
- Keep `claude_state.template.json` as an optional Claude runtime-state template input and clarify across the product surface that it is not itself a credential-providing method.
- Update Claude auto-credential discovery and importability rules so the packaged `houmao-create-specialist` skill can treat those vendor-supported Claude lanes as importable rather than rejecting them as "logged in but unsupported".
- Update Claude runtime bootstrap and auth projection rules so a Claude runtime can launch unattended from either minimal env credentials or projected vendor login state without Houmao clobbering the vendor-owned files it imported.
- Update user-facing docs, CLI reference wording, and skill/reference guidance so Claude's real credential lanes are described clearly and `claude_state.template.json` is documented only as optional bootstrap state.

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-mgr-project-agent-tools`: Claude auth bundle management needs to accept and preserve vendor-supported Claude OAuth token and login-state inputs.
- `houmao-mgr-project-easy-cli`: Easy specialist creation needs to accept the new Claude auth lanes and persist them into the derived credential bundle.
- `houmao-create-specialist-credential-sources`: Claude auto-credential discovery needs to recognize vendor-supported Claude login state and `CLAUDE_CODE_OAUTH_TOKEN` as importable Houmao inputs.
- `houmao-create-specialist-skill`: The packaged specialist-authoring skill needs to distinguish Claude credential lanes from the optional `claude_state.template.json` bootstrap template.
- `claude-cli-noninteractive-startup`: Claude unattended bootstrap needs to coexist with projected vendor login-state files instead of assuming only template-derived `.claude.json` state.
- `docs-easy-specialist-guide`: The easy-specialist guide needs to describe Claude credential methods separately from the optional Claude state-template input.
- `docs-cli-reference`: The `houmao-mgr` CLI reference needs to distinguish Claude credential-providing inputs from the optional Claude state-template input.

## Impact

- `src/houmao/srv_ctrl/commands/project.py`
- `src/houmao/project/assets/starter_agents/tools/claude/adapter.yaml`
- `src/houmao/agents/realm_controller/backends/claude_bootstrap.py`
- `src/houmao/agents/assets/system_skills/houmao-create-specialist/SKILL.md`
- `src/houmao/agents/assets/system_skills/houmao-create-specialist/references/claude-credential-lookup.md`
- `docs/getting-started/easy-specialists.md`
- `docs/reference/cli/houmao-mgr.md`
- `openspec/specs/houmao-create-specialist-skill/spec.md`
- `openspec/specs/docs-easy-specialist-guide/spec.md`
- `openspec/specs/docs-cli-reference/spec.md`
- Claude auth and skill regression coverage in `tests/unit/srv_ctrl/test_project_commands.py` and `tests/unit/agents/test_system_skills.py`
