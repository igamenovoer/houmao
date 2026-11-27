# Instructional Managed Hermes Agent Suite

Status: proven

Agent-driven live verification for Houmao-managed Hermes agents running against a real self-hosted Qwen 3.8 OpenAI-compatible Chat Completions endpoint with `xhigh` thinking. The suite covers Service, Headless, and TUI, reasoning and role projection, isolated named profiles on a shared gateway, and offline and Stalwart mailbox round trips.

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved via `git rev-parse --show-toplevel`).
- **Manager binary.** Build or sync the workspace environment with `pixi install` and point `HOUMAO_MGR` at `$REPO_ROOT/.pixi/envs/default/bin/houmao-mgr`.
- **Prepared test owner.** Prepare stock Hermes in a dedicated private directory under the repository's ignored `tmp/` tree. Select it with `HOUMAO_TEST_HERMES_OWNER_ROOT`. The parallel isolation case requires a root dedicated to that case so its teardown can verify every test profile is gone. [Hermes Owner Setup](../../../docs/reference/run-phase/hermes-owner-setup.md)
- **Model pool (`Qwen 3.8` with `xhigh` thinking).** Configure an owner-private (`0600`) external model pool at `${XDG_DATA_HOME:-$HOME/.local/share}/houmao/test-fixtures/model-pool.toml` (or set `HOUMAO_TEST_MODEL_POOL`) with a `client = "hermes"`, `case = "self-hosted"` entry pointing to your Qwen 3.8 Chat Completions server and an external `0600` env file supplying a non-empty `HOUMAO_TEST_SELF_HOSTED_API_KEY`. Set `HOUMAO_TEST_MODEL` to that pool key (or override individual slots with `HOUMAO_TEST_MODEL_A` / `HOUMAO_TEST_MODEL_B`). See [Test-Agent Fixture Tools](../../../scripts/agents/test-fixtures/README.md#hermes).

```toml
schema_version = 1

[models.local_hermes_qwen38]
client = "hermes"
case = "self-hosted"
model = "Qwen/Qwen3.8-27B-FP8"
base_url = "http://127.0.0.1:14888/v1"
env_file = "/external/private/hermes-local.env"
reasoning_effort = "xhigh"
```

- **Local filesystem mailbox (`offline`).** Requires no external service. The mail scenario initializes both fixture registries against the run-owned store under `$RUN_TMP/runtime/mailbox` and joins both agents to that shared root.
- **Stalwart mail service (`online`, Scenario 6 only).** Treats any selected Stalwart deployment (default `http://127.0.0.1:10080/.well-known/jmap`) as shared infrastructure. The suite never starts, stops, resets, or reconfigures Stalwart; it provisions two uniquely prefixed run-owned accounts with verified sending identities and Archive roles, and deprovisions only those recorded principals during cleanup. If no live Stalwart service or private `service.json` is configured, mark Scenario 6 `VERIFIED-UNREACHABLE` rather than mocking Stalwart.
- **Project-local temporary root.** `$REPO_ROOT/tmp/instructional-tests/<test-slug>/` (Git-ignored). Every per-run script (`scripts/`), disposable fixture state (`runtime/`), `run-meta.json`, and surviving proof artifact (`evidence/agent-hermes/<scenario-slug>/`) lives inside this directory with `0700` permissions.
- **Tmux and gateway ownership.** Clear `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR` before every command. Each worker has an isolated tmux socket and a distinct `HERMES_HOME` under the selected owner. The test owner shares a registry, runtime, and native gateway across workers. Teardown uses the recorded test-host identity.
- **Concurrency.** Distinct `<test-slug>` runs isolate filesystem and tmux state safely, though concurrent `xhigh` runs against the same single-GPU Qwen 3.8 server may serialize on inference latency. Do not double-drive a single launched agent.

## Launch

Ensure the workspace binaries are current and verify the model pool and live Qwen 3.8 endpoint before allocating agent runs:

```bash
pixi install
umask 077
unset TMUX TMUX_PANE TMUX_TMPDIR
export REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
export BUNDLE_ROOT="$REPO_ROOT/tests/instructional/agent-hermes"
export FIXTURE="$REPO_ROOT/scripts/agents/test-fixtures/fixture.py"
export LAB="$BUNDLE_ROOT/helpers/hermes_lab.py"
export HOUMAO_MGR="${HOUMAO_MGR:-$REPO_ROOT/.pixi/envs/default/bin/houmao-mgr}"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-agent-hermes"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export EVIDENCE="$RUN_TMP/evidence/agent-hermes"
# Prepare this installation once with the linked owner setup instructions.
export HOUMAO_TEST_HERMES_OWNER_ROOT="${HOUMAO_TEST_HERMES_OWNER_ROOT:-$RUN_TMP/hermes-owner}"

mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime" "$EVIDENCE"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored" >&2; exit 1; }
chmod 700 "$RUN_TMP"
test -x "$HOUMAO_MGR"
test -d "$HOUMAO_TEST_HERMES_OWNER_ROOT"

pixi run python "$FIXTURE" list-models > "$EVIDENCE/model-pool-list.json"
pixi run python "$FIXTURE" check --pool-slot a --mode service --surface manager --live \
  > "$EVIDENCE/a-check-service.json"
jq -e '.configuration.client == "hermes"' "$EVIDENCE/a-check-service.json" >/dev/null
```

Each scenario prepares and launches its required Hermes mode(s) into dedicated subdirectories under `$RUN_TMP/runtime/` using `fixture.py prepare` (supplying `--pool-slot`, `--surface manager`, `--tmux-server new`, `--prompt-mode unattended`, `--system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md"`, and `--reasoning-level 5` when testing numeric precedence) followed by `fixture.py launch`.

## Doctor

Run `doctor` after launching any scenario's agent(s), before the first drive, and after any surprising failure:

```bash
pixi run python "$LAB" doctor \
  --run-dir "$RUN_A" \
  --expected-effort xhigh \
  | tee "$EVIDENCE/doctor.json"
```

Add `--run-dir "$RUN_B"` for dual-agent scenarios, `--mailbox-root "$RUN_TMP/runtime/mailbox"` for the offline mail scenario, and `--mail-config "$MAIL_CONFIG"` for the Stalwart online mail scenario. `doctor` qualifies the selected runtime, checks agent availability and the recorded gateway PID, inspects the actual profile's reasoning and tool settings, and verifies any configured mail services.

## Drive

Drive agents exclusively through the public Houmao CLI surfaces (`fixture.py` and `houmao-mgr agents single --agent-id <id> ...`, wrapped by `hermes_lab.py` to enforce clean tmux and registry environments). Do not inject answers into agent workspaces, patch `$HERMES_HOME/config.yaml` behind Houmao's back, or accept an assistant's self-report without an independent second view.

Recommended execution order:

1. `service-lifecycle-and-reasoning`
2. `headless-continuation-and-boundaries`
3. `tui-native-control-and-detachment`
4. `multi-agent-isolation-and-daemon-ownership`
5. `mail-local-fs-round-trip`
6. `mail-stalwart-online-round-trip`

## Evidence

Save every artifact under `$RUN_TMP/evidence/agent-hermes/<scenario-slug>/`. Cleanup must preserve this tree.

| Artifact | Required Evidence |
| --- | --- |
| `doctor.json` | Repo `HEAD`, `houmao-mgr` and `hermes` versions, live daemon PIDs, `agent.reasoning_effort == "xhigh"`, tool posture, and mailbox health. |
| `prepare*.json`, `launch*.json` | Prepared backend (`hermes_service` / `hermes_headless` / `hermes_tui`), pool key/slot, `agent_id`, and isolated runtime paths. |
| `home-snapshot-*.json` | Read-only second view of the actual managed launch home: `config.yaml`, `SOUL.md` presence, projected `skills/`, `reasoning_provenance`, `hermes-daemon.json`, ACP bindings, TUI admission records, and headless turn summaries. |
| `state-*.json`, `prompt-*.json`, `relaunch*.json`, `interrupt*.json` | Public manager receipts, session ID continuity, terminal attachment transitions, and explicit refusal diagnostics for negative checks. |
| `redaction-audit.json` | Zero occurrences of `HERMES_MANAGED_API_KEY`, `ws://127.0.0.1`, `wss://127.0.0.1`, and `hermes-gateway-ticket.` across all public outputs. |
| `offline-*.json` | Run-local filesystem mailbox setup, `peek` non-mutation proof, message list/archive state, and SQLite `unread_count == 0` thread summaries. |
| `provision.json`, `stalwart-*.json` | Run-owned Stalwart accounts, JMAP inbox/archive observations, `inReplyTo`/`references` threading, and post-cleanup principal absence. |
| `transcript-*/` | Sanitized Hermes runtime artifacts (`stdout.jsonl`, `stderr.log`, `hermes-request.json`, `hermes-native-admission.json`, and home snapshot). |
| `stop.json`, `host-retired.json`, `evidence-check.txt` | Profile stop receipts, exact test-host retirement after profile cleanup, and surviving evidence inventory. |

## Cleanup

Stop the runs recorded by this session and verify their profiles are parked. Stop keeps the shared host available for other profiles. Clean any provisioned Stalwart principals and keep the evidence directory.

```bash
pixi run python "$LAB" stop \
  --run-dir "$RUN_A" \
  --evidence-root "$EVIDENCE" \
  | tee "$EVIDENCE/stop.json"
find "$EVIDENCE" -type f | sort > "$EVIDENCE/evidence-check.txt"
```

Pass additional `--run-dir` flags for every launched run in the session, and `--mail-config "$MAIL_CONFIG"` when Stalwart accounts were provisioned (add `--keep-accounts` only if intentionally retaining accounts for post-mortem review, then clean up with `stalwart-deprovision`).

To retire the test host, use the [isolation case cleanup](cases/multi-agent-isolation-and-daemon-ownership.md#remove-the-profiles-and-retire-the-host) after removing every retained worker profile in the selected owner root.

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `helpers/hermes_lab.py` | `pixi run python tests/instructional/agent-hermes/helpers/hermes_lab.py --help` | Doctor, managed-home and daemon second-view inspection, isolated `houmao-mgr` pass-through, redaction audit, local FS (`offline`) and Stalwart (`online`) mailbox orchestration, notifier control, transcript capture, and scoped cleanup. |
| `helpers/roles/hermes-worker.md` | `fixture.py prepare --system-prompt-file tests/instructional/agent-hermes/helpers/roles/hermes-worker.md` | Neutral engineering assistant role covering workspace tasks, mailbox skill workflow, and honest reporting of unavailable toolsets. |

## Case Index

| Case | Capability Tags | User-Visible Behavior |
| --- | --- | --- |
| [service-lifecycle-and-reasoning.md](cases/service-lifecycle-and-reasoning.md) | `hermes-service`, `acp`, `reasoning-xhigh`, `guardrails` | Default managed Hermes launches in `service` mode with `xhigh` reasoning projected to the real launch home, completes multi-turn workspace and skill work, survives exact relaunch and ACP interrupt, and enforces mode, tool-posture, and redaction guardrails. |
| [headless-continuation-and-boundaries.md](cases/headless-continuation-and-boundaries.md) | `hermes-headless`, `jsonl`, `continuation`, `guardrails` | Finite Hermes CLI workers continue one verified session across PIDs, accept literal stdin, survive exact relaunch, and reject an unprepared owner. |
| [tui-native-control-and-detachment.md](cases/tui-native-control-and-detachment.md) | `hermes-tui`, `ink`, `native-rpc`, `detachment` | Managed Hermes Ink runs in an isolated tmux pane with structured native RPC, valid durable admission receipts, busy refusal, human-turn queue tracking, Ink detachment without losing native settlement, session-switch reporting, and parser-op refusal. |
| [multi-agent-isolation-and-daemon-ownership.md](cases/multi-agent-isolation-and-daemon-ownership.md) | `multi-agent`, `isolation`, `shared-gateway` | Two projects share qualified dependencies and a native host, with separate profiles, sessions, workspaces, and scoped retirement. |
| [mail-local-fs-round-trip.md](cases/mail-local-fs-round-trip.md) | `multi-agent`, `offline-mail`, `filesystem`, `notifier` | Two managed Hermes agents (`service` + `tui`) exchange local filesystem email via `offline` notifiers and `houmao-process-emails-via-gateway`, preserving `peek` non-mutation, atomic `unread_count == 0` archive summaries, and negative notifier guardrails. |
| [mail-stalwart-online-round-trip.md](cases/mail-stalwart-online-round-trip.md) | `multi-agent`, `online-mail`, `stalwart`, `jmap`, `notifier` | Two managed Hermes agents (`service` + `tui`) exchange real threaded email over Stalwart JMAP with `online` notifiers, dual-channel `offline`/`online` isolation, and clean run-owned principal deprovisioning. |
