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
pixi run python scripts/agents/test-fixtures/fixture.py check --case cloud-api --client codex --model MODEL --env-file /external/selected-deepseek.env
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

## Codex App-Server Service

Use `--client codex --mode service --surface manager` with Codex CLI `0.169.0` and a Responses endpoint. The manager fixture opens one app-server and keeps the native thread across `prompt` calls.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client codex --mode service --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --executable /selected/codex-0.169.0
```

Use the prepared directory with `launch`, `prompt`, and `stop`. [Codex App-Server Service](../../../docs/reference/run-phase/codex-app-server-service.md).

## Kimi Web

Select `--client kimi --mode web --surface manager` and an explicit executable for Kimi Code `2.6.0`. The fixture supports `browser-connection` for an explicitly selected browser runner. The command creates a private credential file and returns its path with the safe identity. [Kimi Web](../../../docs/reference/run-phase/kimi-web.md).

## Kimi ACP Service

The manager fixture supports `--client kimi --mode service` on Kimi Code `2.6.0`. It keeps the native ACP session alive across calls and matches the result and usage to each managed request. Use `launch` once, then run `prompt` for each follow-up.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client kimi --mode service --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --executable /selected/kimi-2.6.0
```

The raw fixture surface supports one-shot CLI calls and owned TUI entry. Use the captured service identity and `stop` to clean up a manager service fixture. [Kimi Code ACP Service](../../../docs/reference/run-phase/kimi-acp-service.md).

## DSH Headless

Use `--client dsh --mode headless` to select `dsh_headless` on the raw, manager, or passive-server fixture surface. Each prompt invokes the native `headless` profile with its launcher patches before `--json`. Raw fixtures send literal prompt bytes through stdin and record the opening native session identity and terminal reason from JSON lines. Continuation creates a new worker and passes the exact captured `--session-id` in the original workspace. The manager and passive server preserve their managed identity across workers.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client dsh --mode headless --surface raw \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","high":"high"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh
```

Run `launch` with a prompt and `prompt` for a follow-up using the prepared run directory. Use `--case cloud-api --env-file /external/selected-deepseek.env` for an explicitly selected DeepSeek Messages route. The external file supplies the endpoint, credential, model, and declared capacities under the fixture's existing input names. [DSH headless control](../../../docs/reference/run-phase/dsh-headless.md), [selected inputs](../../../tests/fixtures/agent-launch/README.md).

## DSH ACP Service

Use `--client dsh --mode service --surface manager` with the same model, endpoint, compatibility metadata, and qualified executable as the headless fixture. Launch once and issue two `prompt` commands against the prepared run directory. The fixture waits for each gateway operation's own usage record. Use `stop` to stop the owned service and its private supervisor. [DSH ACP service](../../../docs/reference/run-phase/dsh-service.md).

## DSH Web

Use `--client dsh --mode web` with `--surface raw` or `--surface manager`. The helper reports unavailable modes before creating a run. Use a qualified installed executable. [DSH preparation](../../../tools/dsh/README.md), [Web qualification scenarios](../../../docs/reference/run-phase/dsh-web-acceptance.md).

Cloud configuration defaults to the native DeepSeek Messages adapter. Self-hosted configuration defaults to pi-ai `openai-completions`. Both require an exact model, context window, maximum output tokens, and declared reasoning support. Use `--dsh-reasoning false` for a model without reasoning or a JSON slot-to-wire map such as `'{"off":"none","low":"low","high":"high"}'` for supported efforts. Use `--dsh-compat '{"supports_developer_role":false}'` to set model compatibility on OpenAI Completions. Case descriptors can name environment references for capacities, reasoning, and compatibility. Use `--dsh-protocol` to select a protocol supported by the descriptor's adapter. DeepSeek Messages preserves a trailing `/v1` and appends it when absent. Supply the base URL before `/messages`.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case cloud-api --client dsh --env-file /external/selected-deepseek.env
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case cloud-api --client dsh --mode web --surface raw \
  --env-file /external/selected-deepseek.env \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh
```

Cloud DSH reads credentials from the explicitly selected external env file. Self-hosted OpenAI Completions accepts explicit endpoint and model flags without a key. That path writes `api_key_env: null` and uses `Authorization: Bearer houmao-local-no-auth` in native requests. Select an endpoint that accepts that public placeholder. Both surfaces ignore ambient credential and model variables. The generated setup records credential names, and every agent owns its DSH home, shared-agent root, selected skills, journal, and invocation artifacts.

The Web host binds loopback and defers opening a browser to the operator. Select `--prompt-mode as_is` only when testing human questions or native approval behavior; normal automated browser checks retain unattended defaults.

After launch, explicitly request `fixture.py browser-connection --run-dir /external/prepared-run` to create the private browser descriptor. This command returns a path and token-free identity, never the sign-in token itself. A deliberately chosen local browser consumer reads the descriptor; the maintained Bun browser qualification uses the same mechanism.

Browser sign-in uses a private local URL obtained from the run's connection mechanism. Keep the token and browser cookies outside public summaries. The native root token exchange redirects to a clean origin. Select and verify the exact native session in the sidebar before submitting browser input; there is no supported `?sessionId=` shortcut. The programmatic adapter keeps its own API Peer with `interactions=none` and remains bound to its recorded session when the browser navigates elsewhere.

Browser and API clients can alternate work on that same native session. A browser draft is local until submitted. Ordinary API delivery uses `ready_only`; busy, queued, maintenance, or question-blocked work refuses immediately. Explicit operator queueing requires its own policy selection. After a lost response, inspect the original receipt and state; reconnecting does not authorize resending. `interrupt` targets captured native activity and `stop` terminates only the owned host.

Each supervised fixture has a unique `tmux -S` socket. The manager captures that exact socket before launch. The run's PATH shim also selects that server and clears inherited `TMUX` and `TMUX_PANE`. Cleanup stops only captured identities on the fixture's server. Raw one-shot CLI calls run without tmux. Start a separately owned passive server with its own explicit isolated tmux target.

## Qualification

Default automated tests use synthetic credentials and harmless clients. Live qualification is explicit and requires working credentials, installed clients, declared compatible protocols, and a qualified model. Reports include the selected case, model, protocol, mode, backend, and the native build version when the executable reports it. Interactive runs include the verified terminal or browser surface. Record completed and resumed prompts, direct human-interface interaction, and available public usage. Report rejected credentials or unavailable self-hosted/native prerequisites as gaps. Never label an unexecuted lane as passed. Historical captures and completed change-local wrappers retain their factual model names; maintained launch paths use this helper.
