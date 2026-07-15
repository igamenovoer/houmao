# Kimi Code Login Handling

Use this subskill only when the user wants a fresh default Kimi Code OAuth login and wants the resulting Kimi Code home imported into Houmao Kimi credential storage. This is a Kimi-specific login/import workflow, not a maintained `houmao-mgr ... credentials kimi login` helper.

Do not use this subskill for Kimi Platform API keys or compatible provider API keys. Route API-key material through `actions/add.md` or `actions/set.md` with `references/kimi-credential-kinds.md`.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the credential name, target, and whether this is create-only or an explicit update from the current prompt first and recent chat context second when they were stated explicitly.
3. If the credential name or target is still missing, ask the user before proceeding.
4. If the user provided an API key, a `config.toml`, a credential JSON file, or an existing Kimi Code home instead of asking for a fresh default OAuth login, stop and route to `actions/add.md` or `actions/set.md`.
5. Resolve the Kimi Code CLI with `command -v kimi || command -v kimi-code`; if neither exists, report that Kimi Code CLI is required for this login workflow.
6. Create an isolated temporary Kimi Code home. Do not use `~/.kimi-code` or any ambient `KIMI_CODE_HOME` for a new Houmao credential login unless the user explicitly asked to import an existing home.
7. Start `kimi login` in a dedicated tmux session by default, with the temporary home and set proxy variables passed into the tmux session.
8. Attach to the tmux session or inspect it so the user can open the verification URL, enter the device code, and complete browser-side authorization.
9. After `kimi login` exits successfully, verify that `<temp-kimi-home>/credentials/kimi-code.json` exists before importing.
10. Import the temp home through the existing Kimi `add` or `set --code-home` command for the selected target.
11. After a successful import, delete only the temporary Kimi Code home that this workflow created. If login or import fails, preserve the temp home path and report it as recovery context.

## Required Inputs

- `name`
- a resolved target
- create-only versus explicit update intent

## Tmux Kimi Login Session

Use a unique session name and pass through set proxy variables without printing their values:

```bash
kimi_cmd="$(command -v kimi || command -v kimi-code)"
kimi_home="$(mktemp -d -t houmao-kimi-login-XXXXXX)"
session_name="houmao-kimi-login-<credential>"

proxy_env_args=()
for name in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy; do
  if [ "${!name+x}" = x ]; then
    proxy_env_args+=(-e "${name}=${!name}")
  fi
done

login_command="KIMI_CODE_HOME=$(printf '%q' "$kimi_home") $(printf '%q' "$kimi_cmd") login"
tmux new-session -d -s "$session_name" "${proxy_env_args[@]}" -e "KIMI_CODE_HOME=$kimi_home" "$login_command"
tmux attach-session -t "$session_name"
```

If `tmux` is not available, ask the user before falling back to a direct foreground run or another terminal-sharing path.

Kimi Code `kimi login` is an OAuth device-code flow. It prints the verification URL and user code, may attempt to open a browser, and waits for browser-side authorization. The Kimi TUI `/login` flow is different because it can also collect Kimi Platform API keys; API-key storage belongs in `actions/add.md` or `actions/set.md`.

## Import Commands

For create-only project import:

```bash
<chosen houmao-mgr launcher> project credentials kimi add --name <credential> --code-home <temp-kimi-home>
```

For explicit project update:

```bash
<chosen houmao-mgr launcher> project credentials kimi set --name <credential> --code-home <temp-kimi-home>
```

For create-only direct native-agent import:

```bash
<chosen houmao-mgr launcher> internals native-agent credentials kimi add --native-agent-root <dir> --name <credential> --code-home <temp-kimi-home>
```

For explicit direct native-agent update:

```bash
<chosen houmao-mgr launcher> internals native-agent credentials kimi set --native-agent-root <dir> --name <credential> --code-home <temp-kimi-home>
```

Use create-only `add` unless the user explicitly said to update, replace, or refresh an existing credential.

## Verification

Before import, verify the default OAuth file exists:

```bash
test -f "$kimi_home/credentials/kimi-code.json"
```

If `config.toml` exists, optionally validate it without printing credential contents:

```bash
KIMI_CODE_HOME="$kimi_home" "$kimi_cmd" doctor config "$kimi_home/config.toml"
```

Do not print raw token JSON or copy credential-file contents into the conversation.

## Non-Default Kimi Code Environments

If the user explicitly needs `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`, or `KIMI_CODE_BASE_URL`, warn before proceeding: Kimi Code may write a scoped OAuth token file such as `credentials/kimi-code-env-<hash>.json`, while the current Houmao Kimi `--code-home` import expects `credentials/kimi-code.json`.

Do not promise that a non-default Kimi Code environment imported through `--code-home` will work unless Houmao import support for that scoped credential filename has been added. Ask before attempting any lower-level recovery path.

## Guardrails

- Do not run or invent `houmao-mgr project credentials kimi login` or `houmao-mgr internals native-agent credentials kimi login`.
- Do not use the operator's default `~/.kimi-code` or ambient `KIMI_CODE_HOME` for a fresh login.
- Do not add `--inherit-auth-env` for Kimi proxy preservation; proxy variables are preserved through the tmux environment setup.
- Do not inherit the full shell environment into the login session just to preserve proxies.
- Do not print proxy values, provider tokens, API keys, raw token JSON, or raw auth-file contents.
- Do not import when `credentials/kimi-code.json` is missing.
- Do not delete a failed-login temp home; preserve and report the path for recovery.
- Do not route Kimi Platform API-key storage through `kimi login`.
