# Login Credential

Use this action only when the user wants to run a maintained provider login helper for a fresh Claude, Codex, or Gemini account and import the resulting auth file into Houmao credential storage. Kimi credential CRUD is supported by the other action pages, and fresh default Kimi Code OAuth login/import is handled by `../subskills/kimi-code-login-handling.md`; Kimi does not have a maintained Houmao credential login helper in this change.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and whether this is a create or explicit update from the current prompt first and recent chat context second when they were stated explicitly.
3. If the selected tool is `kimi`, do not run or invent a maintained Houmao Kimi login helper. For a fresh default Kimi Code OAuth login, load `../subskills/kimi-code-login-handling.md`. For API keys, existing config files, credential JSON files, or existing Kimi Code homes, route Kimi credential creation or updates through `actions/add.md` or `actions/set.md` with explicit Kimi credential inputs instead.
4. If the tool family, credential name, or target is still missing, ask the user before proceeding.
5. Use the default create-only login behavior unless the user explicitly said to update, replace, or refresh an existing credential.
6. Build the direct command: `project credentials <tool> login` for the project lane or `internals native-agent credentials <tool> login` for the direct native-agent lane.
7. Start the direct command in a dedicated tmux session by default, then attach to or inspect that session so the user can complete any provider browser, device-code, console, or paste-back authentication steps.
8. Preserve the current shell's proxy environment in the tmux session by passing set proxy variables explicitly with tmux `-e` arguments.
9. Report the credential name, provider command, and temp-home cleanup status returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target

## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> login --name <credential> [--update]
<chosen houmao-mgr launcher> internals native-agent credentials <tool> login --native-agent-root <dir> --name <credential> [--update]
```

Add `--update` only when the user explicitly intends to replace an existing credential.

## Tmux Login Session

Run the maintained Houmao login command inside tmux by default. This keeps an attachable terminal surface for browser URLs, device codes, paste-back prompts, and provider console prompts without hand-rolling provider home creation or auth-file import.

Use a unique session name and pass through set proxy variables without printing their values:

```bash
session_name="houmao-credential-login-<tool>-<credential>"
login_command='<chosen houmao-mgr launcher> project credentials <tool> login --name <credential> [--update]'

proxy_env_args=()
for name in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy; do
  if [ "${!name+x}" = x ]; then
    proxy_env_args+=(-e "${name}=${!name}")
  fi
done

tmux new-session -d -s "$session_name" "${proxy_env_args[@]}" "$login_command"
tmux attach-session -t "$session_name"
```

For direct native-agent roots, set `login_command` to the maintained native-agent credential login command instead:

```bash
login_command='<chosen houmao-mgr launcher> internals native-agent credentials <tool> login --native-agent-root <dir> --name <credential> [--update]'
```

If `tmux` is not available, ask the user before falling back to a direct foreground run or another terminal-sharing path.

Do not add `--inherit-auth-env` for ordinary proxy preservation. Proxy variables are preserved by the tmux environment setup above. Use `--inherit-auth-env` only when the user explicitly wants the provider login command to keep ambient provider auth variables such as existing API keys, auth tokens, or OAuth tokens.

## Guardrails

- Do not guess the tool family, target, or credential name.
- Do not run or invent a maintained Kimi login helper; use `../subskills/kimi-code-login-handling.md` for explicit Kimi Code OAuth login/import requests.
- Do not add `--update` unless the user explicitly asked to update, replace, or refresh an existing credential.
- Do not manually create provider home directories, run provider login commands, copy auth files into Houmao storage, or delete temp directories for this ordinary workflow; the maintained Houmao credential login command owns temp-home creation, provider CLI invocation, auth artifact import, successful cleanup, and failed-login temp-home reporting.
- Do not print proxy values, provider tokens, API keys, or raw auth-file contents while preparing or reporting the tmux login session.
- Do not use `--inherit-auth-env` as a proxy-inheritance mechanism.
- Do not scan existing provider homes to infer the account unless the user explicitly asks for a lower-level recovery workflow.
- Do not promise fully headless Gemini login; the supported flow launches Gemini in an isolated home and the user may need to finish OAuth interactively before exiting Gemini.
- If the command fails and reports a preserved temp home, report that path as recovery context instead of deleting it yourself.
