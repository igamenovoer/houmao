# Launch a Test Fixture

## Workflow

1. **Select the client, route, surface, and mode** from **Supported Lanes** and [../references/credential-resolution.md](../references/credential-resolution.md).
2. **Check or configure local inputs** using [configure-fixtures.md](configure-fixtures.md). Confirm any prompt, model metadata, and passive authority before launching.
3. **Prepare the selected lane** through the fixture helper, capturing its private `run_dir` and prerequisites.
4. **Launch the captured run** and send only selected prompts using **Launch and Follow-Up**. Preserve authoritative identity even when a later step fails.
5. **Verify the requested outcome** using **Verification and Handoff**, distinguishing startup, completed turns, usage availability, and cleanup.
6. **Return evidence and clean up when requested or at test completion**, targeting only this run's recorded authority.

If the test does not fit a supported lane, use the native planning tool to inspect the maintained CLI/harness interfaces and selected fixture inputs, then execute a supported plan or report the precise unsupported combination.

## Supported Lanes

| Surface | Modes | Authority and Use |
| --- | --- | --- |
| `raw` | `headless`, `tui` | Direct client/native output; no Houmao managed identity |
| `manager` | `headless`, `tui` | Current `houmao-mgr project agents launch`; captured agent/gateway identity |
| `passive-server` | `headless` | Same-host `houmao-passive-server` with an explicitly selected local authority URL |

Choose from the test subject. Do not infer headless from unattended posture. Provider-specific commands retain raw TUI behavior. For an exact raw TUI workdir/session, explicit `as_is`, or extra native arguments, use [the common adapter](../references/common-launch.md#exact-workdir-tui-adapter). The helper's normal TUI launches are unattended and allocate their own workdir/session; it exposes no corresponding overrides for managed lanes.

Keep runtime, registry, generated homes, and workdir state external. An already-running passive server must be authorized for this test and able to read the private paths on the same dev box. Pass its URL with `launch --passive-url URL`; preparation alone does not select a server. Start a new server only when included in the requested test setup, with isolated external roots. TUI birth belongs to the manager. Never stop a pre-existing server as fixture cleanup.

## Prepare

Run from the checkout, after the private cloud file has its selected model/key settings. This example selects Claude manager headless:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case cloud-api --client claude --surface manager --mode headless \
  --env-file "$HOME/.config/houmao/test-fixtures/deepseek.env"
```

Select `self-hosted` with its own private inputs for that case. For native login, replace the API-case/env-file flags with `--auth-method native-login --auth-bundle NAME`, and an external `--auth-root` if selected. Do not combine native auth with an API case. Pass explicit `--model`, `--context-window`, `--reasoning-key`, `--reasoning-effort`, or `--capabilities` only when needed by the selected model/configuration.

The returned `run_dir` owns the configured project and selected executable. Preparation is offline. See the [helper guide](../../../../scripts/agents/test-fixtures/README.md) for the supported role/seed/system-prompt inputs. Installing the case's skill pack and defining test assertions remain caller responsibilities.

## Launch and Follow-Up

For headless execution, use the prompt selected by the test. The following minimal prompts are examples; execute them only as an authorized smoke test:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py launch \
  --run-dir /external/prepared-run \
  --prompt 'Reply exactly OK. Do not use tools.'
pixi run python scripts/agents/test-fixtures/fixture.py prompt \
  --run-dir /external/prepared-run \
  --prompt 'Reply exactly DONE. Do not use tools.'
```

Raw headless launch requires a prompt and stores native JSONL/stderr privately. Its follow-up uses the captured provider session ID. Managed follow-up uses the captured authority and gateway. Do not guess a resume target or launch another agent as a substitute for resumption. A headless manager launch may create the agent without an initial prompt; raw headless may not.

When the selected test needs online mail, continue with [attach-online-mail.md](attach-online-mail.md) for an existing normal account and an active managed gateway. A raw-client launch alone supplies no managed authority for this attachment.

For passive birth, add the selected `--passive-url http://127.0.0.1:PORT` to `launch`. For TUI, omit the prompt initially, verify the live process and surface, then use `prompt` or the caller's input interface as appropriate. The fixture helper sends TUI text and Enter separately. A recorder caller retains ownership of recorded inputs and recording timing.

## Verification and Handoff

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run
pixi run python scripts/agents/test-fixtures/fixture.py check --run-dir /external/prepared-run --live
pixi run python scripts/agents/test-fixtures/fixture.py stop --run-dir /external/prepared-run
```

`check` is offline by default. Explicit `--live` queries captured managed usage or raw TUI liveness; it does not send a model prompt. Neither an offline check nor a live session alone proves a completed response. For a turn test, inspect completion/error evidence and exact session continuity. Preserve unavailable metrics as unavailable. Never report zero usage merely because the provider emitted none.

Return the selected route/client/model, surface/mode, private `run_dir`, outcome, completed/resumed turn evidence when requested, usage availability, actual managed agent/tracked-agent ID or raw session/pane, and identity-scoped follow-up/cleanup commands. Follow [the shared evidence contract](../references/common-launch.md#evidence-and-cleanup) for `launch.json`, `launch-report.md`, and repository-local sanitized pointers.

Helper `prompt`, `check`, and `stop` select the captured runtime/registry/overlay roots. For direct manager follow-up, use the exact roots recorded by the helper, as described in its guide. Cleanup never broad-kills tmux, provider processes, gateways, or unrelated agents. Stop test-owned agents at completion unless the developer requested a live handoff; retain private evidence and report failed cleanup explicitly.
