# DSH Headless Setup

Edit `dsh-setup.yaml` to declare the exact selected model and its context/output capacities before launching. The empty model catalog deliberately fails validation. Houmao does not inherit a shipped model or oversized capacity fallback.

The native `deepseek` adapter requires `messages` and resolves the explicit `DEEPSEEK_BASE_URL_ANTHROPIC` and `DEEPSEEK_API_KEY` references from the selected local auth bundle. A generic route instead uses `adapter: pi-ai`, `protocol: openai-completions`, an explicit route name, and its own endpoint/key references. Endpoints must support the declared protocol. Do not place key values in this setup file.

Add model entries with `id`, `context_window`, `max_output_tokens`, and explicit `reasoning` metadata. Set `selected_model` to one declared model ID. Selected skills and MCP servers remain explicit; managed profiles disable implicit user skill roots and HMR. DSH native login and interactive Web control are outside the first headless change.

The sibling `openai-compatible` setup supplies the generic pi-ai/Chat Completions route with `OPENAI_BASE_URL` and `OPENAI_API_KEY`. Its model catalog is also deliberately empty. Create the credential with the matching explicit `--adapter` selection; both setups require an endpoint that implements the selected protocol.
