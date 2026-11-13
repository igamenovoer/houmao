# Fixture Credential Selection

## Workflow

1. **Resolve one credential route** from **Selection Routes**. Honor an explicitly named API case or native bundle.
2. **Validate only selected inputs** using the fixture helper's offline `check`; see [../commands/configure-fixtures.md](../commands/configure-fixtures.md) for setup.
3. **Discover native files only when native login is requested.** Present safe candidate metadata and require a selected source before import.
4. **Record safe provenance.** Keep the client, API case or native bundle name, env-file path/reference names, explicit model metadata, and local validation result.
5. **Report a missing input or unsupported state** without falling through to another account, wrapper, endpoint, or protocol.

If the task needs a custom descriptor or native layout, use the native planning tool to inspect the explicitly selected source against the fixture helper's supported schema, then execute the supported route or report its limitation.

## Selection Routes

| Requested Route | Inputs | Resolution |
| --- | --- | --- |
| DeepSeek / `cloud-api` | Key, selected client endpoint, explicit model; context for Kimi | Tracked `cloud-api.yaml` with process references or an explicitly selected env file |
| `self-hosted` | Explicit model and compatible endpoint; optional key; context for Kimi | Tracked `self-hosted.yaml`, or an explicitly selected descriptor declaring available protocols |
| Native login | Selected imported bundle for the client | `--auth-method native-login --auth-bundle NAME`, with an external store |
| `auto` or unspecified account | Developer clarification or read-only native discovery | Discovery does not choose an account, import it, or establish live authentication |

The two API cases need no vendor auth JSON or native login. Native selection is independent of API cases and must not receive DeepSeek env-file settings. An explicit API selection bypasses the old personal-launcher/ambient-login resolver entirely. This skill no longer prefers `claude-kimi`, `claude-yunwu`, or arbitrary wrappers; a missing selected route remains a blocker.

## API Input Precedence

Use `scripts/agents/test-fixtures/fixture.py`; do not implement another dotenv parser or provider-config generator. Explicit supported CLI values take precedence over process references, which take precedence over the selected env file. No env file loads automatically. Ask the developer to update a private file or select another source when a process override is unintended; never print the competing values.

| Client | Protocol | Endpoint Reference | Projection |
| --- | --- | --- | --- |
| Claude | Anthropic Messages | `DEEPSEEK_BASE_URL_ANTHROPIC` for cloud | Auth token, API root, and selected model aliases |
| Codex | OpenAI Responses | `DEEPSEEK_BASE_URL_OPENAI` for cloud | Run-local provider block plus private `OPENAI_API_KEY` |
| Kimi | OpenAI Chat Completions | `DEEPSEEK_BASE_URL_OPENAI` for cloud | Selected `KIMI_MODEL_*` env, including required context |

Claude expects its API root without an added trailing `/v1`; Codex and Kimi preserve a selected version/custom prefix. A Chat-only service cannot satisfy Codex's Responses requirement. Descriptor validation checks declared protocols; a live run establishes actual endpoint compatibility.

Self-hosted references are `HOUMAO_TEST_SELF_HOSTED_MODEL`, `HOUMAO_TEST_SELF_HOSTED_ANTHROPIC_BASE_URL`, `HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL`, and optional `HOUMAO_TEST_SELF_HOSTED_API_KEY`. Kimi also needs `HOUMAO_TEST_SELF_HOSTED_CONTEXT_WINDOW`. An absent self-hosted key may resolve to the documented anonymous placeholder; a cloud key must be nonempty. There is no fixed self-hosted model or port.

## Native Discovery and Import

Use read-only `discover-auth` for the selected tool's configured/default homes or explicitly bounded search roots. `import-auth` consumes an explicitly selected candidate or source, copying only supported files into the external store. Discovery never proves that a token is current.

Supported primary files are Claude `.credentials.json` with supported companion state, Codex `auth.json`, and Kimi `credentials/kimi-code.json` with matching `config.toml`. Report malformed, empty, helper/keychain-only, scoped, or custom-provider configurations according to helper diagnostics. In particular, config-backed custom Codex routing needs an explicit API case rather than a guessed native import.

Reusable bundles default to `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/auth/`. `--auth-root` or `HOUMAO_TEST_AUTH_ROOT` selects another external root. Source files and reusable bundles remain unchanged when clients write to their run-owned copies.

## Constraints

- Configure a new host from its selected inputs; do not copy this developer's `.env`, personal launchers, or credentials to it.
- Treat model/context/reasoning settings as explicit inputs. The helper defaults capabilities to `tool_use`; add thinking or image support only for a qualified model.
- Preserve already selected proxy settings when needed by the host. Never invent a fixed proxy or record proxy credentials/values in reports.
- Keep secrets in the process environment or a private file. Do not request a key in chat or pass it through `--api-key` shell arguments.
