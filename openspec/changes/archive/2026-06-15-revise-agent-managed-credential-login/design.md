## Context

`houmao-credential-mgr` currently routes credential login requests to the maintained `houmao-mgr project credentials <tool> login` and `houmao-mgr internals native-agent credentials <tool> login` commands. Those commands own the isolated provider home, provider CLI invocation, import, and cleanup lifecycle.

The gap is in agent operation guidance. Provider logins often require a browser URL, device code, paste-back code, or interactive provider prompt. When an agent runs the login helper as a plain command, the operator may not have a stable terminal surface to inspect or interact with. A second gap affects Claude credential creation: Claude Code now exposes `claude setup-token`, described by the local CLI as a long-lived authentication token setup command. Official Claude Code authentication docs map that generated token to `CLAUDE_CODE_OAUTH_TOKEN`, which Houmao already stores through `--oauth-token`.

## Goals / Non-Goals

**Goals:**

- Make the packaged credential skill direct agents to run maintained login helper commands inside a dedicated tmux session.
- Preserve the current shell's proxy environment in that tmux session by default for provider login connectivity.
- Keep the maintained Houmao login helper as the only owner of provider temp homes, artifact import, and cleanup.
- Make Claude `add` guidance prefer the `claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN` lane when the user asks for a new Claude credential without specifying credential material.
- Keep the distinction between `ANTHROPIC_AUTH_TOKEN` bearer-token credentials and Claude Code long-lived OAuth tokens clear.

**Non-Goals:**

- Add a new `houmao-mgr` CLI flag or new provider login helper.
- Automate the `claude setup-token` flow inside Houmao credential storage.
- Change credential bundle file formats or migration behavior.
- Change Kimi login support; Kimi remains CRUD-only for this skill.

## Decisions

1. Wrap maintained login helpers with tmux at the skill level.

   Agents SHALL still build the same `houmao-mgr ... credentials <tool> login --name <name>` command. The skill guidance will teach them to start that command inside a dedicated tmux session, then attach, capture, or send keys as needed. This preserves the maintained command boundary while giving the operator a reliable interactive surface.

   Alternative considered: add tmux orchestration to `houmao-mgr credentials <tool> login`. That would turn a documentation/agent-guidance fix into a CLI behavior change and would duplicate lifecycle concerns already handled by the agent's terminal tooling.

2. Pass proxy variables explicitly into tmux login sessions.

   Tmux has a server and session environment. A long-running tmux server can miss proxy variables that were added to the invoking shell later. The skill guidance will tell agents to include repeated `tmux new-session -e NAME=value` arguments for set proxy variables: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase variants.

   Alternative considered: rely on tmux's default environment update behavior. That is weaker because the session can inherit stale tmux-server state rather than the current process environment.

3. Treat `--inherit-auth-env` as auth-env specific, not proxy inheritance.

   The existing Houmao login helpers start from `os.environ` and scrub provider auth variables unless `--inherit-auth-env` is passed. Proxy variables are not part of that scrub list. The skill should not tell agents to add `--inherit-auth-env` just to preserve proxies; it should reserve that flag for explicit cases where ambient provider auth variables must be preserved.

   Alternative considered: always add `--inherit-auth-env` for tmux login. That can accidentally let stale `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or similar auth material affect a login flow.

4. Prefer Claude Code setup-token output for unspecified Claude creation.

   When a user says to create a new Claude credential and does not specify the credential lane, the skill will present the long-lived Claude Code token as the preferred path: run `claude setup-token`, capture the generated token from the user, and store it with `--oauth-token` as `CLAUDE_CODE_OAUTH_TOKEN`. Existing vendor login import remains available through `credentials claude login` or `--config-dir`.

   Alternative considered: prefer the existing `credentials claude login` vendor-login import. That remains useful, but it creates opaque `.credentials.json` vendor state and is not the best default for CI/script-style credential creation where a one-year token is the intended Claude Code surface.

## Risks / Trade-offs

- Tmux may be unavailable on a user's machine -> the skill must ask the user before falling back to a direct login run or another terminal-sharing method.
- Proxy env values are sensitive in some organizations -> the skill should pass only known proxy variable names and avoid printing secret credential values.
- `claude setup-token` requires a Claude subscription -> the Claude reference must keep API key, vendor-login, and bearer-token lanes available for users without that subscription path.
- Long-lived tokens need careful handling -> the skill must tell agents to treat `CLAUDE_CODE_OAUTH_TOKEN` as an opaque secret and not echo it back after collection.

## Migration Plan

This is a packaged-skill artifact change. Update the affected Markdown assets and any tests that assert installed skill text or OpenSpec behavior. Rollback is a revert of the skill-text change because no stored credential data or CLI contract changes are introduced.
