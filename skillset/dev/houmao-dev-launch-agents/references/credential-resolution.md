# Credential and Launcher Resolution

## Workflow

1. **Select the provider resolver.** Codex and Kimi use native auto credentials; Claude uses the ordered fallback chain.
2. **Inspect only approved sources.** Check command availability, recognized environment variable names, provider-native homes, and the bounded trusted `.env` locations below.
3. **Validate without mutating auth.** Use status, doctor, version, or provider-list commands that do not log in, log out, or rewrite credentials.
4. **Return a strategy record.** Include launcher name/path, strategy name, source path, and variable names without values.
5. **Block when no usable strategy exists.** Report the missing source and a manual remediation; do not start an interactive login.

If provider credential state uses an unrecognized custom layout, use the native planning tool to inspect only the user-authorized path and map it to one explicit launch environment without printing values; otherwise stop as blocked.

## Meaning of `auto`

`auto` means reuse the credential state the installed provider CLI would normally discover from its inherited environment or native home. It is a discovery mode, not a credential bundle named `auto`, a CLI flag, or permission to create credentials.

Auto discovery must not run `codex login`, `kimi login`, `claude auth login`, device authorization, browser authentication, logout, or credential mutation.

## Codex Auto Credential

Resolve `command -v codex`, then accept auto credential posture when at least one maintained native lane is usable:

- `codex login status` succeeds
- recognized inherited credential variables are non-empty, such as `OPENAI_API_KEY` or `CODEX_ACCESS_TOKEN`
- the resolved `CODEX_HOME` or default `~/.codex` contains readable native auth state accepted by the installed Codex CLI

Use `codex login status` as the preferred non-secret gate. Do not read or print `auth.json` content. A failed status with no recognized environment lane is a blocker.

For Houmao Codex live testing, inspect `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and their lowercase equivalents. Preserve the proxy variables already present in the environment for the Codex child process. Do not invent or override a proxy server, and record only variable names rather than values.

## Kimi Code Auto Credential

Resolve `command -v kimi`, falling back to `command -v kimi-code`. Accept auto credential posture when one of these native lanes is coherent:

- the resolved `KIMI_CODE_HOME` or default `~/.kimi-code` contains valid `config.toml` plus its referenced native credential/provider state
- recognized inherited env-model variables form a usable provider definition, including model name, API key, and base URL where the provider requires them
- `kimi doctor config <path>` and `kimi provider list --json` confirm a configured provider without exposing a secret

Do not print credential JSON or API-key variables. Do not run Kimi login. Native Kimi `--auto` controls permission posture; it is unrelated to credential discovery.

## Claude Code Ordered Resolver

Evaluate these strategies in order and stop at the first usable one:

1. `command -v claude-kimi`
2. Kimi API endpoint and key in a trusted `.env`
3. `command -v claude-yunwu`
4. other usable `claude-*` launchers resolved through `command -v`
5. native Claude auto credential through `command -v claude`

Do not reorder the chain because a lower-priority launcher is familiar or already visible on `PATH`.

### `claude-kimi`

Run `command -v claude-kimi`. If it resolves, verify the executable exists and a bounded `--version` or `--help` probe reaches Claude Code. Select the wrapper itself as the launcher; do not extract, print, or duplicate its secrets and do not append another unattended flag that it may already own.

### Trusted `.env` Kimi Lane

Inspect `<workdir>/.env`, then the repository-root `.env` when it is a different file. Do not scan arbitrary directories. Treat the file as data, not executable shell code.

Accept a complete pair from recognized names:

- key: `KIMI_API_KEY` or `KIMI_ANTHROPIC_KEY`
- endpoint: `KIMI_BASE_URL`, `KIMI_API_ENDPOINT`, or `KIMI_ANTHROPIC_BASE_URL`

Map the selected values inside a mode-`0700` run-local helper:

- selected Kimi key → `ANTHROPIC_API_KEY`
- selected Kimi endpoint → `ANTHROPIC_BASE_URL`

The helper must parse simple dotenv assignments, strip matching single or double quotes, reject command substitutions and unsupported shell syntax, export the mapped variables only inside the child process, and `exec claude`. Record the `.env` path and selected variable names, never values.

If only one half of the pair exists or the file is unsafe to parse as data, continue to `claude-yunwu` rather than guessing.

### `claude-yunwu`

Run `command -v claude-yunwu` and apply the same executable and bounded probe checks as `claude-kimi`. Select the wrapper as-is when usable.

### Other `claude-*` Launchers

Enumerate command names beginning with `claude-`, sort them, exclude already-tried names, and run `command -v <candidate>` for each. Accept only a candidate whose resolved command is executable and whose bounded `--version` or `--help` probe identifies a Claude Code launcher. Record and skip rejected candidates.

If multiple candidates are usable, prefer the first sorted candidate unless the user selected one explicitly. Do not inspect wrapper secret values.

### Native Claude Auto Credential

Resolve `command -v claude`. Accept native auto credential posture when `claude auth status --json` succeeds or recognized inherited Claude credential variables form a usable lane. The provider-native config directory may be `CLAUDE_CONFIG_DIR` or the normal Claude home.

For unattended native launch, add `--dangerously-skip-permissions`. For explicit `as_is`, do not add it. A failed auth status with no recognized environment lane is the final credential blocker.

## Preferences

Read these preferences as route-shaping defaults after applying hard precedence.

- Prefer provider status/doctor output over reading native credential files.
- Prefer wrapper execution over wrapper secret extraction.
- Prefer the workdir `.env` over the repository-root `.env` when both contain a complete Kimi pair.
- Prefer a blocker over interactive login or guessed environment mappings.

## Constraints

Read these constraints as hard credential-handling boundaries.

- Secret values must not appear in chat, command output, tmux command strings, metadata, diffs, or reports.
- The Claude resolver must evaluate strategies in the declared order.
- `.env` content must not be sourced or executed merely to discover values.
- Auto discovery must not mutate provider auth state.
- A partial endpoint/key pair must not be treated as usable Claude credential state.

## Quality Gates

Read these gates before handing a selected strategy to a provider launch page.

### Metrics

- Resolver coverage: number of declared strategies checked before selection or blocker; complete ordered coverage is better.
- Secret exposure count: detected secret values in output artifacts; lower is better and zero is required.
- Mutation count: auth-changing commands run during discovery; lower is better and zero is required.

### Checks

- Strategy identity: the result names one declared strategy and resolved launcher.
- Precedence: no lower-priority Claude strategy was selected while a higher-priority strategy was usable.
- Non-mutating proof: selection relies on command resolution and status/probe evidence only.
- Secret hygiene: the strategy record contains paths and variable names but no values.
