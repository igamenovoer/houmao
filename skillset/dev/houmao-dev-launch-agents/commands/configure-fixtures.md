# Configure Local Test Fixtures

## Workflow

1. **Select the client and source** through [../references/credential-resolution.md](../references/credential-resolution.md): cloud API, self-hosted API, or explicitly selected native login.
2. **Check local prerequisites** in **Fresh Host Setup**. Resolve the checkout and selected executable without launching an agent.
3. **Prepare the selected private settings** using **DeepSeek Setup**, **Self-Hosted Setup**, or **Native Login Setup**. Preserve existing files and keep source credentials external.
4. **Run the offline configuration check** and report missing fields or unsupported combinations without contacting a model endpoint.
5. **Return setup evidence and a launch handoff** with the selected client, case/auth method, model metadata, private input path, validation result, and requested next routine. Do not launch for a setup-only request.

If local settings do not match the examples, use the native planning tool to map the selected inputs to the tracked fixture descriptor and helper options, then execute that plan without guessing credentials or capabilities.

## Fresh Host Setup

Run from the checkout. Require Pixi and the selected client CLI on `PATH`, then use `pixi install` when repository dependencies are not installed. Managed preparation also needs Git; TUI and managed execution need tmux. Resolve `claude`, `codex`, `kimi`, or the explicitly selected qualified `dsh`; when only `kimi-code` exists, record that path and pass it through `prepare --executable PATH` later. Report a missing client; global client installation and interactive login are separate tasks.

Use the repository's [fixture helper guide](../../../../scripts/agents/test-fixtures/README.md) and [case descriptors](../../../../tests/fixtures/agent-launch/README.md) as the configuration contract. No local model service is required for `cloud-api`.

## DeepSeek Setup

Choose an external private env file, for example `~/.config/houmao/test-fixtures/deepseek.env`. If it does not exist, create its parent with user-only permissions and copy the tracked secret-free example there. Do not overwrite an existing developer file:

```bash
install -d -m 700 "$HOME/.config/houmao/test-fixtures"
# Run this copy only after confirming the destination is absent.
cp tests/fixtures/agent-launch/.env.example "$HOME/.config/houmao/test-fixtures/deepseek.env"
chmod 600 "$HOME/.config/houmao/test-fixtures/deepseek.env"
```

Have the developer fill the key locally, or use an already selected process reference. The file needs these settings for the selected clients; these are file contents, not shell commands:

```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL_ANTHROPIC=https://api.deepseek.com/anthropic
DEEPSEEK_BASE_URL_OPENAI=https://api.deepseek.com
HOUMAO_TEST_CLOUD_MODEL=
HOUMAO_TEST_CLOUD_CONTEXT_WINDOW=
HOUMAO_TEST_CLOUD_CAPABILITIES=tool_use
```

The key and model must be nonempty before checking. Claude uses the Anthropic reference; Codex and Kimi use the OpenAI reference. Context is required for Kimi and optional for the other clients. Set it to the selected model's supported context, not a value copied from another model. API setup requires no native auth JSON.

Run the selected client check, replacing `claude` with `codex` or `kimi` as requested:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case cloud-api --client claude \
  --env-file "$HOME/.config/houmao/test-fixtures/deepseek.env"
```

The [2026-11-13 qualification](../../../../openspec/changes/archive/2026-11-13-refresh-test-agent-fixtures/tests/qualification.md) used `deepseek-flash`, context `1048576`, Codex effort `low`, and Kimi reasoning key `reasoning_content`. This is a recorded tested combination, not an automatic model default. Use it when selected by the developer or when model selection is delegated; use explicit overrides for another model. Generic fixtures must not inherit those model-specific settings blindly.

## Self-Hosted Setup

For DSH, select the pinned runtime through [the development preparation guide](../../../../tools/dsh/README.md). The cloud route uses native Messages, while the self-hosted route explicitly uses pi-ai Chat Completions. Add the selected case's `MAX_OUTPUT_TOKENS` and `DSH_REASONING` references to the external env file, alongside its model and context. Reasoning must be JSON `false` or a qualified preset mapping. DSH ignores ambient credentials and requires `--env-file`; no local model or auth JSON is needed for the cloud route. Select `headless` for ACP or raw/manager `tui` for Web. Native-login selection remains rejected.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case cloud-api --client dsh --env-file /external/selected-deepseek.env
```

Select `self-hosted` with the model, endpoint references, and Kimi context described in the shared credential reference. The endpoint must offer the client's protocol. Use a custom versioned descriptor when only some protocols are available; do not insert a translation proxy or assume that a Chat Completions server supports Responses.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case self-hosted --client kimi \
  --env-file /external/selected-self-hosted.env
```

No fixed server, port, model name, reasoning effort, or image capability is implied.

## Native Login Setup

Use native login only when requested. Show candidate IDs, file paths, supported filenames, and importability, never auth content. Import after a source or candidate and bundle name have been selected:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py discover-auth --client codex
pixi run python scripts/agents/test-fixtures/fixture.py import-auth \
  --client codex --source /selected/native-home/auth.json --name work
```

Apply `--auth-root` for an explicit external store and `--replace` only for explicitly requested replacement. An unavailable/expired native login is not a reason to use DeepSeek automatically. The helper validates native bundle identity during `prepare`; an optional vendor model follows the selected provider.

## Output Contract

Return `configured`, `incomplete`, or `blocked` with the selected client and route, missing prerequisite names, private source path/reference names, explicit model metadata, and offline check result. A setup result does not claim a working remote credential or a successful model response. Record the next launch surface/mode only when selected. Never include resolved keys or native JSON.
