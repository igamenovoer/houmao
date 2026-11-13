# `kimi-writer-team-manual/`

Supported manual demo for a three-agent Kimi Code writing team.

The pack copies [examples/writer-team](../../../examples/writer-team/) into `outputs/project/`, redirects Houmao project state into `outputs/overlay/`, imports operator-supplied Kimi credential material, creates three Kimi specialists and mailbox-enabled project profiles, launches visible unattended Kimi TUI writer agents plus a headless unattended reviewer, enables gateway mail-notifier polling, and leaves the operator in control of the story run.

## Prerequisites

- `pixi`
- `tmux`
- `kimi` or `kimi-code` on `PATH`
- one usable Kimi credential source:
  - `--kimi-code-home ~/.kimi-code`
  - `--kimi-auth-bundle /external/kimi-run/assets/tools/kimi/auth/default`
  - `--kimi-config-toml <path>` plus optional `--kimi-credential-json <path>`
  - selected run-owned env-model settings from the shared helper

The demo does not commit live Kimi credential files. It fails before launch when no credential input is available.

## Start

OAuth-style Kimi Code home import:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh start --demo-output-dir /external/kimi-writer-team --kimi-code-home ~/.kimi-code
```

Local fixture bundle import:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh start --demo-output-dir /external/kimi-writer-team \
  --kimi-auth-bundle /external/kimi-run/assets/tools/kimi/auth/default
```

API runs use the generic fixture helper with explicit model/context selection. Use the selected external credential inputs with this demo's credential options; never pass a resolved key in a shell argument or save it in tracked parameters. Choose an external `--demo-output-dir` for every live invocation.

`start` resets the selected external output directory, creates a fresh copied writer-team project, launches `alex-story`, `alex-char`, and `alex-review`, enables notifier polling for all three, and prints attach plus follow-up commands.

## Manual Run

Attach to the master:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh attach --demo-output-dir /external/kimi-writer-team --agent alex-story
```

Send the smoke start charter to the master:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh prompt-start --demo-output-dir /external/kimi-writer-team --chapters 1
```

Inspect live posture:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh status --demo-output-dir /external/kimi-writer-team
scripts/demo/kimi-writer-team-manual/run_demo.sh inspect --demo-output-dir /external/kimi-writer-team
scripts/demo/kimi-writer-team-manual/run_demo.sh notifier --demo-output-dir /external/kimi-writer-team status
```

Send a manual mailbox nudge from one team member to another when needed:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh send-mail --demo-output-dir /external/kimi-writer-team \
  --from-agent alex-story \
  --to-agent alex-char \
  --subject "Character pass for chapter 1" \
  --body-content "Read story/chapters/01-arrival.md, update character profiles, and reply to alex-story with the paths."
```

Stop the team:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh stop --demo-output-dir /external/kimi-writer-team
```

## Output Layout

- `outputs/project/`: copied writer-team workspace and visible story artifacts
- `outputs/overlay/`: project catalog, credentials, profiles, mailbox, runtime, jobs, and managed homes
- `outputs/registry/`: demo-local managed-agent registry
- `outputs/control/`: persisted state and JSON evidence
- `outputs/logs/`: command stdout/stderr
- `outputs/deliveries/`: rendered start charter and manual prompt payloads

Story artifacts should appear under:

- `outputs/project/story/chapters/`
- `outputs/project/story/characters/`
- `outputs/project/story/review/`

## Notes

This demo uses a hybrid Kimi posture. `alex-story` and `alex-char` launch as local-interactive TUI agents with `launch.prompt_mode: unattended`, which puts the visible Kimi sessions in auto permission mode before managed prompts. `alex-review` still launches through Kimi headless with `launch.prompt_mode: unattended` as the separate review posture. Each launch keeps the gateway in the background so notifier rounds can wake the agents.

## Generic API Fixtures

Prepare credentials with `pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client TOOL --model MODEL --env-file .env` (Kimi also needs `--context-window TOKENS`). Select `self-hosted` for a compatible local API or explicitly imported native-login state separately. Use only the returned external run-owned credential inputs and external demo outputs. See [the fixture helper](../../agents/test-fixtures/README.md).

The external bundle may come from `fixture.py prepare --client kimi --case cloud-api --model MODEL --context-window TOKENS --env-file .env`. Point `--kimi-auth-bundle` at its `assets/tools/kimi/auth/default`. The demo preserves context/capability env in its existing credential channel, invokes secret-bearing credential commands in-process, and rejects checkout-local live output roots.
