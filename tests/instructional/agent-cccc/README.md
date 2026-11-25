# Instructional CCCC Chat Suite

Agent-driven verification for two Houmao-managed DSH Web agents collaborating through the optional `houmao-cccc` gateway plugin. The suite covers peer discovery, `request_reply` round trips, push batching, busy-agent waiting, and recovery of pending deliveries after reattachment. The graded flows use CCCC chat for all peer communication.

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved through `git rev-parse --show-toplevel`).
- **Manager and plugin.** Select matching builds of `houmao-mgr` and `houmao-cccc` with the fenced request presentation and receiver v2 support. Set `HOUMAO_MGR` and `HOUMAO_CCCC` to those two executables. The default is the uv tool environment at `$HOME/.local/share/uv/tools/houmao/bin/`.
- Model lane: self-hosted Qwen at `http://127.0.0.1:14888/v1`, model `Qwen/Qwen3.8-27B-FP8`, context window `262144`, maximum output tokens `8192`, reasoning map `{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}`, compatibility `{"supports_developer_role":false}`.
- DSH executable: qualified build `0.2.2-rc.3` at `$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- **CCCC service.** Set `CCCC_ENDPOINT` to an already-running external-receiver protocol 2 service built from the tracked pin and patches. [Native build and service tooling](../../../tools/cccc/README.md)
- Shared-service boundary: the suite creates one uniquely named Group and two inert external-receiver Actors. It never starts, stops, resets, or reconfigures the selected CCCC service and never touches another Group or grant.
- Local service identity: the default runtime descriptor is `$HOME/.local/share/houmao-cccc-receiver/runtime.json`; the binary is `$HOME/.local/share/houmao-cccc-receiver/target/debug/cccc`. Configuration verifies the selected PID, `/proc` executable, build receipt, protocol, patch identity, and binary hash. Omit both identity arguments for a remote or separately administered service; negotiated binding/capability checks remain mandatory.
- Private external root: Houmao rejects plugin credential files inside the checkout. Set `CCCC_PRIVATE_ROOT` to an owner-private directory outside `$REPO_ROOT`, defaulting to `$HOME/.local/state/houmao/cccc-instructional`. The helper creates one run-specific subdirectory, uses the supported grant exporter, and deletes only the two run-owned credential documents during cleanup.
- Project-local temporary root: `$REPO_ROOT/tmp/instructional-tests/<run-id>/`. Temporary scripts, fixture homes, plugin selections without tokens, and evidence remain under this Git-ignored directory. The external credential directory is a product-required exception and contains no evidence.
- Isolation: each fixture prepares with `--tmux-server new` and owns a private tmux socket, registry, runtime root, home, gateway port, and native Web origin. The two agents have distinct Houmao UUIDs and CCCC Actor registrations. Never touch the caller's default tmux server or an agent this run did not create.
- Operator recovery channel: `configure` joins each agent to its run-local offline filesystem mailbox. `recovery-post` is available only for operator-originated recovery after a failure; it requires an explicit confirmation flag and invalidates the graded flow. It is not a peer backup channel and cannot turn a CCCC failure into a pass.
- Concurrency: parallel runs need distinct run IDs and fixture roots. The unique Group isolates CCCC state on a shared service. Do not double-drive one agent or reuse a run handle.

## Launch

Select the installed manager and local plugin. If the plugin is absent from the existing uv environment, install the local package without resolving or replacing the manager's dependencies:

```bash
uv pip install --python "$HOME/.local/share/uv/tools/houmao/bin/python" \
  --no-deps "$REPO_ROOT/packages/houmao-cccc"
```

Create the private run workspace and verify the live preconditions:

```bash
umask 077
unset TMUX TMUX_PANE TMUX_TMPDIR
export REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
export BUNDLE_ROOT="$REPO_ROOT/tests/instructional/agent-cccc"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-agent-cccc"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export EVIDENCE="$RUN_TMP/evidence/agent-cccc"
export RUN_META="$RUN_TMP/run-meta.json"
export HOUMAO_MGR="${HOUMAO_MGR:-$HOME/.local/share/uv/tools/houmao/bin/houmao-mgr}"
export HOUMAO_CCCC="${HOUMAO_CCCC:-$HOME/.local/share/uv/tools/houmao/bin/houmao-cccc}"
export DSH_EXECUTABLE="${DSH_EXECUTABLE:-$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js}"
export BASE_URL="http://127.0.0.1:14888/v1"
export MODEL="Qwen/Qwen3.8-27B-FP8"
export CCCC_ENDPOINT="${CCCC_ENDPOINT:?Set the receiver v2 service endpoint}"
export CCCC_SERVICE_RUNTIME="${CCCC_SERVICE_RUNTIME:-$HOME/.local/share/houmao-cccc-receiver/runtime.json}"
export CCCC_PROVIDER_BINARY="${CCCC_PROVIDER_BINARY:-$HOME/.local/share/houmao-cccc-receiver/target/debug/cccc}"
export CCCC_PRIVATE_ROOT="${CCCC_PRIVATE_ROOT:-$HOME/.local/state/houmao/cccc-instructional}"
mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime/runs-a" "$RUN_TMP/runtime/runs-b" "$EVIDENCE"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored" >&2; exit 1; }
chmod 700 "$RUN_TMP"
test -x "$HOUMAO_MGR" && test -x "$HOUMAO_CCCC" && test -x "$DSH_EXECUTABLE"
test ! -e "$CCCC_PRIVATE_ROOT" || test -d "$CCCC_PRIVATE_ROOT"
curl -fsS "$BASE_URL/models" >/dev/null
curl -fsS "$CCCC_ENDPOINT/api/v1/health" >/dev/null
"$HOUMAO_MGR" --version
"$HOUMAO_CCCC" --help >/dev/null
```

Prepare two real DSH Web agents with the general CCCC correspondent role:

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode unattended --tmux-server new \
  --role cccc-a --system-prompt-file "$BUNDLE_ROOT/helpers/roles/cccc-correspondent.md" \
  --run-root "$RUN_TMP/runtime/runs-a" > "$EVIDENCE/a-prepare.json"
export RUN_A="$(jq -r '.run_dir' "$EVIDENCE/a-prepare.json")"

pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode unattended --tmux-server new \
  --role cccc-b --system-prompt-file "$BUNDLE_ROOT/helpers/roles/cccc-correspondent.md" \
  --run-root "$RUN_TMP/runtime/runs-b" > "$EVIDENCE/b-prepare.json"
export RUN_B="$(jq -r '.run_dir' "$EVIDENCE/b-prepare.json")"
test -f "$RUN_A/run.json" && test -f "$RUN_B/run.json"
```

Launch both agents and seed one ordinary native conversation in each before attaching CCCC. The work file supports the first scenario and is not a communication channel:

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$RUN_A" > "$EVIDENCE/a-launch.json"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$RUN_B" > "$EVIDENCE/b-launch.json"
printf 'cobalt\n' > "$RUN_A/workdir/shared-note.txt"
printf 'cobalt\n' > "$RUN_B/workdir/shared-note.txt"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prompt \
  --run-dir "$RUN_A" --prompt "Remember the phrase amber desk and reply with the single word ready." \
  > "$EVIDENCE/a-seed.json"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prompt \
  --run-dir "$RUN_B" --prompt "Remember the phrase silver lamp and reply with the single word ready." \
  > "$EVIDENCE/b-seed.json"
```

Provision the Group and grants, join the operator-only recovery mailboxes, and attach both plugins. Credential contents never enter the run metadata or agent briefs:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" configure \
  --run-a "$RUN_A" --run-b "$RUN_B" --endpoint "$CCCC_ENDPOINT" \
  --service-runtime "$CCCC_SERVICE_RUNTIME" --provider-binary "$CCCC_PROVIDER_BINARY" \
  --private-root "$CCCC_PRIVATE_ROOT" --run-meta "$RUN_META" \
  --evidence-root "$EVIDENCE" > "$EVIDENCE/configure.json"
```

## Doctor

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" doctor \
  --run-meta "$RUN_META" | tee "$EVIDENCE/doctor.json"
```

Doctor exits zero only when the selected service identity remains valid, both gateways and native bodies are healthy, both CCCC bindings are connected to the recorded owner/Group/Actor with stable binding IDs, native PID/supervisor/conversation identities match the pre-attachment snapshots, and both operator-only offline recovery mailboxes remain registered. Run Doctor before the first scenario, on each fresh run, and after every failed or surprising drive.

## Drive

Each case uses a fresh neutral token and a case-specific evidence directory:

```bash
export TOKEN="desk-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
export CASE_EVIDENCE="$EVIDENCE/two-agent-chat-round-trip"
mkdir -p "$CASE_EVIDENCE"
```

Use `prompt` for ordinary operator requests. Agents choose and execute their own local `houmao-cccc` commands or matching local plugin HTTP routes. The helper never sends or replies to chat on their behalf. `cccc` exposes only read-only binding, capability, member, history, and delivery inspection. `verify` checks native event ancestry and exact attempt states; `audit` rejects peer mail and provider-admin tool calls.

Run the pull round trip first, then the push batch and busy ASAP cases. Run the gateway reconnect case last and re-run Doctor after it reattaches Agent B's gateway. Each case establishes its own delivery prerequisites.

## Evidence

Save artifacts under `$RUN_TMP/evidence/agent-cccc/<scenario-slug>/`. Every scenario requires the triggering operator prompt, both native DSH transcripts, CCCC history, delivery attempts, and a channel audit. `verify` supplies a compact native request/reply and attempt proof.

| Artifact | Required evidence |
| --- | --- |
| `configure.json` / `run-meta.json` | Run-owned Group, owner/Actor/binding identities, gateway coordinates, grant IDs without tokens, and body-preservation snapshots. |
| `doctor.json` | Compatible provider identity, healthy agents, connected bindings, stable native bodies, and operator recovery mailbox registrations. |
| `round-trip.json` | One native request, its threaded agent-authored reply, message modes, ancestry, and exact delivery-attempt states. |
| `native-batch.json` | Exactly one native request fence with the two distinct ordered message handles. |
| `pending.json` / `not-delivered-*.json` | Provider pending work and absence of a native prompt while the body is busy or detached. |
| `a-transcript-*.jsonl`, `b-transcript-*.jsonl` | Actual discovery, send/reply/retry, local file work, and incoming CCCC turns. |
| `channel-audit.json` | Actual bash tool calls and zero Houmao mail, CCCC Mail, or provider-admin fallback. |
| `stop.json` | Owned-agent and private-tmux cleanup, grant revocation, verified Group absence, credential deletion, and surviving evidence root. |

A pass requires agreement among transcripts, gateway receipts, and native CCCC history. A final assistant summary is never sufficient proof. Cleanup must preserve `evidence/`.

## Cleanup

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" stop \
  --run-meta "$RUN_META" | tee "$EVIDENCE/stop.json"
find "$EVIDENCE" -type f | sort > "$EVIDENCE/evidence-check.txt"
```

`stop` disconnects the two receivers where possible, stops only the recorded agents and verified private tmux servers, revokes only the two recorded grants, deletes only the recorded Group, verifies its absence, deletes the two external credential documents, and leaves evidence untouched. It is safe to retry after a partial cleanup; do not replace it with process-name kills or shared-service lifecycle commands.

If an agent is wedged and an operator recovery note is necessary, first capture the failed CCCC evidence and classify the scenario as failed or blocked. Only then use the explicitly confirmed offline operator path:

```bash
pixi run python "$BUNDLE_ROOT/helpers/cccc_lab.py" recovery-post \
  --run-meta "$RUN_META" --role b --confirm-operator-recovery \
  --subject "Operator recovery" --body "Stop the current work and become ready for shutdown."
```

This command never represents peer communication and cannot contribute to a passing scenario.

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `helpers/cccc_lab.py` | `pixi run python tests/instructional/agent-cccc/helpers/cccc_lab.py --help` | Provision, attach, Doctor, prompt, inspect, verify, audit, recover, reattach, and clean up the chat-only pair. |
| `helpers/roles/cccc-correspondent.md` | `fixture.py prepare --system-prompt-file tests/instructional/agent-cccc/helpers/roles/cccc-correspondent.md` | General worker and CCCC correspondent role; forbids all peer-mail channels and provider administration. |

`cccc_lab.py` defaults to `$HOUMAO_MGR` and `$HOUMAO_CCCC`, then their uv tool paths. Run any subcommand with `--help` for its exact inputs. Error output excludes credential contents and provider response bodies.

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [two-agent-chat-round-trip.md](cases/two-agent-chat-round-trip.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `peer-discovery` | Two real agents discover one another, perform file-reading work, and complete a threaded CCCC `request_reply` exchange without mail. |
| [push-batch-replies-by-handle.md](cases/push-batch-replies-by-handle.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `push`, `batching` | One compact native prompt carries two ordered requests, and the recipient authors two exact-parent replies. |
| [busy-push-waits-for-idle.md](cases/busy-push-waits-for-idle.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `push-asap` | A busy recipient receives the pending request once after becoming idle. |
| [gateway-reconnect-pending-delivery.md](cases/gateway-reconnect-pending-delivery.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `gateway-recovery` | Gateway reattachment preserves the body and binding and delivers pending CCCC work. |

## Receiver v2 Self-Proof

On 2026-11-25, two real fixture-managed DSH Web `0.2.2-rc.3` agents used self-hosted `Qwen/Qwen3.8-27B-FP8` with workspace builds of `houmao-mgr 3.0.0rc8` and `houmao-cccc 0.3.0`. The isolated receiver v2 service at `127.0.0.1:18851` used the tracked provider patches at upstream revision `d12732ebd6dfdbc260a59a286bd5e510d04d4832`. Its running binary SHA-256 was `ebb619dccb0e598f18f4afed590413366b507247d7187ed8a3af1f4722d22864`.

- Push batch produced one native user message `18f31543-18a1-44dd-ade5-4bedf6329f8e` with one request fence, two distinct reply handles, and the original CCCC order, timestamps, and sender. CCCC recorded one accepted attempt per message, and each authored reply referenced its exact native parent.
- Busy ASAP kept the new message out of the recipient's native transcript during a live shell turn. After idle, CCCC recorded one accepted handoff and a threaded reply to the waiting message.
- Reconnect preserved the native body and Actor binding. The same provider attempt `eb4782e9-bca8-4449-961f-a0c86ef40451` moved from pending while detached to accepted after reattachment, then received an authored reply.
- All three channel audits passed. Cleanup stopped the run-owned agents, removed their Group and credential files, and retained the evidence.

Private evidence is under `tmp/instructional-tests/cccc-v2-recheck-s2DVO8/evidence/`. The native batch check is `push-batch-replies-by-handle/native-batch.json`. Read the matching `first-reply.json`, `second-reply.json`, and scenario round-trip reports for exact receipts. These are real-agent observations from the workspace builds. Independent installed-wheel and deterministic checks have their own reports.

## Historical Receiver v1 Self-Proof

All three cases passed on 2026-11-25 with `houmao-mgr 3.0.0rc7`, `houmao-cccc 0.2.0`, DSH `0.2.2-rc.3`, and self-hosted `Qwen/Qwen3.8-27B-FP8` at commit `e20dc9b882f611575e2199ef89fade36e93f8a51`. The real patched CCCC protocol-1 service at `127.0.0.1:8849` matched its managed build receipt; no agents, model, provider transport, or delivery receipts were mocked.

- `two-agent-chat-round-trip`: request `2e45a2bd6ad1443b9083f08e757625a6` had one `accepted` handoff. B's native read tool returned `cobalt`, and its threaded native `send` reply `aaed2d646c944123beaae34de437be80` contained the file word and marker. The channel audit found no peer mail or provider administration.
- `busy-refusal-and-explicit-retry`: B's real `sleep 45` turn produced initial `refused`. B's transcript had no request token after it became ready. A used `chat retry`, producing chronological `refused,accepted` attempts and threaded reply `f81a11a114fa46b4a1d8749988e47c0e` on the original request.
- `gateway-reconnect-no-replay`: B's gateway detach produced initial `failed`. Reattachment preserved the binding ID, native PID, supervisor identity, and native session. B had no request token before A's explicit retry; final attempts were `failed,accepted` with threaded reply `e7895ebe386c488d89056fb0b8230a84`.
- Cleanup stopped both agents and private tmux servers, revoked both grants, deleted and verified absence of Group `g_2e3c096c7ffb`, and removed both external Actor credential files. A repeated stop returned the same clean result with both agents and sockets already absent. All 63 evidence files present at cleanup survived.

Evidence is under `tmp/instructional-tests/20261125T061701Z-agent-cccc/evidence/agent-cccc/`; each case has `round-trip.json`, `final-recheck.json`, native history/deliveries, both transcripts, and `channel-audit.json`. The durable report is `.imsight-arts/project-mgr/agent-driven-testing/reports/20261125T062600Z-agent-cccc.md`.

Three harness gaps were corrected and re-verified: initialize the run-local offline store before mailbox registration, read DSH Web's nested liveness/readiness state instead of headless-only fields, and compare CCCC's newest-first receipts in chronological order. The role was also aligned with the product's supported local plugin HTTP alternative to the CLI. A separate first setup attempt under `tmp/instructional-tests/20261125T061546Z-agent-cccc/` was cleaned without running a scenario. No product regression was observed.

The operator-only filesystem recovery channel was registered but not invoked. Other clients/models, remote CCCC deployments, provider crash/restart, CCCC Mail, and all agent-to-agent mail remain outside this suite's verified scope.
