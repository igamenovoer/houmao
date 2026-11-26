# Project Specialists

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this subskill when the user wants to create, inspect, update, list, or remove one project specialist through `project specialist ...`.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
- Read [../../references/common/credential-routing.md](../../references/common/credential-routing.md) for create requests or credential-reference edits.
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
<chosen houmao-mgr launcher> internals config-drafts generate --id project.specialist --intent '{"fields":{"name":"general-kimi","tool":"kimi","credential":"fixture"}}'
```

The `project.specialist` config draft is intentionally minimal. Its JSON intent must contain a top-level `fields` object whose only draft fields are `name`, `tool`, and `credential`. For prompt content, setup changes, model/reasoning, skills, env records, system-skill policy, mailbox posture, or credential material, use the maintained `project specialist create|set` command fields directly instead of adding them to the draft intent.

For `set`, keep the maintained patch command explicit and include only the user-requested mutation fields.

## Create Inputs

Common specialist inputs:

- `--name`
- `--tool claude|codex|kimi|dsh`
- `--credential <name>`
- `--system-prompt` or `--system-prompt-file`
- `--setup <name>`; default is `default`
- `--no-unattended` only when the user explicitly wants `as_is`; do not invent this flag from preference. For Kimi TUI automation, keep the default unattended prompt mode instead of adding raw Kimi permission flags.
- `--model`
- `--reasoning-level`
- repeatable `--skill <registered-project-skill>` or `--with-skill <dir>` (registers in `.houmao/content/skills/` and binds)
- repeatable `--env-set NAME=value`
- managed system-skill policy: `--system-skill-pack <admin|agent>`, `--system-skills-mode default|extend|replace|none`, `--no-system-skills`
- layered per-tool parameters: `--tool-params JSON-OR-@PATH` (including `tool_params.permissions` and adapter-specific runtime settings)

For Codex GPT-5.6, normalized reasoning level 0 is invalid. Sol and Terra expose six ordered levels (`low`, `medium`, `high`, `xhigh`, `max`, `ultra`), and Luna exposes five through `max`. Higher values saturate at the model maximum. For Kimi, select an alias from native TOML. Positive reasoning levels index the alias's effective `support_efforts` from 1 and use its exact labels. Level 0 requires a model that permits thinking off. Leave the numeric override unset to use native defaults.

Tool-specific auth inputs:

- Claude: `--api-key`, optional `--claude-auth-token`, optional `--claude-oauth-token`, optional `--claude-config-dir`, optional `--base-url`, optional `--claude-model`
- Claude optional bootstrap state: `--claude-state-template-file`; this is optional bootstrap state and not a credential-providing method
- Codex: `--api-key`, optional `--base-url`, optional `--codex-org-id`, optional `--codex-auth-json`
- DSH: create an explicit DSH credential (`--adapter deepseek|pi-ai`, `--api-key`, `--base-url`, `--api-key-env`, `--base-url-env`) via `project credentials dsh add` and reference it with `--credential <name>`, or pass supported common `--api-key` / `--base-url` inputs when creating
- Kimi accepts `--kimi-config-toml`, optionally with `--api-key` for a matching native key reference or `--kimi-credential-json` for OAuth. Use `--kimi-code-home` to import a supported OAuth home.

## Credential Discovery During Create

Use credential discovery only for specialist creation.

When the user omits tool or credential input, first apply Specialist Create Defaulting from [../../references/common/credential-routing.md](../../references/common/credential-routing.md):

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
- DSH: [../../../houmao-credential-mgr/references/dsh-credential-kinds.md](../../../houmao-credential-mgr/references/dsh-credential-kinds.md)
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
- `--system-skill-pack <admin|agent>`, `--system-skills-mode default|extend|replace|none`, `--no-system-skills`, `--clear-system-skills`
- `--tool-params JSON-OR-@PATH`, `--clear-tool-params`

## Guardrails

- DO NOT guess the specialist name, tool lane, credential name, or auth values.
- DO NOT infer tool or credential from installed CLIs, project language, file names, vendor tool homes, or credential storage directory basenames.
- DO NOT remove and recreate a project specialist for ordinary prompt, skill, setup, credential, prompt-mode, model, reasoning-level, or env edits; use `project specialist set`.
- DO NOT use `project specialist set` for specialist rename or tool-lane changes. Ask whether to create a new specialist instead.
- DO NOT enter credential discovery for list, get, set, remove, project profile creation, or launch.
- DO NOT execute login flows or auth-generation helpers.
- DO NOT treat `auto credentials` as a literal CLI flag.
- DO NOT infer auth identity from `.houmao/` auth directory names.
- DO NOT hand-author specialist config YAML skeletons; use `internals config-drafts generate` for supported minimal specialist config authoring.
- DO NOT pass model, env, mailbox, prompt, skill, or credential material fields to `project.specialist` config drafts.
- DO NOT add raw Kimi `--auto` or `--yolo` launch flags to specialists; use prompt mode for managed automation.
