# Generic Agent Launch Fixtures

These tracked descriptors define two API cases: `self-hosted` and `cloud-api`. Select the client (`claude`, `codex`, or `kimi`), model, mode, and launch surface independently. DeepSeek is the initial cloud configuration. There is no pinned model, local port, personal account, reasoning effort, or model context default.

Use the development helper through `pixi run python scripts/agents/test-fixtures/fixture.py`. Seed roles and setups remain in [plain-agent-def](../plain-agent-def/README.md); managed preparation creates a fresh project instead of treating that seed tree as a project overlay.

Copy required variable names from [.env.example](.env.example) into a local ignored env file. The helper reads only an explicitly selected file as literal data. Process variables take precedence over file values; explicit non-secret flags take precedence over both. It does not execute shell syntax or expand variables.

| Client | Protocol | Base URL Convention |
| --- | --- | --- |
| Claude | Anthropic Messages | Root before `/v1/messages`, for example the configured Anthropic gateway root. |
| Codex | OpenAI Responses | Prefix before `/responses`; preserve an explicitly supplied `/v1` prefix. |
| Kimi | OpenAI Chat Completions | Prefix before `/chat/completions`; preserve an explicitly supplied `/v1` prefix. |

Cloud credentials reference `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, and `DEEPSEEK_BASE_URL_OPENAI`. Supply `--model` or `HOUMAO_TEST_CLOUD_MODEL`. A cloud key is mandatory. A self-hosted server without authentication can use the explicit anonymous placeholder that the helper supplies when its optional key reference is empty.

Kimi also requires an explicit context window. Capabilities default to the minimal text/tool probe. Thinking, image support, reasoning effort, and reasoning field names must match the chosen model; they are never inherited from an earlier capture. A shared URL does not establish that a server supports both OpenAI protocols. A custom descriptor can omit unsupported protocols, and online qualification checks the selected protocol.

Native login files are optional, separately selected inputs. They are discovered and imported into an external local store; neither API case requires them. Real credentials and authenticated run homes stay outside the checkout. Historical sanitized usage captures retain their original model/version metadata and do not define launch defaults.
