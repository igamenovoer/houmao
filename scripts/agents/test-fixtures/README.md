# Test-Agent Fixture Tools

Run this development utility through `pixi run python scripts/agents/test-fixtures/fixture.py`. It consumes the tracked [API case descriptors](../../../tests/fixtures/agent-launch/README.md) and keeps reusable live credentials outside the checkout.

## Select Models for Instructional Tests

Copy [the example pool](../../../tests/fixtures/agent-launch/model-pool.example.toml) to `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/model-pool.toml`, set its permissions to `0600`, and customize the entries for your machine. Keep API keys in separate external env files and reference imported native-login bundles by name. Use `HOUMAO_TEST_MODEL_POOL` or `--model-pool PATH` to select another external pool file.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py list-models
export HOUMAO_TEST_MODEL=local_dsh
pixi run python scripts/agents/test-fixtures/fixture.py check --pool-slot lead --mode web --surface manager
pixi run python scripts/agents/test-fixtures/fixture.py prepare --pool-slot lead --mode web --surface manager
```

Set `HOUMAO_TEST_MODEL_<SLOT>` to override a single agent slot. For example, `HOUMAO_TEST_MODEL_LEAD` overrides the shared key for `lead`. The fixture converts runs of punctuation and whitespace in slot names to underscores, trims leading and trailing underscores, and uppercases the result. Use `--pool-key KEY` to select an entry directly. A missing or invalid key reports the available keys.

Pair pool selection with `--mode` and `--surface` to validate the required run mode. Pool selection supplies the case, client, routing, and native model metadata, so omit those direct flags. `--executable` and `--reasoning-level` can override the entry for preparation. The selected `pool_key` and, when applicable, `pool_slot` appear in the check output and `run.json`.

Add `--live` to a pool-backed check to probe the API's models route with the selected credentials. A reachable endpoint can report that the route is unavailable. Native-login checks validate the local import, with credential acceptance verified at launch.

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

Reusable auth defaults to `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/auth/`; override it with `--auth-root` or `HOUMAO_TEST_AUTH_ROOT`. Private runs default to `${XDG_STATE_HOME:-~/.local/state}/houmao/test-fixtures/runs/`, with `--run-root` or `HOUMAO_TEST_RUN_ROOT` overrides. Auth roots must resolve outside the checkout. Run roots may instead resolve to a purpose-specific subdirectory of the checkout's Git-ignored `tmp/` tree; the bare `tmp/` root and other checkout paths remain invalid. All private directories retain owner-only permissions, and gateway access paths retain no-follow traversal.

The generic API cases require no imported native JSON. DeepSeek uses local key/endpoint references. Native login is a separately selected auth method and never becomes an API-key fallback.

## Check API Configuration

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check --case cloud-api --client codex --model MODEL --env-file /external/selected-deepseek.env
pixi run python scripts/agents/test-fixtures/fixture.py check --case self-hosted --client kimi --model MODEL --context-window TOKENS
```

Replace `MODEL` and `TOKENS` with explicit values for the selected model. Offline checks validate selected inputs and print a secret-free description. They do not claim that a remote endpoint or saved login works. No command accepts a resolved key as a flag.

## Prepare and Launch

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client claude --model MODEL --mode headless --surface manager --env-file /external/selected-deepseek.env
pixi run python scripts/agents/test-fixtures/fixture.py launch --run-dir /external/prepared-run --prompt 'Reply exactly OK. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir /external/prepared-run --prompt 'Reply exactly DONE. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run --live
pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir /external/prepared-run
```

Use the `run_dir` returned by `prepare`. Preparation performs local validation and project construction without contacting the model endpoint. Each invocation creates a unique run with private `assets/`, `home/`, `workdir/`, `private-env.json`, and `run.json`. Launch records the actual owned runtime path, including project-overlay runtime placement. Managed preparation uses current project/tool/credential/specialist behavior. Secret-bearing credential commands execute in-process, so keys do not become OS arguments. Generated setups contain routing and model metadata; private credential files hold keys.

`--surface raw` starts the installed client for native-format qualification. Raw headless launch requires a prompt, writes `raw-turn-N.jsonl`/`.stderr` privately, and captures an exact provider session ID for later `prompt` calls. Terminal TUI clients use an owned tmux session. `--surface manager` uses `houmao-mgr project agents launch` with a generated launch profile. Headless, DSH Web, and managed Hermes TUI prompts use semantic control. Other terminal TUI prompts send literal text and Enter separately. Automation defaults to `--prompt-mode unattended`. Select `--prompt-mode as_is` deliberately for human interaction tests. Kimi prompt mode omits `--auto`, because that flag is incompatible with prompt mode.

Manager launches install the managed `agent` system-skill pack by default. For isolation tests that need a minimal runtime home, add the manager-only `--no-system-skills` option to `prepare`. Use `check` with the same case arguments to preview the policy without launching. The prepared run records `configuration.system_skill_policy` in `run.json` as `default` or `none`.

`--surface passive-server` supports headless birth only. Start `houmao-passive-server` with external runtime/registry roots, then pass its local authority URL with `launch --passive-url http://127.0.0.1:PORT`. The helper builds the selected brain and uses `/houmao/agents/headless/launches` and `/houmao/agents/{id}/turns`. The server runs on the same dev box and must be able to read those private paths. TUI birth uses the manager.

For native login, select `prepare --client claude --auth-method native-login --auth-bundle work` (or Codex/Kimi). This path neither reads the API env file nor injects DeepSeek settings. Native source/store files are copied into the run before client launch. Imported Codex auth tied to a custom config-backed provider is reported as unsupported; configure that provider through an explicit API case instead.

`check` stays offline unless `--live` is explicit. Its prerequisite list names missing executables, tmux, or private state. Live managed checks query the captured authority's public usage route; they do not send a billable prompt. `run.json` and `report.json` retain sanitized state and authoritative managed IDs after failure. Native output stays private. Cleanup uses only captured agent IDs or owned tmux session names and preserves evidence. A failed cleanup remains explicit and requires scoped follow-up.

Manager-backed `prompt` and `stop` verify the captured runtime in the run's own registry. If `houmao-mgr agents single relaunch` activates a newer generation of that same runtime, the fixture refreshes its saved state before acting. A second `stop` succeeds once the fixture confirms that runtime is stopped. Missing or changed ownership produces an error and leaves the recorded identity available for follow-up.

When a manager command exits with an error, the fixture reports `manager_exit_code` and, when saved, `diagnostic_path` in its stderr JSON. The path points to a redacted, owner-private diagnostic in the run directory. If the initial prompt fails after launch, `report.json` still records the launched identity and cleanup outcome. A cleanup error can add a separate `cleanup_diagnostic_path`.

For direct follow-up, use the recorded `agent_id` with `houmao-mgr agents single --agent-id ID state`, `gateway status`, or `stop`. Set `HOUMAO_GLOBAL_REGISTRY_DIR` to the run's `registry/`, `HOUMAO_GLOBAL_RUNTIME_DIR` to the returned identity's `runtime_root`, and `HOUMAO_PROJECT_OVERLAY_DIR` to the run's `workdir/.houmao/`. The helper's `prompt`, `check`, and `stop` commands select those roots automatically. It never mutates the shared tmux server environment or stops unrelated agents.

## Model Metadata

Claude uses Anthropic Messages, Codex uses Responses, and Kimi uses Chat Completions. Supply the API root for Claude, without an added trailing `/v1`; the client appends `/v1/messages`. Codex and Kimi preserve a supplied version/custom prefix. A descriptor must declare the selected protocol; a Chat-only server cannot qualify Codex.

Model selection is always explicit for API cases. Kimi additionally requires `--context-window TOKENS` or the case's context reference. Capabilities default to `tool_use`; opt into `thinking` or `image_in` only for a qualified model. Optional `--reasoning-key`, `--reasoning-effort`, `--context-window`, and `--capabilities` project selected values without inheriting historical model assumptions. Codex renders an explicit model/provider and optional context/effort; the generic tracked template requires a selected `OPENAI_BASE_URL` at build time. Empty or conflicting routing fails before launch.

Kimi API fixtures put their provider and model settings in a private credential `config.toml`. Supply each native effort label using a separate `--support-effort LABEL` in the model's declared order. `--reasoning-effort LABEL` sets the native default. With `--surface manager`, `--reasoning-level N` creates a launch profile that selects an effort by its one-based position. Prepare older Kimi env-model fixtures again to generate a native catalog.

Manager fixtures accept `--reasoning-level N` during preparation for models with a supported preset catalog. The level applies at launch through the `fixture-agent` profile. For DSH, level 0 selects a declared `off` slot and positive levels select the declared thinking slots in escalation order. For example, with `off`, `low`, `medium`, and `xhigh` declared, level 3 selects `xhigh`. Preparation rejects unavailable levels before creating run state.

## Codex App-Server Service

Use `--client codex --mode service --surface manager` with Codex CLI 0.169.0 or later and a Responses endpoint. The manager fixture opens one app-server and keeps the native thread across `prompt` calls.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client codex --mode service --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --executable /selected/bin/codex
```

Use the prepared directory with `launch`, `prompt`, and `stop`. [Codex App-Server Service](../../../docs/reference/run-phase/codex-app-server-service.md).

## Kimi Web

Select `--client kimi --mode web --surface manager` and an explicit executable for Kimi Code 2.6.0 or later. The fixture supports `browser-connection` for an explicitly selected browser runner. The command creates a private credential file and returns its path with the safe identity. [Kimi Web](../../../docs/reference/run-phase/kimi-web.md)

## Kimi ACP Service

Use `--client kimi --mode service` with Kimi Code 2.6.0 or later. The manager fixture keeps the native ACP session alive across calls and matches the result and available usage to each managed request. Use `launch` once, then run `prompt` for each follow-up.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client kimi --mode service --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --executable /selected/bin/kimi
```

The raw fixture surface supports one-shot CLI calls and owned TUI entry. Use the captured service identity and `stop` to clean up a manager service fixture. [Kimi Code ACP Service](../../../docs/reference/run-phase/kimi-acp-service.md).

## DSH Headless

Use `--client dsh --mode headless` to select `dsh_headless` on the raw, manager, or passive-server fixture surface. Each prompt invokes the native `headless` profile with its launcher patches before `--json`. Raw fixtures send literal prompt bytes through stdin and record the opening native session identity and terminal reason from JSON lines. Continuation creates a new worker and passes the exact captured `--session-id` in the original workspace. The manager and passive server preserve their managed identity across workers.

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client dsh --mode headless --surface raw \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable /selected/qualified-runtime/node_modules/.bin/dsh
```

Run `launch` with a prompt and `prompt` for a follow-up using the prepared run directory. Use `--case cloud-api --env-file /external/selected-deepseek.env` for an explicitly selected DeepSeek Messages route. The external file supplies the endpoint, credential, model, and declared capacities under the fixture's existing input names. [DSH headless control](../../../docs/reference/run-phase/dsh-headless.md), [selected inputs](../../../tests/fixtures/agent-launch/README.md).

## DSH ACP Service

Use `--client dsh --mode service --surface manager` with the same model, endpoint, compatibility metadata, and qualified executable as the headless fixture. Launch once and issue two `prompt` commands against the prepared run directory. The fixture waits for each gateway operation's own usage record. Use `stop` to stop the owned service and its private supervisor. [DSH ACP service](../../../docs/reference/run-phase/dsh-service.md).

## DSH Web

Use `--client dsh --mode web` with `--surface raw` or `--surface manager`. The helper reports unavailable modes before creating a run. Use a qualified installed executable. [DSH preparation](../../../tools/dsh/README.md), [Web qualification scenarios](../../../docs/reference/run-phase/dsh-web-acceptance.md).

Cloud configuration defaults to the native DeepSeek Messages adapter. Self-hosted configuration defaults to pi-ai `openai-completions`. Both require an exact model, context window, maximum output tokens, and declared reasoning support. Use `--dsh-reasoning false` for a model without reasoning or a JSON slot-to-wire map such as `'{"off":"none","low":"low","xhigh":"xhigh"}'` for supported efforts. Use `--dsh-compat '{"supports_developer_role":false}'` to set model compatibility on OpenAI Completions. Case descriptors can name environment references for capacities, reasoning, and compatibility. Use `--dsh-protocol` to select a protocol supported by the descriptor's adapter. DeepSeek Messages preserves a trailing `/v1` and appends it when absent. Supply the base URL before `/messages`.

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

Local managed fixtures and raw TUI or Web fixtures use the execution owner's shared Houmao tmux server by default. Run `fixture.py prepare --tmux-server new` to give a local fixture a private server. Automated tests that use tmux select an isolated server explicitly. Launch records the concrete socket, and follow-up ignores the caller's `TMUX` and `TMUX_PANE`. Cleanup stops only the run's captured agent or verified session. Raw headless calls run directly. Passive launches use the socket selected by the addressed passive server.

## Hermes

Hermes fixtures use explicit OpenAI-compatible Chat Completions inputs. Select `--case self-hosted` or `--case cloud-api` and an explicit credential env file or model-pool key. Choose `--mode service` for persistent ACP, `--mode headless` for one-shot JSONL, or `--mode tui` for Ink. Tmux-backed Hermes fixtures use isolated tmux servers.

Managed runs require `--hermes-owner-root` or `HOUMAO_TEST_HERMES_OWNER_ROOT` to select a private, prepared stock installation under the repository's ignored `tmp/` tree. Prepare the root once using the owner setup guide. The fixture uses one isolated Houmao registry and runtime in `<owner-root>/fixture-owner` across projects. Each run still owns its workspace, named native profile, project link, and tmux socket. The raw surface resolves stock `hermes` on PATH and uses a standalone fixture home. [Hermes Owner Setup](../../../docs/reference/run-phase/hermes-owner-setup.md)

Set `--reasoning-effort xhigh` to select an exact native effort on either surface. Hermes accepts `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. For manager fixtures, `--reasoning-level 5` stores the `xhigh` preset on the launch profile and takes precedence over the native default. Level `0` selects `none` explicitly. The Hermes fixture accepts manager levels `0` through `6`.

Add an entry like this to your external model pool, using your endpoint, model, and credential file. Select it with `--pool-key local_hermes` on either surface to use the same effort.

```toml
[models.local_hermes]
client = "hermes"
case = "self-hosted"
model = "your-hermes-model"
base_url = "https://models.example.invalid/v1"
env_file = "/external/private/hermes.env"
reasoning_effort = "xhigh"
```

For a deterministic loopback provider, start the fixture peer in one terminal and keep it running:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py chat-peer \
  --state-dir tmp/hermes-qualification/peer
```

The peer writes the model, URL, and synthetic credential to the owner-private `peer.env`. It serves a fixed answer and retains private `requests.jsonl` evidence for the selected model, authentication, role, and conversation messages. It records the top-level `reasoning_effort` when present.

```bash
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --client hermes --case self-hosted --model houmao-fixture-chat \
  --env-file tmp/hermes-qualification/peer/peer.env \
  --hermes-owner-root tmp/hermes-qualification/owner \
  --mode headless --surface manager --reasoning-level 5 --run-root tmp/hermes-qualification/runs
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py launch --run-dir RUN_DIR
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir RUN_DIR --prompt 'First turn'
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prompt --run-dir RUN_DIR --prompt 'Second turn'
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir RUN_DIR
```

Replace `RUN_DIR` with the returned `run_dir`. Run `check --run-dir RUN_DIR --live` to compare the saved launch binding with native host, profile, session, and dependency evidence. Prepare another run against the same owner root to exercise separate projects. Stop retains the native profile for relaunch. After explicit worker and build cleanup removes every named profile, `retire-hermes-owner --hermes-owner-root tmp/hermes-qualification/owner` verifies and retires the recorded test host.

For a standalone stock run, prepare with `--surface raw --reasoning-effort xhigh` and the same case and env file. Raw Headless takes its first prompt at launch with `--prompt`. Raw Service launches ACP and records its private protocol stream. TUI waits for Ink to become ready and publishes its isolated pane. Compare the peer's private request history with the mode's native turn evidence.

## Qualification

Default automated tests use synthetic credentials and harmless clients. Live qualification is explicit and requires working credentials, installed clients, declared compatible protocols, and a qualified model. Reports include the selected case, model, protocol, mode, backend, and the native build version when the executable reports it. Interactive runs include the verified terminal or browser surface. Record completed and resumed prompts, direct human-interface interaction, and available public usage. Report rejected credentials or unavailable self-hosted/native prerequisites as gaps. Never label an unexecuted lane as passed. Historical captures and completed change-local wrappers retain their factual model names; maintained launch paths use this helper.
