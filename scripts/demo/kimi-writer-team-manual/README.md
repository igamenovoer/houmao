# `kimi-writer-team-manual/`

Supported manual demo for a three-agent Kimi Code writing team.

The pack copies [examples/writer-team](../../../examples/writer-team/) into `outputs/project/`, redirects Houmao project state into `outputs/overlay/`, imports operator-supplied Kimi credential material, creates three Kimi specialists and mailbox-enabled project profiles, launches three local-interactive Kimi TUI agents, enables gateway mail-notifier polling, and leaves the operator in control of the story run.

## Prerequisites

- `pixi`
- `tmux`
- `kimi` or `kimi-code` on `PATH`
- one usable Kimi credential source:
  - `--kimi-code-home ~/.kimi-code`
  - `--kimi-auth-bundle tests/fixtures/auth-bundles/kimi/personal-a-default`
  - `--kimi-config-toml <path>` plus optional `--kimi-credential-json <path>`
  - `--api-key <key>` plus optional env-model settings

The demo does not commit live Kimi credential files. It fails before launch when no credential input is available.

## Start

OAuth-style Kimi Code home import:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh start --kimi-code-home ~/.kimi-code
```

Local fixture bundle import:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh start \
  --kimi-auth-bundle tests/fixtures/auth-bundles/kimi/personal-a-default
```

API-key lane:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh start \
  --api-key "$KIMI_MODEL_API_KEY" \
  --model-name kimi-k2
```

`start` resets `outputs/`, creates a fresh copied writer-team project, launches `alex-story`, `alex-char`, and `alex-review`, enables notifier polling for all three, and prints attach plus follow-up commands.

## Manual Run

Attach to the master:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh attach --agent alex-story
```

Send the smoke start charter to the master:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh prompt-start --chapters 1
```

Inspect live posture:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh status
scripts/demo/kimi-writer-team-manual/run_demo.sh inspect
scripts/demo/kimi-writer-team-manual/run_demo.sh notifier status
```

Send a manual mailbox nudge from one team member to another when needed:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh send-mail \
  --from-agent alex-story \
  --to-agent alex-char \
  --subject "Character pass for chapter 1" \
  --body-content "Read story/chapters/01-arrival.md, update character profiles, and reply to alex-story with the paths."
```

Stop the team:

```bash
scripts/demo/kimi-writer-team-manual/run_demo.sh stop
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

This demo intentionally uses Kimi local-interactive TUI posture. Specialist creation stores `launch.prompt_mode: as_is`, project launch omits `--headless`, and each launch asks Houmao to keep the gateway in the background so notifier rounds can wake the agents while the Kimi TUIs remain attachable.

