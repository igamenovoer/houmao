# Run Log: `project easy specialist create` blocked on Claude auth discovery for `gpu-coder`

## Summary

I attempted to create a reusable easy specialist named `gpu-coder` on the `claude` tool lane through the supported `houmao-mgr project easy specialist create` workflow. The specialist was not created because no usable Claude auth source could be confirmed within the workflow's allowed credential-discovery surfaces.

## Environment

- Date: 2026-04-05 UTC
- Repo: `/data1/huangzhe/code/houmao`
- Requested specialist: `gpu-coder`
- Tool lane: `claude`
- Resolved default credential bundle name: `gpu-coder-creds`
- Resolved launcher: `pixi run houmao-mgr`

## User Inputs During This Attempt

- Initial trigger: `houmao-create-specialist`
- Later inputs:
  - `name=gpu-coder, tool=claude, find credential from claude-kimi`
  - `find credentials in tests/fixtures/agents/ , use kimi api key`
  - `auto credential`

## Commands And Checks Performed

I first resolved the correct launcher and verified the relevant command surfaces:

```bash
pixi run houmao-mgr --help
pixi run houmao-mgr project easy specialist create --help
pixi run houmao-mgr project agents tools claude auth get --help
pixi run houmao-mgr project agents tools claude auth list --help
```

I then checked whether the requested Claude credential bundle already existed project-locally:

```bash
pixi run houmao-mgr --print-json project agents tools claude auth get --name claude-kimi
pixi run houmao-mgr --print-json project agents tools claude auth list
```

Observed result:

- `claude-kimi` was not found under `.houmao/agents/tools/claude/auth/`
- the project-local Claude auth list was empty

After the user explicitly opted into auto credential discovery, I scanned only the supported Claude auth surfaces allowed by the skill:

```bash
printf 'CLAUDE_CONFIG_DIR=%s\nANTHROPIC_API_KEY=%s\nANTHROPIC_AUTH_TOKEN=%s\nANTHROPIC_BASE_URL=%s\nANTHROPIC_MODEL=%s\n' \
  "${CLAUDE_CONFIG_DIR-}" "${ANTHROPIC_API_KEY-}" "${ANTHROPIC_AUTH_TOKEN-}" "${ANTHROPIC_BASE_URL-}" "${ANTHROPIC_MODEL-}"

find /data1/huangzhe/code/houmao/.claude -maxdepth 2 \( -name 'claude_state.template.json' -o -name '*.json' \) | sort
find "$HOME/.claude" -maxdepth 2 \( -name 'claude_state.template.json' -o -name '*.json' \) | sort
```

Observed result:

- `ANTHROPIC_API_KEY` was unset
- `ANTHROPIC_AUTH_TOKEN` was unset
- `ANTHROPIC_BASE_URL` was unset
- `ANTHROPIC_MODEL` was unset
- no `claude_state.template.json` was found in the repo-local Claude home or the user-home Claude config

## What Happened

The specialist-create workflow reached the point where auth was required, but no acceptable source could be mapped into Claude create flags:

- no existing project-local Claude auth bundle was available to reuse
- no supported Claude environment variables were set
- no reusable Claude state template file was present in the allowed Claude config locations

Because of that, I did not run the create command itself:

```bash
pixi run houmao-mgr project easy specialist create --name gpu-coder --tool claude ...
```

## Why The Attempt Is Blocked

This run is blocked by the `houmao-create-specialist` skill guardrails, not by a CLI crash:

- the workflow does not allow guessing API keys, auth tokens, model names, or base URLs
- the workflow does not allow scanning arbitrary repo subdirectories for credentials
- the user specifically asked to inspect `tests/fixtures/agents/`, but that location is outside the skill's permitted auto-credential scan surfaces
- the skill only permits auto-discovery from the selected tool's maintained config locations and supported environment variables, and those checks were insufficient here

In practical terms, the blocker is: there is still no confirmed Claude auth input that can legally be passed to `project easy specialist create`.

## What Is Needed To Unblock

One of the following is required:

1. Explicit Claude auth inputs such as `--api-key` and, if needed, `--base-url` or `--claude-model`.
2. A valid project-local Claude auth bundle name that already exists under `.houmao/agents/tools/claude/auth/`.
3. A supported Claude credential source appearing in the allowed auto-discovery surfaces on a later retry.

Until one of those exists, `gpu-coder` cannot be created through the supported specialist workflow.
