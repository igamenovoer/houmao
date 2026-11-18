# Test-Agent Fixture Tools

Run this development utility through `pixi run python scripts/agents/test-fixtures/fixture.py`. It consumes the tracked [API case descriptors](../../../tests/fixtures/agent-launch/README.md) and keeps live credentials outside the checkout.

## Discover and Import Native Login State

```bash
pixi run python scripts/agents/test-fixtures/fixture.py discover-auth --client codex
pixi run python scripts/agents/test-fixtures/fixture.py discover-auth --client claude --no-defaults --search-root /selected/configs
pixi run python scripts/agents/test-fixtures/fixture.py import-auth --client codex --source /selected/home/auth.json --name work
```

Discovery reports candidate IDs, paths, supported companion filenames, and local importability. It does not authenticate, refresh tokens, run credential helpers, or print file contents. Default discovery checks only the selected tool's configured and standard homes. Explicit recursive roots are bounded; history, sessions, caches, and escaping symlinks are excluded. Import requires `--source` or `--candidate`; multiple accounts never cause an implicit choice.

| Client | Primary File | Optional Companion |
| --- | --- | --- |
| Claude | `.credentials.json` | Supported `.claude.json` state; the default home may use its parent-level state file. |
| Codex | `auth.json` | Only supported auth content is copied; unrelated personal config is excluded. |
| Kimi | `credentials/kimi-code.json` | Matching `config.toml`. |

An import copies supported files byte-for-byte, preserves the original source, and publishes a user-private bundle. `--replace` is required to replace an existing name. Empty/malformed credentials, helper-only/keychain-only auth, and unsupported scoped OAuth files are not treated as usable saved login state. Local validation does not prove a credential is current.

Reusable auth defaults to `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/auth/`; override it with `--auth-root` or `HOUMAO_TEST_AUTH_ROOT`. Private runs default to `${XDG_STATE_HOME:-~/.local/state}/houmao/test-fixtures/runs/`, with `--run-root` or `HOUMAO_TEST_RUN_ROOT` overrides. Both must resolve outside the checkout, including symlinked paths.

The generic API cases require no imported native JSON. DeepSeek uses local key/endpoint references. Native login is a separately selected auth method and never becomes an API-key fallback.

## Check API Configuration

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check --case cloud-api --client codex --model MODEL --env-file .env
pixi run python scripts/agents/test-fixtures/fixture.py check --case self-hosted --client kimi --model MODEL --context-window TOKENS
```

Replace `MODEL` and `TOKENS` with explicit values for the selected model. Offline checks validate selected inputs and print a secret-free description. They do not claim that a remote endpoint or saved login works. No command accepts a resolved key as a flag.

## Prepare and Launch

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client claude --model MODEL --mode headless --surface manager --env-file .env
pixi run python scripts/agents/test-fixtures/fixture.py launch --run-dir /external/prepared-run --prompt 'Reply exactly OK. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir /external/prepared-run --prompt 'Reply exactly DONE. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run --live
pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir /external/prepared-run
```

Use the `run_dir` returned by `prepare`. Preparation performs local validation and project construction without contacting the model endpoint. Each invocation creates a unique run with private `assets/`, `home/`, `workdir/`, `private-env.json`, and `run.json`. Launch records the actual owned runtime path, including project-overlay runtime placement. Managed preparation uses current project/tool/credential/specialist behavior. Secret-bearing credential commands execute in-process, so keys do not become OS arguments. Generated setups contain routing and model metadata; private credential files hold keys.

`--surface raw` starts the installed client for native-format qualification. Raw headless launch requires a prompt, writes `raw-turn-N.jsonl`/`.stderr` privately, and captures an exact provider session ID for later `prompt` calls. Terminal TUI clients use an owned tmux session. `--surface manager` uses `houmao-mgr project agents launch` with a project specialist. Headless and DSH Web prompts use semantic control; terminal TUI prompts send literal text and Enter separately. Automation defaults to `--prompt-mode unattended`; select `--prompt-mode as_is` deliberately for human interaction tests. Kimi prompt mode omits `--auto`, because that flag is incompatible with prompt mode.

`--surface passive-server` supports headless birth only. Start `houmao-passive-server` with external runtime/registry roots, then pass its local authority URL with `launch --passive-url http://127.0.0.1:PORT`. The helper builds the selected brain and uses `/houmao/agents/headless/launches` and `/houmao/agents/{id}/turns`. The server runs on the same dev box and must be able to read those private paths. TUI birth uses the manager.

For native login, select `prepare --client claude --auth-method native-login --auth-bundle work` (or Codex/Kimi). This path neither reads the API env file nor injects DeepSeek settings. Native source/store files are copied into the run before client launch. Imported Codex auth tied to a custom config-backed provider is reported as unsupported; configure that provider through an explicit API case instead.

`check` stays offline unless `--live` is explicit. Its prerequisite list names missing executables, tmux, or private state. Live managed checks query the captured authority's public usage route; they do not send a billable prompt. `run.json` and `report.json` retain sanitized state and authoritative managed IDs after failure. Native output stays private. Cleanup uses only captured agent IDs or owned tmux session names and preserves evidence. A failed cleanup remains explicit and requires scoped follow-up.

For direct follow-up, use the recorded `agent_id` with `houmao-mgr agents single --agent-id ID state`, `gateway status`, or `stop`. Set `HOUMAO_GLOBAL_REGISTRY_DIR` to the run's `registry/`, `HOUMAO_GLOBAL_RUNTIME_DIR` to the returned identity's `runtime_root`, and `HOUMAO_PROJECT_OVERLAY_DIR` to the run's `workdir/.houmao/`. The helper's `prompt`, `check`, and `stop` commands select those roots automatically. It never mutates the shared tmux server environment or stops unrelated agents.

## Model Metadata

Claude uses Anthropic Messages, Codex uses Responses, and Kimi uses Chat Completions. Supply the API root for Claude, without an added trailing `/v1`; the client appends `/v1/messages`. Codex and Kimi preserve a supplied version/custom prefix. A descriptor must declare the selected protocol; a Chat-only server cannot qualify Codex.

Model selection is always explicit for API cases. Kimi additionally requires `--context-window TOKENS` or the case's context reference. Capabilities default to `tool_use`; opt into `thinking` or `image_in` only for a qualified model. Optional `--reasoning-key`, `--reasoning-effort`, `--context-window`, and `--capabilities` project selected values without inheriting historical model assumptions. Codex renders an explicit model/provider and optional context/effort; the generic tracked template requires a selected `OPENAI_BASE_URL` at build time. Empty or conflicting routing fails before launch.

## DSH ACP and Web

DSH uses `--client dsh --mode headless` for ACP on `raw`, `manager`, and `passive-server` surfaces. Its `--mode tui` posture selects the native Web surface on `raw` and `manager`. Web qualification is tracked separately in the [compatibility reference](../../../docs/reference/run-phase/dsh-web.md) and [scenario map](../../../docs/reference/run-phase/dsh-web-acceptance.md); a passing ACP run does not qualify Web. Native-login selection is rejected before any private run is allocated. Install and explicitly select the qualified executable described in [DSH preparation](../../../tools/dsh/README.md); product launch never installs a runtime.

Cloud configuration defaults to the native DeepSeek Messages adapter. Self-hosted configuration defaults to pi-ai `openai-completions`. Both require an exact model, context window, maximum output tokens, and declared reasoning support. Use `--dsh-reasoning false` for a model without reasoning or a JSON slot-to-wire map such as `'{"off":"none","low":"low","high":"high"}'` for supported efforts. Use `--dsh-compat '{"supports_developer_role":false}'` to set model compatibility on OpenAI Completions. Case descriptors can name environment references for capacities, reasoning, and compatibility. Use `--dsh-protocol` to select a protocol supported by the descriptor's adapter. DeepSeek Messages preserves a trailing `/v1` and appends it when absent. Supply the base URL before `/messages`.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case cloud-api --client dsh --env-file /external/selected-deepseek.env
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case cloud-api --client dsh --mode headless --surface raw \
  --env-file /external/selected-deepseek.env \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh
```

Cloud DSH reads credentials from the explicitly selected external env file. Self-hosted OpenAI Completions accepts explicit endpoint and model flags without a key. That path writes `api_key_env: null` and uses `Authorization: Bearer houmao-local-no-auth` in native requests. Select an endpoint that accepts that public placeholder. Both surfaces ignore ambient credential and model variables. The generated setup records credential names, and every agent owns its DSH home, shared-agent root, selected skills, journal, and invocation artifacts.

Raw DSH calls use the packaged ACP driver with create/exact-resume/prompt/close, rather than the one-shot CLI. `raw-turns/turn-N/provider-stdout.jsonl` retains native ACP frames separately from `raw-turn-N.jsonl` driver events. Continuation preserves the captured exact native ID and fails rather than selecting another session. `interrupt --run-dir PATH` sends native cancellation through the captured managed authority or the birth-verified raw driver; a timeout or interruption never resends a prompt.

For Web preparation, use the same explicit case and env file with `--mode tui --surface manager` (or `raw`). The host stays headless at the operating-system level: it binds loopback and does not open a browser automatically. Select `--prompt-mode as_is` only when testing human questions or native approval behavior; normal automated browser checks retain unattended defaults.

After launch, explicitly request `fixture.py browser-connection --run-dir /external/prepared-run` to create the private browser descriptor. This command returns a path and token-free identity, never the sign-in token itself. A deliberately chosen local browser consumer reads the descriptor; the maintained Bun browser qualification uses the same mechanism.

Browser sign-in uses a private local URL obtained from the run's connection mechanism. Keep the token and browser cookies outside public summaries. The native root token exchange redirects to a clean origin. Select and verify the exact native session in the sidebar before submitting browser input; there is no supported `?sessionId=` shortcut. The programmatic adapter keeps its own API Peer with `interactions=none` and remains bound to its recorded session when the browser navigates elsewhere.

Browser and API clients can alternate work on that same native session. A browser draft is local until submitted. Ordinary API delivery uses `ready_only`; busy, queued, maintenance, or question-blocked work refuses immediately. Explicit operator queueing requires its own policy selection. After a lost response, inspect the original receipt and state; reconnecting does not authorize resending. `interrupt` targets captured native activity and `stop` terminates only the owned host.

Every helper-owned tmux command explicitly names a unique `-L` server. A private run-owned PATH shim applies the same target to managed runtime subprocesses, clearing inherited `TMUX` and `TMUX_PANE`. Cleanup stops only captured sessions/agents within that server. Raw headless ACP requires no tmux server. A separately started passive server must use its own explicit isolated tmux target; the client cannot change a pre-existing server's process environment.

## Qualification

Default automated tests use synthetic credentials and harmless clients. Live qualification is explicit and requires working credentials, installed clients, declared compatible protocols, and a qualified model. Record exact versions, actual model, completed/resumed prompts, direct TUI interaction, and available public usage. Report rejected credentials or unavailable self-hosted/native prerequisites as gaps. Never label an unexecuted lane as passed. Historical captures and completed change-local wrappers retain their factual model names; maintained launch paths use this helper.
