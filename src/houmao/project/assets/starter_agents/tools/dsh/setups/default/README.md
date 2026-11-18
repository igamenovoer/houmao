# DSH Headless Setup

Declare exact models in `tool-params.yaml` or a higher-priority `tool_params` layer before launching. Each model entry needs `id`, `context_window`, `max_output_tokens`, and `reasoning_efforts`. Use `false` for a model without reasoning or a map of native slots to wire values. Quote the YAML key `'off'`. Set Houmao `model.name` when the effective catalog contains several models.

The native `deepseek` route uses the Messages protocol. Match the setup's `DEEPSEEK_BASE_URL_ANTHROPIC` and `DEEPSEEK_API_KEY` references to the selected credential bundle's roles.

The sibling `openai-compatible` setup selects endpoint-only pi-ai Chat Completions with an `OPENAI_BASE_URL` endpoint role. The endpoint must accept the public `Authorization: Bearer houmao-local-no-auth` header that DSH sends. For an authenticated compatible route, set `provider.api_key_env` to the bundle's API-key role. The `provider.compat` and `models[].compat` settings accept options supported by the selected pi-ai protocol.
