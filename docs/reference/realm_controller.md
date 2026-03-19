# Realm Controller

`houmao.agents.realm_controller` provides a repo-owned runtime for:

- composing `{brain manifest, role}` into a backend launch plan,
- starting interactive sessions (local or CAO),
- sending prompts, raw control input, or runtime-owned mailbox operations across resumed sessions,
- persisting schema-validated session manifests.

For the new detailed reference trees, use:

- [System Files Reference](./system-files/index.md) for the canonical Houmao-owned filesystem map, root overrides, and operator preparation guidance.
- [Runtime-Managed Agents Reference](./agents/index.md) for session targeting, interaction-path comparison, runtime-owned state, and recovery boundaries.
- [Shared Registry Reference](./registry/index.md) for cross-runtime-root discovery, record contracts, cleanup behavior, and runtime publication hooks.
- [Agent Gateway Reference](./gateway/index.md) for gateway attachability, HTTP and status contracts, queue behavior, and lifecycle handling.
- [Mailbox Reference](./mailbox/index.md) for filesystem mailbox behavior and managed mailbox flows.
- [Mailbox Roundtrip Tutorial Pack](../../scripts/demo/mailbox-roundtrip-tutorial-pack/README.md) for the explicit two-agent CAO-backed walkthrough that ties `build-brain`, `start-session`, `mail send/check/reply`, and `stop-session` together.

## CLI Entry Point

Use the module CLI:

```bash
pixi run python -m houmao.agents.realm_controller --help
```

Supported commands:

- `build-brain`
- `start-session`
- `send-prompt`
- `gateway-send-prompt`
- `send-keys`
- `attach-gateway`
- `detach-gateway`
- `gateway-status`
- `gateway-interrupt`
- `cleanup-registry`
- `mail`
- `stop-session`

Command intent:

- Use `send-prompt` for normal prompt turns that should wait for readiness/completion and advance turn state.
- Use `gateway-send-prompt` and `gateway-interrupt` only after a live gateway is already attached; they do not auto-attach a gateway implicitly.
- Use `send-keys` for low-level CAO tmux control input such as slash-command menus, partial typing, arrow-key navigation, or explicit `Escape`/`Ctrl-*` delivery that must not auto-submit with `Enter`.
- Use `mail` for runtime-owned mailbox operations (`check`, `send`, `reply`) against resumed mailbox-enabled sessions.
- Use `cleanup-registry` to remove stale shared-registry `live_agents/` directories left behind by crashes or expired soft leases.
- For the detailed `send-keys` contract, grammar, and examples, see [Realm Controller Send-Keys](./realm_controller_send_keys.md).

## Shared Agent Registry

Runtime-owned tmux-backed sessions publish a secret-free shared discovery record under one per-user registry root. That registry is a locator layer for cross-runtime-root recovery, not a replacement source of truth for `manifest.json`, tmux discovery, gateway state, or mailbox state.

For the dedicated registry subtree, start at [Shared Registry Reference](./registry/index.md).

- [Discovery And Cleanup](./registry/operations/discovery-and-cleanup.md): Name-based fallback from tmux-local discovery to the registry, plus `cleanup-registry` behavior and result buckets.
- [Record And Layout](./registry/contracts/record-and-layout.md): Effective root resolution, `agent_id`-keyed on-disk layout, and the strict v2 `record.json` shape.
- [Resolution And Ownership](./registry/contracts/resolution-and-ownership.md): Canonical naming, authoritative `agent_id`, `generation_id`, freshness, conflicts, and stale-versus-hard-invalid outcomes.
- [Runtime Integration](./registry/internals/runtime-integration.md): Publication hooks, persisted generation behavior, and the warning boundary for non-fatal registry refresh failures.

## Gateway-Capable Sessions

New runtime-owned tmux-backed sessions now publish gateway capability by default even when no live gateway process is attached yet.

Use [Agent Gateway Reference](./gateway/index.md) for the detailed attach contract, live HTTP routes, status model, durable artifacts, and lifecycle or recovery semantics. Use [Agents And Runtime](./system-files/agents-and-runtime.md) for the canonical session-root, nested `gateway/`, and `job_dir` filesystem map. This page keeps the gateway overview short so those details live in one place.

- The tmux session environment publishes stable attach pointers through `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`.
- When a live gateway is attached, tmux also publishes `AGENTSYS_AGENT_GATEWAY_HOST`, `AGENTSYS_AGENT_GATEWAY_PORT`, `AGENTSYS_GATEWAY_STATE_PATH`, and `AGENTSYS_GATEWAY_PROTOCOL_VERSION`.
- `state.json` is seeded under the gateway root before the first live attach and returns to the offline or not-attached state on graceful detach.
- Blueprint `gateway.host` and `gateway.port` act only as listener defaults for attach actions; they do not start a live gateway by themselves, and unknown gateway keys are rejected during blueprint load.
- If no gateway port override or default is supplied, attach requests a system-assigned port during gateway startup and then persists the actual bound port for later re-attach or restart.

Launch-time auto-attach is optional:

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --gateway-auto-attach
```

Later attach and detach stay explicit lifecycle actions:

```bash
pixi run python -m houmao.agents.realm_controller attach-gateway \
  --agent-identity AGENTSYS-gpu

pixi run python -m houmao.agents.realm_controller gateway-status \
  --agent-identity AGENTSYS-gpu

pixi run python -m houmao.agents.realm_controller gateway-send-prompt \
  --agent-identity AGENTSYS-gpu \
  --prompt "Queue this through the gateway"

pixi run python -m houmao.agents.realm_controller detach-gateway \
  --agent-identity AGENTSYS-gpu
```

`gateway-send-prompt` and `gateway-interrupt` require a live attached gateway and fail explicitly when the session is only gateway-capable. Legacy direct-control commands such as `send-prompt` still work for sessions that have no live gateway attached.

## Agent Definition Directory Resolution

Runtime command surfaces now use two resolution models.

For the detailed session-targeting model and how it relates to the runtime-managed interaction paths, see [Runtime-Managed Agent Public Interfaces](./agents/contracts/public-interfaces.md).

Build/start and manifest-path control (`--agent-identity /abs/.../manifest.json`) still resolve the agent definition directory with this ambient precedence:

1. CLI `--agent-def-dir`
2. env `AGENTSYS_AGENT_DEF_DIR`
3. default `<pwd>/.agentsys/agents`

Name-based tmux-backed control (`send-prompt`, `send-keys`, `mail`, and `stop-session` with `--agent-identity AGENTSYS-...` or an unprefixed name) uses a different default:

1. explicit CLI `--agent-def-dir` override, otherwise
2. the addressed tmux session's published `AGENTSYS_AGENT_DEF_DIR`, or
3. the fresh shared-registry record's stored `runtime.agent_def_dir` when tmux-local discovery is unavailable

Name-based tmux control still does not fall back to the caller's ambient `AGENTSYS_AGENT_DEF_DIR` or cwd-derived default when the live session pointer is missing or stale.

The resolved directory must contain `brains/`, `roles/`, and optionally `blueprints/`.

## Build a Brain

```bash
pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir tests/fixtures/agents \
  --recipe brains/brain-recipes/codex/gpu-kernel-coder-default.yaml
```

## Mailbox-Enabled Sessions

Mailbox support can come from declarative brain config or from `start-session` overrides. The implemented v1 transport is `filesystem`.

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless \
  --mailbox-transport filesystem \
  --mailbox-root tmp/shared-mail \
  --mailbox-principal-id AGENTSYS-research \
  --mailbox-address AGENTSYS-research@agents.localhost
```

Runtime behavior for mailbox-enabled sessions:

- bootstrap or validate the selected mailbox transport before the session begins,
- safely register the active mailbox for filesystem sessions or provision the active mailbox for `stalwart` sessions,
- project the runtime-owned mailbox skill for the selected transport,
- expose `AGENTSYS_MAILBOX_*` plus transport-specific `AGENTSYS_MAILBOX_FS_*` or `AGENTSYS_MAILBOX_EMAIL_*` bindings to the launched session,
- persist the resolved mailbox binding in the session manifest so resume uses the same mailbox configuration.

`AGENTSYS_MAILBOX_FS_INBOX_DIR` follows the active mailbox registration path for the session's full mailbox address, so it may resolve through a symlink-backed `mailboxes/<address>` entry into a private mailbox directory.

For the dedicated mailbox reference subtree, start at [Mailbox Reference](./mailbox/index.md). It now carries the detailed quickstart, contracts, operations, and internals pages for mailbox behavior.

The `mail` command operates on resumed mailbox-enabled sessions and currently supports:

- `mail check`
- `mail send`
- `mail reply`

Notes:

- `mail send` recipients must use full mailbox addresses such as `AGENTSYS-orchestrator@agents.localhost`.
- `mail send` and `mail reply` require explicit body content through `--body-file` or `--body-content`.
- `mail reply` now prefers shared opaque `message_ref` values and accepts the legacy `--message-id` flag only as a compatibility alias.
- `mail` supports both the filesystem mailbox transport and the `stalwart` transport, and shared mailbox operations prefer the live gateway `/v1/mail/*` facade when it is attached.
- For the mailbox quickstart, contracts, managed helper rules, lifecycle modes, repair expectations, and internals, see [Mailbox Reference](./mailbox/index.md).

## Local Codex Session (Default: `codex_headless`)

Start a session from an existing brain manifest:

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder
```

Notes:

- Default non-CAO Codex backend is `codex_headless`.
- Runtime executes each turn in tmux using:
  - first turn: `codex exec --json <prompt>`
  - resume turn: `codex exec --json resume <thread_id> <prompt>`
- Runtime persists Codex `thread_id` as the resumable headless session id.
- Role injection uses Codex config override:
  `-c developer_instructions=<role-prompt>`.

## Legacy Codex App-Server Override (Deprecation Window)

`codex_app_server` remains available as an explicit override during a bounded
deprecation window:

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend codex_app_server
```

Sunset criteria for removal in follow-up change:

- Codex headless stability in real usage and CI smoke coverage.
- Unit/integration/manual test parity with prior non-CAO Codex behavior.
- Docs parity for start/resume/stop/identity workflows.

## Codex Bootstrap Contract

For Codex launches (`codex_headless`, `codex_app_server`, and Codex `cao_rest`),
runtime startup enforces a shared non-interactive bootstrap contract on
`CODEX_HOME/config.toml`:

- always set `[notice].hide_full_access_warning = true`,
- always seed trust for launch context under
  `[projects."<resolved-path>"].trust_level = "trusted"`,
- resolve trust target to agent-definition root when `.git` is discoverable from launch
  workdir, otherwise use the explicit launch workdir,
- only re-assert `approval_policy` / `sandbox_mode` when those keys are
  explicitly present in the selected Codex config profile.

Bootstrap is idempotent and preserves unrelated config settings.

## Claude Headless Resume (tmux-backed `claude -p --resume`)

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity <runtime-root>/sessions/claude_headless/<session-id>/manifest.json \
  --prompt "Summarize the current plan"
```

The runtime captures `session_id` from machine-readable output and persists it in the
session manifest for follow-up turns.

Migration-phase resume/session control still reloads role data from the agent
definition directory. Deferred portability follow-up is tracked in:
`context/issues/known/issue-runtime-resume-still-coupled-to-agent-def-dir.md`.

Claude headless base args come from the Claude tool adapter (`brains/tool-adapters/claude.yaml:launch.args`).
Backend code reserves and injects only:

- `--resume <session_id>`
- `--output-format <format>`
- `--append-system-prompt <text>` (when native role injection is used)

If adapter `launch.args` contains any reserved arg, launch-plan construction fails fast with a configuration error.

## Claude Bootstrap Contract

For Claude launches (`claude_headless` and `cao_rest`), runtime startup enforces a shared non-interactive bootstrap contract on `CLAUDE_CONFIG_DIR`:

- `settings.json` must exist and set `skipDangerousModePermissionPrompt: true`.
- `claude_state.template.json` must exist (projected from credential profile input).
- runtime `.claude.json` is materialized only when missing (create-only), by applying launcher-enforced keys onto the template:
  - `hasCompletedOnboarding: true`
  - `numStartups: 1`
  - `customApiKeyResponses` based on `ANTHROPIC_API_KEY` suffix when set

Rationale: Claude Code first-run behavior may show interactive onboarding/approval prompts and may contact `api.anthropic.com` for feature flags even when `ANTHROPIC_BASE_URL` is configured. This bootstrap keeps orchestrated launches non-interactive in isolated homes.

Verified against Claude Code `v2.1.62` on `2026-02-27`.

## Model selection (Claude Code)

For Claude Code launches, set model-selection via environment variables. This
works for both `backend=claude_headless` and `backend=cao_rest`.

Supported variables:

- `ANTHROPIC_MODEL` (primary model selector; for example `opus` or a fully-qualified model id)
- `ANTHROPIC_SMALL_FAST_MODEL` (optional small/fast model override)
- `CLAUDE_CODE_SUBAGENT_MODEL` (optional subagent model override)
- `ANTHROPIC_DEFAULT_OPUS_MODEL` (optional alias pinning)
- `ANTHROPIC_DEFAULT_SONNET_MODEL` (optional alias pinning)
- `ANTHROPIC_DEFAULT_HAIKU_MODEL` (optional alias pinning)

Usage notes:

- `claude_headless`: runtime process env starts from caller environment and then
  overlays allowlisted values from the Claude credential profile
  (`brains/api-creds/claude/<profile>/env/vars.env`).
- `cao_rest`: tmux session env starts from caller environment, overlays the
  Claude credential profile env file, then applies runtime launch overlays.

Examples:

```bash
ANTHROPIC_MODEL=opus ANTHROPIC_SMALL_FAST_MODEL=claude-3-5-haiku-latest \
pixi run python -m houmao.agents.realm_controller start-session \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless

ANTHROPIC_MODEL=opus CLAUDE_CODE_SUBAGENT_MODEL=sonnet \
pixi run python -m houmao.agents.realm_controller start-session \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url http://localhost:<port>
```

Use the same loopback port configured for the CAO launcher. `9889` is the default example port, but any supported launcher-managed loopback port is allowed.

## Gemini Headless Resume (tmux-backed `gemini -p --resume`)

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend gemini_headless

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity <runtime-root>/sessions/gemini_headless/<session-id>/manifest.json \
  --prompt "Continue from the prior answer"
```

Gemini resume requires the same working directory/project context captured in the session manifest.

## Headless Stop/Cleanup Semantics

For tmux-backed headless sessions (`codex_headless`, `claude_headless`,
`gemini_headless`):

- Default `stop-session` preserves the tmux session for inspection.
- Explicit cleanup path removes the tmux session:

```bash
pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-identity AGENTSYS-gpu \
  --force-cleanup
```

## CAO-Backed Session

For the docs-side overview of the interactive CAO wrapper flow, see [Interactive CAO Demo](./cao_interactive_demo.md). For the full step-by-step operator tutorial, see [Interactive CAO Full-Pipeline Tutorial Pack](../../scripts/demo/cao-interactive-full-pipeline-demo/README.md).

Start CAO explicitly before `start-session`:

```bash
pixi run python -m houmao.cao.tools.cao_server_launcher start \
  --config config/cao-server-launcher/local.toml
```

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --agent-identity gpu \
  --cao-base-url http://localhost:<port>

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-identity AGENTSYS-gpu \
  --prompt "Continue from the prior answer"

pixi run python -m houmao.agents.realm_controller send-keys \
  --agent-identity AGENTSYS-gpu \
  --sequence '/model<[Enter]><[Down]><[Enter]>'

pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-identity AGENTSYS-gpu
```

Then stop CAO explicitly:

```bash
pixi run python -m houmao.cao.tools.cao_server_launcher stop \
  --config config/cao-server-launcher/local.toml
```

Use `--cao-base-url http://127.0.0.1:9991` to target another supported
launcher-managed loopback port when needed.

Behavior:

- For name-based tmux-backed resumed operations (`send-prompt`, `send-keys`, `mail`, `stop-session` with an agent name), runtime resolves the manifest path from `AGENTSYS_MANIFEST_PATH` and the effective agent-definition root from explicit `--agent-def-dir` or the addressed session's `AGENTSYS_AGENT_DEF_DIR`.
- For resumed CAO operations (`send-prompt`, `send-keys`, `mail`, `stop-session`), runtime addresses
  the session strictly from the persisted manifest (`cao.api_base_url`,
  `cao.terminal_id`) after resolving `--agent-identity`; there is no resume-time
  `--cao-base-url` override.
- For gateway-aware CAO operations (`attach-gateway`, `detach-gateway`, `gateway-status`, `gateway-send-prompt`, `gateway-interrupt`), runtime validates the stable attach pointers plus the live gateway bindings and then uses `GET /health` as the authoritative liveness check before trusting a live gateway instance.
- `gateway-status` reads the live `GET /v1/status` contract when a live gateway is attached and otherwise falls back to the seeded `state.json` snapshot under `AGENTSYS_GATEWAY_ROOT`.
- `send-prompt` remains the high-level prompt-turn path. It waits for readiness/completion, uses the configured parsing mode, and advances persisted turn state.
- `gateway-send-prompt` and `gateway-interrupt` route through `POST /v1/requests` and return accepted queue records instead of waiting for turn completion.
- `send-keys` is CAO-only in the first release. It resolves the tmux target from persisted CAO session state, reuses `cao.tmux_window_name` when available, falls back to live `GET /terminals/{id}` metadata when older manifests do not yet persist the window name, and returns one JSON control result immediately after delivery.
- `send-keys --sequence` accepts mixed literal text plus exact tmux special-key tokens in the form `<[key-name]>`. Recognition is case-sensitive, whitespace inside the token disables recognition and leaves the substring literal, and `--escape-special-keys` sends the full string literally.
- Guaranteed exact key names for `send-keys`: `Enter`, `Escape`, `Up`, `Down`, `Left`, `Right`, `Tab`, `BSpace`, `C-c`, `C-d`, and `C-z`.
- `send-keys` never appends an implicit trailing `Enter`; include `<[Enter]>` explicitly when submit behavior is desired.
- CAO turn parsing mode is explicitly resolved to one of:
  - `cao_only`
  - `shadow_only`
- Parsing mode resolution order:
  1) `start-session --cao-parsing-mode <mode>` override
  2) brain-manifest config (`runtime.cao_parsing_mode` or `runtime.cao.parsing_mode`)
  3) per-tool default (`claude -> shadow_only`, `codex -> shadow_only`)
- Shadow stall policy config (for `parsing_mode=shadow_only`):
  - `runtime.cao.shadow.unknown_to_stalled_timeout_seconds` (default `30`)
  - `runtime.cao.shadow.completion_stability_seconds` (default `1.0`)
  - `runtime.cao.shadow.stalled_is_terminal` (default `false`)
- `start-session` JSON output for `backend=cao_rest` includes the resolved
  `parsing_mode` alongside `agent_identity`.
- All four `(tool, parsing_mode)` combinations are supported, but non-default
  combinations are operationally advanced:
  - `claude + shadow_only` (default, recommended)
  - `claude + cao_only` (supported, currently less reliable due upstream drift)
  - `codex + shadow_only` (default, recommended)
  - `codex + cao_only` (supported fallback for migration/incident response)
- Strict no-fallback policy:
  - `cao_only`: readiness/completion from CAO terminal status, answer extraction
    from `output?mode=last`.
  - `shadow_only`: readiness/completion from the runtime monitor over
    `output?mode=full`, with current-thread CAO polling in `cao_rest.py`
    feeding readiness/completion pipelines in `cao_rx_monitor.py`, and with parser-owned `surface_assessment` and
    `dialog_projection` artifacts instead of parser-owned final-answer extraction.
    Readiness follows the currently active input surface, not any historical
    slash-command or model-switch line still visible in scrollback. A recovered
    normal prompt is sendable again; only an actually active slash-command or
    waiting-user surface keeps submission blocked.
  - Runtime never mixes parser families in a single turn, and never auto-retries
    under the other parsing mode after mode-specific failure.
- Canonical agent names still use the `AGENTSYS-<name>` namespace, but persisted `tmux_session_name` is now the actual tmux handle and must be learned from manifest or shared-registry metadata rather than inferred from canonical name alone.
- `AGENTSYS` is reserved and cannot be used as the name portion.
- `start-session --agent-identity <name>` accepts name inputs for tmux-backed
  backends (`cao_rest`, `codex_headless`, `claude_headless`, `gemini_headless`)
  and returns the selected canonical identity in CLI JSON output.

For deeper runtime-managed message-passing guidance, use [Session And Message Flows](./agents/operations/session-and-message-flows.md). For the gateway-specific lifecycle and queue semantics behind the gateway-aware bullets above, use [Gateway Lifecycle And Operator Flows](./gateway/operations/lifecycle.md) and [Gateway Queue And Recovery](./gateway/internals/queue-and-recovery.md).

## Missing `PATH` Troubleshooting

CAO-dependent and tmux-backed flows preflight exact executables and fail fast
when they are missing from `PATH`.

- Missing `tmux`: install `tmux` and verify `command -v tmux`.
- Missing `cao-server`: install CAO from the supported fork (`uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release`) and
  verify `command -v cao-server`.
- Missing tool executable (`codex`, `claude`, `gemini`): install the tool CLI and
  verify with `command -v <tool>`.
- If no tmux-backed name is provided, runtime auto-generates a canonical
  `AGENTSYS-<tool-role>` identity and derives the live tmux handle as
  `<canonical-agent-name>-<agent-id-prefix>`, extending the prefix one
  character at a time on collisions.
- For tmux-backed sessions runtime sets
  `AGENTSYS_MANIFEST_PATH=<absolute-session-manifest-path>` and
  `AGENTSYS_AGENT_DEF_DIR=<absolute-agent-def-dir>` in tmux session env.
- To discover the live tmux handle, inspect the returned `tmux_session_name`,
  the persisted manifest, or shared-registry metadata. Name-addressed runtime
  control still uses the canonical `AGENTSYS-<name>` identity.
- Parsing mode must not change AGENTSYS identity naming, tmux manifest-pointer
  publication, or name-based resolution semantics.
- Startup window hygiene for `backend=cao_rest`:
  - Runtime captures the bootstrap tmux `window_id` immediately after session creation.
  - Runtime resolves the CAO terminal tmux `window_id` from `create_terminal(...).name`
    with bounded retry. If resolution fails, bootstrap pruning is skipped.
  - Runtime best-effort selects the CAO terminal window so first `tmux attach`
    lands on the agent window.
  - Runtime best-effort prunes only the recorded bootstrap window (by `window_id`)
    when it is distinct from the resolved CAO terminal window; prune is skipped
    when both resolve to the same tmux window.
  - If resolve/select/prune fails, `start-session` still succeeds and prints
    stderr diagnostics as `warning:` lines; JSON stdout output is unchanged.

- Generates a unique per-session CAO profile from `roles/<role>/system-prompt.md`.
- Installs profile into CAO agent store (`~/.aws/cli-agent-orchestrator/agent-store` by default).
- Maps runtime tools to CAO providers explicitly:
  - `codex` -> `codex`
  - `claude` -> `claude_code`
- Requires `tmux` on `PATH`; runtime creates a per-session tmux session, inherits
  the full caller process environment, overlays credential profile `vars.env`,
  then applies launch-specific env vars (for example the home selector).
- Uses direct terminal input only (no inbox).
- Shadow parsers (when `parsing_mode=shadow_only`) produce frozen
  `surface_assessment` and `dialog_projection` value objects.
- `dialog_projection.normalized_text` remains closer to the captured TUI surface.
- `dialog_projection.dialog_text` is a best-effort heuristic projection for operator inspection and caller-owned extraction patterns; it is not an exact recovered transcript.
- Current runtime lifecycle evidence keys off normalized shadow text after pipeline normalization rather than `dialog_text`.
- Provider parsers own version-aware projector selection, and `projection_metadata.projector_id` identifies the selected projector instance.
- Shared surface assessment facets are:
  - `availability`: `supported`, `unsupported`, `disconnected`, `unknown`
  - `business_state`: `idle`, `working`, `awaiting_operator`, `unknown`
  - `input_mode`: `freeform`, `modal`, `closed`, `unknown`
  - `ui_context`: shared base plus provider-specific extensions
- Runtime success terminality in `shadow_only` requires `submit_ready` plus
  previously-seen post-submit activity (`working` or normalized shadow-text change)
  that then remains stable for `completion_stability_seconds`.
- Caller-owned completion observers may bypass the generic stability window when
  they detect a definitive result payload.
- Runtime shadow parsing for both Claude and Codex is versioned and preset-driven.
  Preset resolution order is:
  1) provider-specific env override,
  2) detected banner version (when present),
  3) deterministic fallback (latest or floor preset).
- Provider override env vars:
  - Claude: `AGENTSYS_CAO_CLAUDE_CODE_VERSION`
  - Codex: `AGENTSYS_CAO_CODEX_VERSION`
- Unknown newer versions are parsed with floor presets and surfaced in
  `parser_metadata.shadow_parser_anomalies` as
  `unknown_version_floor_used`.
- Unknown/drifted output variants fail fast with
  `unsupported_output_format` (no fallback to `cao_only` in-turn).
- Runtime promotes continuous `unknown` status to `stalled` after the
  configured inter-observation-gap threshold
  `unknown_to_stalled_timeout_seconds`.
- Any known observation cancels the pending unknown-to-stalled timer and clears
  stalled tracking before the recovered classification is handled.
- `stalled_is_terminal=true` fails immediately with stalled diagnostics; when
  `false`, runtime continues polling and can recover to known statuses.
- `parser_metadata` now includes:
  - selected preset id/version,
  - output format + variant id,
  - version detection/selection source, and
  - anomaly list (for example `baseline_invalidated`,
    `stalled_entered`, `stalled_recovered`).
- Shadow policy values such as `unknown_to_stalled_timeout_seconds`,
  `completion_stability_seconds`, and `stalled_is_terminal` are surfaced in
  both `parser_metadata` and `mode_diagnostics`.
- `shadow_only` done payloads surface:
  - `surface_assessment`
  - `dialog_projection`
  - `projection_slices`
  - diagnostics-only raw transport tail excerpts when retained
- `shadow_only` done payloads do not include a shadow-mode `output_text` alias.
- Troubleshooting and fixture-capture workflow:
  [`docs/reference/cao_shadow_parser_troubleshooting.md`](./cao_shadow_parser_troubleshooting.md).
- Loopback proxy defaults:
  - Runtime-owned CAO REST calls to supported loopback CAO base URLs
    (`http://localhost:<port>`, `http://127.0.0.1:<port>`) inject loopback entries
    into `NO_PROXY`/`no_proxy` by default so ambient proxy vars do not proxy
    CAO control-plane traffic.
  - CAO tmux session env composition preserves proxy vars for agent egress and
    injects loopback `NO_PROXY`/`no_proxy` entries by default for loopback CAO
    sessions.
  - Set `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` to preserve caller-provided
    `NO_PROXY`/`no_proxy` unchanged (for example, to intentionally route
    localhost traffic through a traffic-watching proxy).

Gemini parser architecture remains unchanged in this change and stays
headless-only. Follow-up design work is tracked in
`context/issues/feat-gemini-headless-parser-architecture.md`.

### Manual Verification Checklist (CAO Startup Window Hygiene)

1. Start a CAO-backed session (`backend=cao_rest`) and capture returned
   `agent_identity` plus `tmux_session_name` (for example `AGENTSYS-gpu` and
   `AGENTSYS-gpu-270b87`).
2. Verify tmux windows:
   `tmux list-windows -t <tmux_session_name> -F '#{window_id} #{window_index} #{window_name}'`.
3. Expected success path:
   only the CAO terminal window is listed (bootstrap shell window is not
   expected after startup completes).
4. Attach and confirm first view:
   `tmux attach -t <tmux_session_name>` should land on the agent terminal window.
5. Warning-path expectation:
   if cleanup cannot resolve/select/prune windows, `start-session` still returns
   success JSON and stderr includes one or more `warning:` lines describing the
   specific cleanup issue. In this case, you may still see a bootstrap window.

## Non-CAO Headless Proxy Contract

For non-CAO headless backends (`codex_headless`, `claude_headless`,
`gemini_headless`), runtime tmux launch env composition preserves proxy vars for
egress and injects loopback entries into `NO_PROXY`/`no_proxy` by default.

- Default: loopback entries (`localhost`, `127.0.0.1`, `::1`) are merged into
  `NO_PROXY`/`no_proxy`.
- Opt-out: set `AGENTSYS_PRESERVE_NO_PROXY_ENV=1` to preserve caller-provided
  `NO_PROXY`/`no_proxy` unchanged.

## Session Manifest

Use [Agents And Runtime](./system-files/agents-and-runtime.md) for the canonical runtime-owned filesystem inventory covering generated homes, generated manifests, runtime session roots, nested gateway files, and workspace-local `job_dir` placement.

Manifests are validated against in-package JSON Schemas before write and on load/resume.

Notes:

- Session manifests now use `schema_version=3` and persist first-class top-level `agent_name`, `agent_id`, `tmux_session_name`, and `job_dir` fields.
- CAO session manifests still require `cao.parsing_mode`.
- Legacy CAO manifests (`schema_version=1`) are rejected to avoid mixed-mode resumes.
- Resume/start enforces parsing-mode consistency between persisted manifest and runtime session state.
