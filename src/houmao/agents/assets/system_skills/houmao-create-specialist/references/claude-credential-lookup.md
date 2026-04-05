# Claude Credential Lookup

Use this reference only when `--tool claude` and the active credential-source mode needs tool-specific lookup guidance.

This page is grounded in Claude Code's official docs, the local `extern/orphan/claude-code` source checkout, and the installed `claude` executable.

## Maintained Roots And Surfaces

- `CLAUDE_CONFIG_DIR` is the maintained Claude config-home override.
- If `CLAUDE_CONFIG_DIR` is set, treat that directory as the Claude config root.
- Otherwise treat `~/.claude` as the normal user config root.
- Project-level Claude settings may exist under `<repo-root>/.claude/settings.json` and `<repo-root>/.claude/settings.local.json`.
- Claude's vendor login credential file is `.credentials.json` under the Claude config root.
- Companion Claude global state may exist as `.claude.json` either inside the selected Claude config root or next to a normal `~/.claude` root as `~/.claude.json`.

## Env Lookup Mode

When the user explicitly points you at env names or patterns, relevant Claude env vars include:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_AUTH_TOKEN`
- `CLAUDE_CODE_OAUTH_TOKEN`
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_MODEL`
- `CLAUDE_CODE_USE_BEDROCK`
- `CLAUDE_CODE_USE_VERTEX`
- `CLAUDE_CODE_USE_FOUNDRY`

Directly importable Claude env-backed inputs for `project easy specialist create` are:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_AUTH_TOKEN`
- `CLAUDE_CODE_OAUTH_TOKEN`
- optional `ANTHROPIC_BASE_URL`
- optional `ANTHROPIC_MODEL`

Map those to `--api-key`, `--claude-auth-token`, `--claude-oauth-token`, `--base-url`, and `--claude-model`.

If matched env vars only indicate Bedrock, Vertex, Foundry, or other non-importable lanes, report that the currently active Claude auth is not directly importable for this command.

## Directory Scan Mode

If the user points you at one directory, scan only inside that directory.

If the directory looks like a repo root, inspect only likely Claude paths inside it:

- `.claude/settings.json`
- `.claude/settings.local.json`
- `.claude/claude_state.template.json`

If the directory looks like a Claude config root, inspect only likely Claude files inside it:

- `.credentials.json`
- `.claude.json`
- `settings.json`
- `settings.local.json`
- `claude_state.template.json`

Use these files to classify Claude's current auth shape without executing any referenced helper scripts.

If the directory contains `.credentials.json`, that directory is importable as `--claude-config-dir`. A companion `.claude.json` should be carried with it when present.

If discovery finds only a reusable `claude_state.template.json`, you may carry it as `--claude-state-template-file`, but only as optional bootstrap state. It is not itself a Claude credential-providing method.

## Auto Credentials Mode

When the user explicitly asks for `auto credentials`, search in this order:

1. repo-local Claude candidate
2. home-dir Claude candidate
3. current process env

For the repo-local Claude candidate:

- If `CLAUDE_CONFIG_DIR` is already set and resolves inside the current repo, inspect that directory first.
- Otherwise inspect `<repo-root>/.claude` if it exists.

For the home-dir Claude candidate:

- If `CLAUDE_CONFIG_DIR` is already set and points under the user's home, inspect that directory first.
- Otherwise inspect `~/.claude`.
- If the selected Claude config root contains `.credentials.json`, map that root to `--claude-config-dir`.
- Treat companion `.claude.json` as part of the same maintained vendor login-state lane when it exists, not as a standalone importable file.
- If the selected environment already exposes `CLAUDE_CODE_OAUTH_TOKEN`, map it to `--claude-oauth-token`.

Prefer one coherent Claude source rather than mixing unrelated settings, files, and env vars.

## Importable Forms

Claude auth is directly importable for easy specialist creation only when you can recover one of these supported forms:

- `ANTHROPIC_API_KEY` with optional `ANTHROPIC_BASE_URL` and optional `ANTHROPIC_MODEL`
- `ANTHROPIC_AUTH_TOKEN` with optional `ANTHROPIC_BASE_URL` and optional `ANTHROPIC_MODEL`
- `CLAUDE_CODE_OAUTH_TOKEN` with optional `ANTHROPIC_BASE_URL` and optional `ANTHROPIC_MODEL`
- a maintained Claude config root containing `.credentials.json` and companion `.claude.json` when present

Claude may also carry an optional reusable `claude_state.template.json` as bootstrap state, but that file is not itself a credential-providing method.

Map them to:

- `--api-key`
- `--claude-auth-token`
- `--claude-oauth-token`
- `--claude-config-dir`
- `--base-url`
- `--claude-model`
- optional `--claude-state-template-file` for reusable bootstrap state only

## Non-Importable Or Unsupported Claude Shapes

Report failure and ask the user for supported explicit auth when discovery finds only:

- a standalone `.claude.json` without the maintained `.credentials.json` config-root login state
- `apiKeyHelper` configuration without a separately recoverable reusable key, OAuth token, or Claude config root
- Bedrock, Vertex, or Foundry auth selected through Claude provider env vars
- other runtime-only Claude auth state that cannot be mapped into the supported create-command flags

Do not assume any Houmao test-fixture paths exist on the deployment host.
