# Generic Agent Launch Fixtures

These tracked descriptors define two API cases: `self-hosted` and `cloud-api`. Select the client (`claude`, `codex`, `kimi`, or `dsh`), model, mode, and launch surface independently. DSH uses `web` on the raw and manager fixture surfaces. DeepSeek is the initial cloud configuration. There is no pinned model, local port, personal account, reasoning effort, or model context default.

Use the development helper through `pixi run python scripts/agents/test-fixtures/fixture.py`. Seed roles and setups remain in [plain-agent-def](../plain-agent-def/README.md); managed preparation creates a fresh project instead of treating that seed tree as a project overlay.

Copy required variable names from [.env.example](.env.example) into a local ignored env file. The helper reads only an explicitly selected file as literal data. Process variables take precedence over file values; explicit non-secret flags take precedence over both. It does not execute shell syntax or expand variables.

DSH reads selected env files outside the checkout and ignores ambient credential and model variables. The cloud descriptor selects `deepseek/messages`. The self-hosted descriptor selects `pi-ai/openai-completions` and supports endpoint-only configuration when the selected input omits a key. Supply context window, maximum output tokens, and `reasoning_efforts` explicitly. The reasoning input is JSON `false` or a native slot-to-wire map. The `HOUMAO_TEST_*_DSH_COMPAT` reference optionally provides JSON model compatibility. Raw and managed Web preparation use the same route and private credentials. [DSH fixture workflow](../../../scripts/agents/test-fixtures/README.md#dsh-web)

| Client | Protocol | Base URL Convention |
| --- | --- | --- |
| Claude | Anthropic Messages | Root before `/v1/messages`, for example the configured Anthropic gateway root. |
| Codex | OpenAI Responses | Prefix before `/responses`; preserve an explicitly supplied `/v1` prefix. |
| Kimi | OpenAI Chat Completions | Prefix before `/chat/completions`; preserve an explicitly supplied `/v1` prefix. |
| DSH Cloud | DeepSeek Messages | Prefix before `/messages`; append `/v1` only when absent. |
| DSH Self-Hosted | Explicit pi-ai `openai-completions` | Preserve the configured prefix before `/chat/completions`. |

Cloud credentials reference `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, and `DEEPSEEK_BASE_URL_OPENAI`. Supply `--model` or `HOUMAO_TEST_CLOUD_MODEL`. A cloud key is mandatory. A self-hosted server without authentication can use the explicit anonymous placeholder that the helper supplies when its optional key reference is empty.

Kimi also requires an explicit context window. Capabilities default to the minimal text/tool probe. Thinking, image support, reasoning effort, and reasoning field names must match the chosen model; they are never inherited from an earlier capture. A shared URL does not establish that a server supports both OpenAI protocols. A custom descriptor can omit unsupported protocols, and online qualification checks the selected protocol.

Native login files are optional, separately selected inputs. They are discovered and imported into an external local store; neither API case requires them. Real credentials and authenticated run homes stay outside the checkout. Historical sanitized usage captures retain their original model/version metadata and do not define launch defaults.

## Developer Model Pool

Use the model pool to share launch settings across instructional suites and local fixture runs. Start with [model-pool.example.toml](model-pool.example.toml). For a new pool, copy the template to the external fixture data directory with mode `0600`.

```bash
pool="${XDG_DATA_HOME:-$HOME/.local/share}/houmao/test-fixtures/model-pool.toml"
mkdir -p "$(dirname "$pool")"
install -m 600 tests/fixtures/agent-launch/model-pool.example.toml "$pool"
```

Keep the live pool outside the checkout and owned by your user. Set `HOUMAO_TEST_MODEL_POOL` or pass `--model-pool` to select another external file. The helper rejects symlinked pool files. File references relative to the pool resolve from its parent directory.

Give each `[models.<key>]` entry a client and model ID. API entries select a `case` and provide a base URL or an external `env_file` with the descriptor's endpoint reference. Cloud entries require an external `env_file` for credentials. Native-login entries select `auth_method = "native-login"` and an imported `auth_bundle` name. Store credential values in those external inputs. Set `supported_modes` if the entry should support only a subset of its client's modes.

List available keys with `pixi run python scripts/agents/test-fixtures/fixture.py list-models`. Use `--pool-key <key>` to select one directly, or `--pool-slot <slot>` to check `HOUMAO_TEST_MODEL_<SLOT>` before `HOUMAO_TEST_MODEL`. [Fixture CLI instructions](../../../scripts/agents/test-fixtures/README.md)
