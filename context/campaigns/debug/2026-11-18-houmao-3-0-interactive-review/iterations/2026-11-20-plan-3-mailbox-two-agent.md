# Iteration Plan 3: Two-Agent Filesystem Mail and Notifier

Status: M1 and M2 passed end to end on `3.0.0rc5`; M3 covers notifier disable and `busy_skip`. The R2 system-skill rerun exposed a `houmao-mgr agents self identity` failure in the Kimi Web session. The R3 rerun on `f7f4245` confirmed the managed-self fix and completed both rounds; its retained agents were stopped and its isolated tmux and gateway state was verified gone on 2026-11-23. R4 on `0d642af` passed with host Kimi `2.7.2` under `>=2.6.0`, observed `busy_skip`, and completed the round without agent-side command errors. R10 on 2026-11-24 replaces R9 with launch profiles that default both Qwen 3.8 agents to `xhigh` reasoning; see [the R10 log](../logs/2026-11-24-iter3-two-agent-mail-r10-launch-profile-xhigh.md). R11 corrects the R10 Kimi conclusion: a config-backed alias exposes the ordered effort catalog and makes the Kimi UI show `xhigh`; see [the R11 log](../logs/2026-11-24-iter3-two-agent-mail-r11-kimi-config-effort.md). R4 teardown is pending. Date: 2026-11-20; R4 evidence added 2026-11-23. Campaign: [debug-intent.md](../debug-intent.md). Question owner: [KQ-4](../key-questions/KQ-4-local-mailbox-and-notifier.md). Evidence: [two-agent mail log](../logs/2026-11-20-iter3-two-agent-mail.md), [system-skill rerun](../logs/2026-11-20-iter3-two-agent-mail-r2-system-skills.md), [managed-self fix rerun](../logs/2026-11-20-iter3-two-agent-mail-r3-self-identity-fix.md), and [version-floor rerun](../logs/2026-11-23-iter3-two-agent-mail-r4-version-floor.md). Model lane: self-hosted `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.

## Question

Can a DSH Web agent and a Kimi Code Web agent, sharing one offline filesystem registry and mailbox root, exchange mail in both directions and wake each other through the live gateway mail-notifier without body restart, duplicate delivery, or replay?

This iteration activates only the local filesystem mailbox transport and its notifier. Stalwart online mail, `houmao-cccc`, execution-owner switching, and the DeepSeek lane remain deferred.

## Frozen Workload

- **Houmao**: uv-installed `houmao-mgr 3.0.0rc5`, Python 3.13, from `/home/huangzhe/.local/share/uv/tools/houmao/bin/`. Do not use the Pixi checkout while the source tree is under active development.
- **DSH**: `tmp/dsh/npm-runtime/node_modules/.bin/dsh` version `0.2.2-rc.3`, mode `web`, backend `dsh_web`.
- **Kimi**: `/home/huangzhe/.local/bin/kimi` version `2.6.0`, mode `web`, backend `kimi_web`.
- **Model**: `Qwen/Qwen3.8-27B-FP8`, OpenAI Chat Completions at `http://127.0.0.1:14888/v1`, context window `262144`, max output `8192`. Use a non-secret placeholder key for Kimi's API-key field; the endpoint ignores it.
- **Shared roots**: `tmp/houmao-30-iter3-mailbox/` contains `registry/`, `runtime/`, `mailbox/`, `runs/`, `inputs/`, and `bin/`. Both agents select the same `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, and `HOUMAO_GLOBAL_MAILBOX_DIR`.
- **Isolation**: each prepared fixture run keeps its own `bin/tmux` shim and `/tmp/tmux-<uid>/houmao-fixture-<run>/` socket. Clear `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR` for every command. Never touch the default tmux server.
- **Gateways**: both launches use `--gateway-background`; capture each gateway port and presence. Do not enable an admin roster; the rc5 empty-roster open policy is the selected access mode for this iteration.
- **Roles**: both agents receive the same short mail-test role. They process one notifier round, reply to the sender, archive the completed message, and stop.

## Predeclared Arms

| Arm | Surface | Required live evidence |
| --- | --- | --- |
| M0 | Shared offline registry and mailbox; two Web launches | Registry association, two distinct addresses, both mailbox bindings active, both gateways healthy, notifier `supported: true` before any mail |
| M1 | DSH → Kimi | DSH sends one message to Kimi; Kimi's gateway notifier polls, enqueues one wake-up, and Kimi's turn reads and replies; DSH receives the reply and archives |
| M2 | Kimi → DSH | Kimi sends one message to DSH; DSH's gateway notifier wakes it, DSH reads and replies; Kimi receives and archives |
| M3 | Notifier behavior | Interval and mode are observable; a busy target produces `busy_skip` rather than a lost or duplicated delivery; disabling the notifier stops future wakeups without clearing the mailbox |
| M4 | Mail lifecycle and teardown | List, peek, read, reply, archive, binding-ID pinning, and both agent stops are clean; no owned gateway, host, or notifier process remains |

## Gates

- **G0 — Shared authority**: Registry and mailbox initialization agree; both agents resolve distinct addresses in the same authority; both gateways report healthy and notifier support.
- **G1 — Delivery**: A message sent by one agent appears in the other's inbox with the correct sender, subject, body, and binding-scoped reference.
- **G2 — Wake-up**: Exactly one notifier wake-up is admitted for the eligible message while the target is idle; the target's native turn runs and the notifier audit records `enqueued`.
- **G3 — Round completion**: The receiver reads, replies, and archives; the sender receives the reply; the original message leaves the eligible inbox.
- **G4 — Teardown**: Disable both notifiers, stop both owned agents and hosts, and verify no campaign tmux server, gateway, or mailbox process remains.

## Command Contract

Prepare both fixtures without launching:

```bash
export ROOT=/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox
export UVPY=/home/huangzhe/.local/share/uv/tools/houmao/bin/python
export FIXTURE=scripts/agents/test-fixtures/fixture.py
export DSH=/data/huangzhe/code/houmao/tmp/dsh/npm-runtime/node_modules/.bin/dsh
export KIMI=/home/huangzhe/.local/bin/kimi

"$UVPY" "$FIXTURE" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --system-prompt-file "$ROOT/inputs/mail-role.txt" \
  --run-root "$ROOT/runs" --executable "$DSH"
```

Repeat with `--client kimi`, no DSH-specific options, and the Kimi executable. For Kimi, export a non-secret `HOUMAO_TEST_SELF_HOSTED_API_KEY=local-no-auth` during preparation so the fixture accepts the endpoint-only lane.

Launch each prepared run through the shared-root launcher:

```bash
"$UVPY" "$ROOT/bin/launch_shared.py" --run-dir "$ROOT/runs/<run>" --name <agent-name>
```

The launcher loads `private-env.json`, calls the maintained in-process manager with the shared roots, `--gateway-background`, `--mode web`, and `--mail-transport filesystem --mail-root "$ROOT/mailbox"`, then records the identity.

Inspect the shared state with:

```bash
export HOUMAO_GLOBAL_REGISTRY_DIR="$ROOT/registry"
export HOUMAO_GLOBAL_RUNTIME_DIR="$ROOT/runtime"
export HOUMAO_GLOBAL_MAILBOX_DIR="$ROOT/mailbox"
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" state
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" mailbox offline status
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" mail resolve-live
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" gateway mail-notifier enable \
  --channel offline --interval-seconds 30 --mode unread_only
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" gateway mail-notifier status \
  --channel offline
```

Send a test message from the sender's scoped context:

```bash
houmao-mgr --print-json agents single --agent-id "$SENDER_ID" mail send \
  --channel offline --expected-binding-id "$SENDER_BINDING_ID" \
  --to "$RECIPIENT_ADDRESS" --subject 'Mailbox wake test' \
  --body-content 'Reply with MAIL-OK and archive this message.'
```

Watch the recipient's gateway log, notifier audit, and native Web state. Do not inject prompts into the browser or supervisor pane to simulate a wake-up.

## Evidence

Record the shared-root identity, both manifests, both mailbox bindings, both gateway descriptors, notifier status before and after enable, notifier audit rows, the delivered message metadata, the native turn outcomes, the reply chain, and the final teardown. Keep private tokens, sign-in URLs, mailbox bodies containing secrets, and provider credentials out of tracked logs. Write the session record under `logs/2026-11-20-iter3-two-agent-mail.md` and any defect discussion under `discussions/`.

## Deferred Scope

Stalwart online mailbox attach/refresh/reconnect/detach and bounded JMAP sync remain deferred. `houmao-cccc` chat and deferred Mail remain deferred. Execution-owner switching and the DeepSeek lane remain deferred. This iteration does not qualify those surfaces.
