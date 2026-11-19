# Passive Observation Verification

## Changes Exercised

Passive observation selects the recorded mode and verified native surface. Only a TUI record with a terminal surface can create a TUI observer. The observer follows the verified pane and generation. The raw TUI detail remains at `/houmao/agents/{agent_ref}/state/detail`, and the curated TUI detail links to that route.

Manager-owned one-shot agents expose headless worker and durable exit evidence without a passive launch binding or attached gateway. Native Web observation follows the verified browser session. Service detail separates owner liveness, native connection readiness, and attributable request evidence. The service conformance case uses a stub because changes 04 through 06 qualify real service adapters.

## Automated Checks

| Command | Result |
| --- | --- |
| `pixi run pytest -q tests/unit/passive_server --tb=short` | 373 passed. Tests covered all four raw and curated state routes, terminal observer replacement on generation change, uncertainty when a headless exit record is missing, and a service with a live owner and a lost connection. |
| `pixi run pytest -q tests/integration/agents/dsh/web/test_gateway_native.py -k share_native_state_without_replay_queue --tb=short` | 1 passed with the explicitly selected DSH `0.2.2-rc.3` executable and a controlled local endpoint. Read-only passive observation preserved the exact Web identity and left the manifest unchanged. |
| `pixi run mypy src/houmao/passive_server src/houmao/server/models.py` | Passed. |
| `pixi run ruff check src/houmao/passive_server src/houmao/server/models.py tests/unit/passive_server` | Passed. |

The pytest suites emitted the existing Starlette test-client deprecation warning. Tmux-related runs cleared inherited `TMUX` and `TMUX_PANE` and targeted private sockets.

## Live Self-Hosted Qwen 3.8

The maintained fixture selected `self-hosted`, the exact model `Qwen/Qwen3.8-27B-FP8`, and the `openai_chat` endpoint at `http://127.0.0.1:14888/v1`. Each lane used a fresh external private run directory, an exact recorded tmux socket, and its own loopback `houmao-passive-server` instance with that run's registry. The compact and detailed raw routes used the run's empty admin enrollment. The curated summary used proof from the current owner self key.

| Tool | Mode and backend | Gateway attached | Gateway detached |
| --- | --- | --- | --- |
| Kimi `2.6.0` | `headless`, `kimi_headless` | Current headless artifact evidence and a completed outcome. | The same completed turn remained readable through its owner artifacts. |
| Kimi `2.6.0` | `tui`, `local_interactive` | The terminal displayed the requested assistant reply marker and returned to a stable, empty composer. Raw state reported `ready` and curated state reported `can_accept_prompt_now=true`. | The same verified terminal returned those readiness fields. The common control field made no native completion claim. |
| DSH `0.2.2-rc.3` | `web`, `dsh_web` | Current native Web evidence with a completed outcome via the live gateway. | Current direct native evidence for the same identity, session, and completed turn. |

For every lane, the fixture socket equaled the manifest socket and the socket reported by the live tmux server. All owned agents stopped through the fixture and all passive listeners exited. The test harness waited for the first TUI or Web observation poll because discovery can publish the identity before the observer initializes. During that interval, the state route correctly returned `503`.

## Kimi Terminal Readiness

The first direct manager-side observation had parsed `idle/freeform` and unknown tracker phase and surface fields in all ten samples. The tracker identity omitted the observed version, so the detector registry rejected it before reading the pane. The launch manifest already carried the observed `2.6.0` version. Passive discovery now forwards the version from the manifest it verifies against the registry. The attached gateway already read the same manifest field.

The Kimi source reference at `67325c1` documents the bordered composer, permission/model footer, and distinct live activity pane. Native Kimi `2.6.0` captures from the self-hosted Qwen fixture showed `Working for 1s` with a braille spinner above an empty, editable composer. The tracker now detects the elapsed label as live activity and suppresses readiness. A normal transcript bullet containing the same words leaves readiness unchanged. No provider-model string was required to recognize the native composer in these captures.

| Check | Result |
| --- | --- |
| `pixi run pytest -q tests/unit/shared_tui_tracking/test_kimi_code_session.py tests/unit/server/test_kimi_tui_parser.py tests/unit/passive_server --tb=short` | 401 passed. The Starlette test-client deprecation warning was unchanged. |
| Replay of actual Kimi `2.6.0` full-scrollback captures | 19 elapsed-spinner samples reported active and held readiness. Idle, unsent draft, and completed samples retained their distinct editing and activity fields. |
| Direct manager tracker after passing the recorded tool version | All ten samples reported `ready`, accepting `yes`, editing `no`, ready posture `yes`, and pending `no`. The isolated fixture stopped cleanly. |
| Live passive TUI rerun after the fixes | Raw and signed curated state showed ready on the exact terminal before and after gateway detach. Cleanup stopped the owned fixture and passive listener. |
| Scoped Ruff and `pixi run mypy src/houmao/shared_tui_tracking/apps/kimi_code/profile.py src/houmao/passive_server` | Passed. |
