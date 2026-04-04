# How Do I Run A Two-Gateway Stalwart Mail Demo And Inspect Alice And Bob In Cypht?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This pack is intentionally Stalwart-only. It does not cover the filesystem mailbox transport.

The demo answers one concrete question:

> "How can I bring up the local Stalwart and Cypht stack, bind two live gateways to pre-made Alice and Bob mailbox accounts, send messages between them, and inspect unread-only behavior through both the gateway facade and Cypht?"

The pack uses:

- `dockers/email-system/` for the Stalwart, Postgres, and Cypht stack,
- two mailbox-enabled `cao_rest` sessions built from the lightweight `mailbox-demo-codex` blueprint,
- two live loopback gateways exposing `/v1/mail/*` and `/v1/mail-notifier`,
- tracked Alice and Bob mailboxes that stay loggable in Cypht because the demo seeds runtime credential files before session bootstrap.

## Prerequisites

- `pixi` is installed.
- The repo environment is installed with `pixi install`.
- `tmux` is installed and on `PATH`.
- Docker is available and the local email-stack images described in [dockers/email-system/README.md](/data1/huangzhe/code/houmao/dockers/email-system/README.md) already exist.
- The default Codex credential profile selected by `tests/fixtures/agents/blueprints/mailbox-demo-codex.yaml` is available.

## Filesystem Layout

By default, the wrapper writes to `tmp/demo/gateway-stalwart-cypht-interactive-demo-pack`.

```text
<demo-output-dir>/
├── cao/                  # demo-local CAO launcher config and runtime state
├── inputs/               # copied tracked demo inputs
├── participants/         # per-side build/start/attach/check/send artifacts
├── stack/                # stack bring-up and account-provision artifacts
├── workspace/            # copied dummy-project workdir
├── runtime/              # built homes, manifests, session roots, gateway roots
├── demo_state.json
├── inspect.json
└── turns.jsonl
```

## Start

Bring up the Docker stack, ensure `alice@example.test` and `bob@example.test`, start both sessions, attach both gateways, and enable unread-mail polling:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh start
```

The start summary prints:

- the Cypht URL,
- Alice and Bob Cypht logins,
- each mailbox address,
- the loopback gateway port for each side.

Default tracked credentials:

- Alice: `alice` / `admin`
- Bob: `bob` / `admin`

The helper resets those Stalwart account passwords to the tracked values on each `start`, then seeds the matching runtime credential files so Houmao reuses the same passwords instead of rotating them during session bootstrap.

## Open Cypht

After `start`, open the printed Cypht URL, normally:

```text
http://127.0.0.1:10081
```

Log in through separate browser profiles or tabs:

- Alice mailbox: username `alice`, password `admin`
- Bob mailbox: username `bob`, password `admin`

Use Cypht as the manual mailbox inspection and read-state surface between turns.

## Send And Check

Send Alice to Bob through Alice's gateway facade:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh send \
  --from alice \
  --to bob \
  --subject "Alice says hello" \
  --body-content "Hi Bob, please confirm the gateway saw this unread mail."
```

Check Bob's unread mail through Bob's gateway facade:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh check --who bob
```

That prints normalized gateway mailbox content, including:

- sender,
- subject,
- opaque `message_ref`,
- unread flag,
- body text or preview.

If you prefer polling until unread mail appears, use:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh watch --who bob
```

Reply from Bob to Bob's latest unread message without copying the opaque `message_ref` manually:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh reply \
  --from bob \
  --latest-unread \
  --body-content "Received. Replying through Bob's gateway."
```

Then check Alice:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh check --who alice
```

The same live sessions and gateways remain available across turns until `stop`.

## Inspect Notifier State

Capture a compact summary of:

- current gateway mailbox status,
- unread-check results,
- notifier status,
- notifier audit outcomes,
- recorded turn history.

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh inspect
```

The command writes `inspect.json` under the demo output directory and prints a short summary.

## Unread-Only Semantics

This demo keeps the existing gateway notifier contract unchanged:

- unread truth is owned by Stalwart,
- notifier polling is gateway-owned,
- reminders are sent only when the managed prompt surface is ready for input,
- unchanged unread mail may be reminded again after the session becomes ready again,
- gateway bookkeeping does not mark mail as read,
- reading a message in Cypht can change later unread results.

That is why this pack treats Cypht as the human acknowledgment surface and the gateway audit trail as the structured notifier evidence.

## Stop

Stop both live sessions, disable notifier polling, stop the demo-local CAO, and bring down the Docker stack:

```bash
scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh stop
```

## Tracked Inputs And Helpers

- [`inputs/demo_parameters.json`](inputs/demo_parameters.json)
- [`scripts/stalwart_demo_helpers.py`](scripts/stalwart_demo_helpers.py)
- [`run_demo.sh`](run_demo.sh)
