# Project Specialists

Use this subskill when the user wants to create, inspect, update, list, or remove one project specialist through `project specialist ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) for create requests or credential-reference edits.
- Confirm the target is a specialist, not a project profile, native launch dossier, or live managed agent.
- For create requests, resolve specialist name, tool, and credential from the prompt, nearby explicit context, or Specialist Create Defaulting before choosing a credential path.

## Actions

- List specialists: no name required.
- Get specialist: require `--name`.
- Create specialist: require `--name`; if `--tool` or `--credential` is omitted, use Specialist Create Defaulting.
- Set specialist: require `--name` and at least one supported mutation.
- Remove specialist: require `--name`.

## Command Shapes

```text
<chosen houmao-mgr launcher> project specialist list
<chosen houmao-mgr launcher> project specialist get --name <name>
<chosen houmao-mgr launcher> project specialist remove --name <name>
```

For `create`, use the CLI-owned config draft before running the maintained command:

```text
<chosen houmao-mgr launcher> internals config-drafts generate --id project.specialist --intent '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}'
```

The `project.specialist` config draft is intentionally minimal. Its JSON intent must contain a top-level `fields` object whose only draft fields are `name`, `tool`, and `credential`. For prompt content, setup changes, model/reasoning, skills, env records, system-skill policy, mailbox posture, or credential material, use the maintained `project specialist create|set` command fields directly instead of adding them to the draft intent.

For `set`, keep the maintained patch command explicit and include only the user-requested mutation fields.

## Create Inputs

Common specialist inputs:

- `--name`
- `--tool claude|codex|gemini|kimi`
- `--credential <name>`
- `--system-prompt` or `--system-prompt-file`
- `--setup <name>`; default is `default`
- `--no-unattended` only when the user explicitly wants `as_is`; do not invent this flag from preference. For Kimi TUI automation, keep the default unattended prompt mode instead of adding raw Kimi permission flags.
- `--model`
- `--reasoning-level`
- repeatable `--with-skill <dir>`
- repeatable `--env-set NAME=value`

Tool-specific auth inputs:

- Claude: `--api-key`, optional `--claude-auth-token`, optional `--claude-oauth-token`, optional `--claude-config-dir`, optional `--base-url`, optional `--claude-model`
- Claude optional bootstrap state: `--claude-state-template-file`; this is optional bootstrap state and not a credential-providing method
- Codex: `--api-key`, optional `--base-url`, optional `--codex-org-id`, optional `--codex-auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--gemini-oauth-creds`
- Kimi: `--api-key`, optional `--base-url`, optional `--kimi-model-name`, optional `--provider-type`, optional `--kimi-code-home`, optional `--kimi-config-toml`, optional `--kimi-credential-json`

## Credential Discovery During Create

Use credential discovery only for specialist creation.

When the user omits tool or credential input, first apply Specialist Create Defaulting from [../common/credential-routing.md](../common/credential-routing.md):

- no Houmao project or `HOUMAO_NATIVE_AGENT_ROOT`: stop and report how to select one;
- no registered credentials: stop and suggest adding or logging in one credential;
- registered credentials exist: pick a matching registered credential based on the prompt or nearby context; if nothing matches, use the credential with the latest listed update time.

The supported modes are:

- Explicit Auth Mode
- Env Lookup Mode
- Directory Scan Mode
- Auto Credentials Mode
- No Discovery Mode

Load only the selected tool credential-kind reference when needed:

- Claude: [../../../houmao-credential-mgr/references/claude-credential-kinds.md](../../../houmao-credential-mgr/references/claude-credential-kinds.md)
- Codex: [../../../houmao-credential-mgr/references/codex-credential-kinds.md](../../../houmao-credential-mgr/references/codex-credential-kinds.md)
- Gemini: [../../../houmao-credential-mgr/references/gemini-credential-kinds.md](../../../houmao-credential-mgr/references/gemini-credential-kinds.md)
- Kimi: [../../../houmao-credential-mgr/references/kimi-credential-kinds.md](../../../houmao-credential-mgr/references/kimi-credential-kinds.md)

For Claude vendor-login files, normalize reuse requests to `--claude-config-dir <claude-config-root>`. If the user points at `.credentials.json`, use its parent directory.

## Set Inputs

Common update and clear inputs:

- `--system-prompt`
- `--system-prompt-file`
- `--clear-system-prompt`
- `--with-skill <dir>`
- `--add-skill <name>`
- `--remove-skill <name>`
- `--clear-skills`
- `--setup <name>`
- `--credential <name>`
- `--prompt-mode unattended|as_is`
- `--clear-prompt-mode`
- `--model`
- `--clear-model`
- `--reasoning-level`
- `--clear-reasoning-level`
- repeatable `--env-set NAME=value`
- `--clear-env`

## Guardrails

- Do not guess the specialist name, tool lane, credential name, or auth values.
- Do not infer tool or credential from installed CLIs, project language, file names, vendor tool homes, or credential storage directory basenames.
- Do not remove and recreate a project specialist for ordinary prompt, skill, setup, credential, prompt-mode, model, reasoning-level, or env edits; use `project specialist set`.
- Do not use `project specialist set` for specialist rename or tool-lane changes. Ask whether to create a new specialist instead.
- Do not enter credential discovery for list, get, set, remove, project profile creation, or launch.
- Do not execute login flows or auth-generation helpers.
- Do not treat `auto credentials` as a literal CLI flag.
- Do not infer auth identity from `.houmao/` auth directory names.
- Do not hand-author specialist config YAML skeletons; use `internals config-drafts generate` for supported minimal specialist config authoring.
- Do not pass model, env, mailbox, prompt, skill, or credential material fields to `project.specialist` config drafts.
- Do not add raw Kimi `--auto` or `--yolo` launch flags to specialists; use prompt mode for managed automation.
