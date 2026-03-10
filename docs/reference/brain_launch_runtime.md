# Brain Launch Runtime

`gig_agents.agents.brain_launch_runtime` provides a repo-owned runtime for:

- composing `{brain manifest, role}` into a backend launch plan,
- starting interactive sessions (local or CAO),
- sending prompts or raw control input across resumed sessions,
- persisting schema-validated session manifests.

## CLI Entry Point

Use the module CLI:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime --help
```

Supported commands:

- `build-brain`
- `start-session`
- `send-prompt`
- `send-keys`
- `stop-session`

Command intent:

- Use `send-prompt` for normal prompt turns that should wait for readiness/completion and advance turn state.
- Use `send-keys` for low-level CAO tmux control input such as slash-command menus, partial typing, arrow-key navigation, or explicit `Escape`/`Ctrl-*` delivery that must not auto-submit with `Enter`.
- For the detailed `send-keys` contract, grammar, and examples, see [Brain Launch Runtime Send-Keys](./brain_launch_runtime_send_keys.md).

## Agent Definition Directory Resolution

Runtime command surfaces resolve the agent definition directory with this
precedence:

1. CLI `--agent-def-dir`
2. env `AGENTSYS_AGENT_DEF_DIR`
3. default `<pwd>/.agentsys/agents`

The resolved directory must contain `brains/`, `roles/`, and optionally
`blueprints/`.

## Build a Brain

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime build-brain \
  --agent-def-dir tests/fixtures/agents \
  --recipe brains/brain-recipes/codex/gpu-kernel-coder-default.yaml
```

## Local Codex Session (Default: `codex_headless`)

Start a session from an existing brain manifest:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest tmp/agents-runtime/manifests/codex/<home-id>.yaml \
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
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --brain-manifest tmp/agents-runtime/manifests/codex/<home-id>.yaml \
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
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest tmp/agents-runtime/manifests/claude/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless

pixi run python -m gig_agents.agents.brain_launch_runtime send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity tmp/agents-runtime/sessions/claude_headless/<session-id>.json \
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
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --brain-manifest tmp/agents-runtime/manifests/claude/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless

ANTHROPIC_MODEL=opus CLAUDE_CODE_SUBAGENT_MODEL=sonnet \
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --brain-manifest tmp/agents-runtime/manifests/claude/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url http://localhost:9889
```

## Gemini Headless Resume (tmux-backed `gemini -p --resume`)

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest tmp/agents-runtime/manifests/gemini/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend gemini_headless

pixi run python -m gig_agents.agents.brain_launch_runtime send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity tmp/agents-runtime/sessions/gemini_headless/<session-id>.json \
  --prompt "Continue from the prior answer"
```

Gemini resume requires the same working directory/project context captured in the session manifest.

## Headless Stop/Cleanup Semantics

For tmux-backed headless sessions (`codex_headless`, `claude_headless`,
`gemini_headless`):

- Default `stop-session` preserves the tmux session for inspection.
- Explicit cleanup path removes the tmux session:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime stop-session \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity AGENTSYS-gpu \
  --force-cleanup
```

## CAO-Backed Session

For an operator-oriented walkthrough of the interactive Claude CAO wrapper flow, see [Interactive CAO Full-Pipeline Demo](../../scripts/demo/cao-interactive-full-pipeline-demo/README.md).

Start CAO explicitly before `start-session`:

```bash
pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
  --config config/cao-server-launcher/local.toml
```

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest tmp/agents-runtime/manifests/codex/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --agent-identity gpu \
  --cao-base-url http://localhost:9889

pixi run python -m gig_agents.agents.brain_launch_runtime send-prompt \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity AGENTSYS-gpu \
  --prompt "Continue from the prior answer"

pixi run python -m gig_agents.agents.brain_launch_runtime send-keys \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity AGENTSYS-gpu \
  --sequence '/model<[Enter]><[Down]><[Enter]>'

pixi run python -m gig_agents.agents.brain_launch_runtime stop-session \
  --agent-def-dir tests/fixtures/agents \
  --agent-identity AGENTSYS-gpu
```

Then stop CAO explicitly:

```bash
pixi run python -m gig_agents.cao.tools.cao_server_launcher stop \
  --config config/cao-server-launcher/local.toml
```

Behavior:

- For resumed CAO operations (`send-prompt`, `send-keys`, `stop-session`), runtime addresses
  the session strictly from the persisted manifest (`cao.api_base_url`,
  `cao.terminal_id`) after resolving `--agent-identity`; there is no resume-time
  `--cao-base-url` override.
- `send-prompt` remains the high-level prompt-turn path. It waits for readiness/completion, uses the configured parsing mode, and advances persisted turn state.
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
  - `shadow_only`: readiness/completion from runtime `TurnMonitor` over
    `output?mode=full`, with parser-owned `surface_assessment` and
    `dialog_projection` artifacts instead of parser-owned final-answer extraction.
    Readiness follows the currently active input surface, not any historical
    slash-command or model-switch line still visible in scrollback. A recovered
    normal prompt is sendable again; only an actually active slash-command or
    waiting-user surface keeps submission blocked.
  - Runtime never mixes parser families in a single turn, and never auto-retries
    under the other parsing mode after mode-specific failure.
- CAO tmux session names use the canonical `AGENTSYS-<name>` namespace.
- `AGENTSYS` is reserved and cannot be used as the name portion.
- `start-session --agent-identity <name>` accepts name inputs for tmux-backed
  backends (`cao_rest`, `codex_headless`, `claude_headless`, `gemini_headless`)

## Missing `PATH` Troubleshooting

CAO-dependent and tmux-backed flows preflight exact executables and fail fast
when they are missing from `PATH`.

- Missing `tmux`: install `tmux` and verify `command -v tmux`.
- Missing `cao-server`: install CAO (`uv tool install cli-agent-orchestrator`) and
  verify `command -v cao-server`.
- Missing tool executable (`codex`, `claude`, `gemini`): install the tool CLI and
  verify with `command -v <tool>`.
  and returns the selected canonical identity in CLI JSON output.
- If no tmux-backed name is provided, runtime auto-generates a short
  `AGENTSYS-<tool-role>` identity and adds a suffix on conflicts.
- For tmux-backed sessions runtime sets
  `AGENTSYS_MANIFEST_PATH=<absolute-session-manifest-path>` in tmux session env.
- To discover active agent identities, run `tmux ls` and use returned
  `AGENTSYS-...` names with `send-prompt` / `send-keys` / `stop-session`.
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
- Shared surface assessment facets are:
  - `availability`: `supported`, `unsupported`, `disconnected`, `unknown`
  - `business_state`: `idle`, `working`, `awaiting_operator`, `unknown`
  - `input_mode`: `freeform`, `modal`, `closed`, `unknown`
  - `ui_context`: shared base plus provider-specific extensions
- Runtime success terminality in `shadow_only` requires `submit_ready` plus
  either post-submit projected-dialog change or observed post-submit `working`.
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
- Runtime promotes continuous `unknown` status to `stalled` after
  `unknown_to_stalled_timeout_seconds`.
- `stalled_is_terminal=true` fails immediately with stalled diagnostics; when
  `false`, runtime continues polling and can recover to known statuses.
- `parser_metadata` now includes:
  - selected preset id/version,
  - output format + variant id,
  - version detection/selection source, and
  - anomaly list (for example `baseline_invalidated`,
    `stalled_entered`, `stalled_recovered`).
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
    (`http://localhost:9889`, `http://127.0.0.1:9889`) inject loopback entries
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
   `agent_identity` (for example `AGENTSYS-gpu`).
2. Verify tmux windows:
   `tmux list-windows -t AGENTSYS-gpu -F '#{window_id} #{window_index} #{window_name}'`.
3. Expected success path:
   only the CAO terminal window is listed (bootstrap shell window is not
   expected after startup completes).
4. Attach and confirm first view:
   `tmux attach -t AGENTSYS-gpu` should land on the agent terminal window.
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

Session manifests are written under:

- `tmp/agents-runtime/sessions/<backend>/<session-id>.json`

Manifests are validated against in-package JSON Schemas before write and on load/resume.

Notes:

- CAO session manifests use `schema_version=2` and require `cao.parsing_mode`.
- Legacy CAO manifests (`schema_version=1`) are rejected to avoid mixed-mode resumes.
- Resume/start enforces parsing-mode consistency between persisted manifest and runtime session state.
