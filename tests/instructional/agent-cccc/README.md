# Instructional CCCC Chat Suite

Agent-driven verification for two Houmao-managed DSH Web agents collaborating through the optional `houmao-cccc` gateway plugin. The suite covers peer discovery, handle-based `request_reply` round trips and receipt lookup, push batching, busy-agent waiting, in-turn gateway queue reads, and recovery of pending deliveries after reattachment. The graded flows use CCCC chat for all peer communication.

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved through `git rev-parse --show-toplevel`).
- **Manager and plugin.** Use matching builds of `houmao-mgr` and `houmao-cccc` with the fenced request presentation and receiver v2 support. Set `HOUMAO_MGR` and `HOUMAO_CCCC` to those two executables. The default is the workspace Pixi environment at `$REPO_ROOT/.pixi/envs/default/bin/`.
- Model lane: self-hosted Qwen at `http://127.0.0.1:14888/v1`, model `Qwen/Qwen3.8-27B-FP8`, context window `262144`, maximum output tokens `8192`, reasoning map `{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}`, compatibility `{"supports_developer_role":false}`.
- DSH executable: qualified build `0.2.2-rc.3` at `$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- **CCCC service.** Set `CCCC_ENDPOINT` to an already-running external-receiver protocol 2 service built from the tracked pin and patches. [Native build and service tooling](../../../tools/cccc/README.md)
- Shared-service boundary: the suite creates one uniquely named Group and two inert external-receiver Actors. It never starts, stops, resets, or reconfigures the selected CCCC service and never touches another Group or grant.
- Local service identity: the default runtime descriptor is `$HOME/.local/share/houmao-cccc-receiver-v2-queue/runtime.json`; the binary is `$HOME/.local/share/houmao-cccc-receiver-v2-queue/target/debug/cccc`. Configuration verifies the selected PID, `/proc` executable, build receipt, protocol 2, the complete tracked patch series, and binary hash. Omit both identity arguments for a remote or separately administered service; negotiated binding/capability checks remain mandatory.
- Private external root: Houmao rejects plugin credential files inside the checkout. Set `CCCC_PRIVATE_ROOT` to an owner-private directory outside `$REPO_ROOT`, defaulting to `$HOME/.local/state/houmao/cccc-instructional`. The helper creates one run-specific subdirectory, uses the supported grant exporter, and deletes only the two run-owned credential documents during cleanup.
- Project-local temporary root: `$REPO_ROOT/tmp/instructional-tests/<run-id>/`. Temporary scripts, fixture homes, plugin selections without tokens, and evidence remain under this Git-ignored directory. The external credential directory is a product-required exception and contains no evidence.
- Isolation: each fixture prepares with `--tmux-server new` and owns a private tmux socket, registry, runtime root, home, gateway port, and native Web origin. The two agents have distinct Houmao UUIDs and CCCC Actor registrations. Never touch the caller's default tmux server or an agent this run did not create.
- Operator recovery channel: `configure` joins each agent to its run-local offline filesystem mailbox. `recovery-post` is available only for operator-originated recovery after a failure; it requires an explicit confirmation flag and invalidates the graded flow. It is not a peer backup channel and cannot turn a CCCC failure into a pass.
- Concurrency: parallel runs need distinct run IDs and fixture roots. The unique Group isolates CCCC state on a shared service. Do not double-drive one agent or reuse a run handle.

## Launch

Select the workspace manager and plugin so both match the checkout under test. `pixi install` is sufficient; no separate uv tool install is used:

```bash
pixi install
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
export HOUMAO_MGR="${HOUMAO_MGR:-$REPO_ROOT/.pixi/envs/default/bin/houmao-mgr}"
export HOUMAO_CCCC="${HOUMAO_CCCC:-$REPO_ROOT/.pixi/envs/default/bin/houmao-cccc}"
export DSH_EXECUTABLE="${DSH_EXECUTABLE:-$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js}"
export BASE_URL="http://127.0.0.1:14888/v1"
export MODEL="Qwen/Qwen3.8-27B-FP8"
export CCCC_ENDPOINT="${CCCC_ENDPOINT:?Set the receiver v2 service endpoint}"
export CCCC_SERVICE_RUNTIME="${CCCC_SERVICE_RUNTIME:-$HOME/.local/share/houmao-cccc-receiver-v2-queue/runtime.json}"
export CCCC_PROVIDER_BINARY="${CCCC_PROVIDER_BINARY:-$HOME/.local/share/houmao-cccc-receiver-v2-queue/target/debug/cccc}"
export CCCC_PRIVATE_ROOT="${CCCC_PRIVATE_ROOT:-$HOME/.local/state/houmao/cccc-instructional}"
mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime/runs-a" "$RUN_TMP/runtime/runs-b" "$EVIDENCE"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored" >&2; exit 1; }
chmod 700 "$RUN_TMP"
test -x "$HOUMAO_MGR" && test -x "$HOUMAO_CCCC" && test -x "$DSH_EXECUTABLE"
test ! -e "$CCCC_PRIVATE_ROOT" || test -d "$CCCC_PRIVATE_ROOT"
curl -fsS "$BASE_URL/models" >/dev/null
curl -fsS "$CCCC_ENDPOINT/api/v1/health" >/dev/null
"$HOUMAO_MGR" --version
"$HOUMAO_CCCC" --version > "$EVIDENCE/cccc-version.txt"
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

Pin the intended `xhigh` reasoning preset in each generated profile before launch:

```bash
"$HOUMAO_MGR" --print-json project --project-dir "$RUN_A/workdir" \
  profile set --name fixture-agent --reasoning-level 3 > "$EVIDENCE/a-xhigh-profile.json"
"$HOUMAO_MGR" --print-json project --project-dir "$RUN_B/workdir" \
  profile set --name fixture-agent --reasoning-level 3 > "$EVIDENCE/b-xhigh-profile.json"
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

Each case uses a fresh neutral token, a case-specific evidence directory, and an explicit effective delivery policy:

```bash
export TOKEN="desk-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
export CASE_SLUG=two-agent-chat-round-trip
export CASE_EVIDENCE="$EVIDENCE/$CASE_SLUG"
mkdir -p "$CASE_EVIDENCE"
```

Use `prompt` for ordinary operator requests. Agents choose and execute their own local `houmao-cccc` commands or matching local plugin HTTP routes. The helper never sends or replies to chat on their behalf. `cccc` exposes only read-only binding, capability, member, history, and delivery inspection. `delivery` sets and waits for the effective pull/ASAP/batch policy. `verify` checks native event ancestry and exact attempt states. `verify-batch` validates the compact native request fence, ordered entries, handles, and absence of private routing data. `audit` rejects peer mail and provider-admin tool calls.

Run the pull round trip first, then push batch and busy ASAP. Run the queue-access case with a receiver that advertises the gateway queue feature. Run gateway reconnect last. Each case sets and records its own delivery policy. Re-run Doctor after the reconnect case reattaches Agent B's gateway.

## Evidence

Save artifacts under `$RUN_TMP/evidence/agent-cccc/<scenario-slug>/`. Every scenario requires the triggering operator prompt, its effective delivery policy, the compact native request fence, both native DSH transcripts, CCCC history, delivery attempts, and a channel audit. `verify` supplies request/reply ancestry and attempt proof; `verify-batch` supplies the one-fence and routing-privacy proof.

| Artifact | Required evidence |
| --- | --- |
| `configure.json` / `run-meta.json` | Run-owned Group, owner/Actor/binding identities, gateway coordinates, grant IDs without tokens, and body-preservation snapshots. |
| `cccc-version.txt` | Installed `houmao-cccc --version` output for the selected matching CLI. |
| `doctor*.json` | Compatible provider identity, healthy agents, connected bindings, stable native bodies, and operator recovery mailbox registrations. |
| `delivery.json` | Active effective pull, ASAP, or timed-batch policy and its revision. |
| `round-trip.json` | One native request, its threaded agent-authored reply, message modes, ancestry, and exact delivery-attempt states. |
| `native-request.json` / `native-batch.json` | Exactly one compact request fence with ordered entries, distinct handles, and no binding, event, token, or repeated-URL leakage. |
| `pending.json` / `attempt-continuity.json` | Provider pending work before reattachment and the same event/attempt identity after it becomes accepted. |
| `not-delivered-*.json` / `delivered-*.json` | Native-token absence while busy or detached, followed by presence after readiness or reattachment. |
| `queue-proof.json` | One in-turn peek, pop, acknowledgment, and recovery flow. Native reply parents match the acknowledged attempts, and ordinary notification resumes with the next eligible attempt. |
| `a-transcript-*.jsonl`, `b-transcript-*.jsonl` | Actual discovery, token-based send, handle-based reply, local file work, and incoming CCCC turns. |
| `channel-audit.json` | Actual bash tool calls and zero Houmao mail, CCCC Mail, or provider-admin fallback. |
| `stop.json` | Owned-agent and private-tmux cleanup, grant revocation, verified Group absence, credential deletion, and surviving evidence root. |

A pass requires agreement among transcripts, the compact request fence, gateway receipts, and native CCCC history. A final assistant summary is never sufficient proof. Cleanup must preserve `evidence/`.

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
| `helpers/cccc_lab.py` | `pixi run python tests/instructional/agent-cccc/helpers/cccc_lab.py --help` | Provision, attach, Doctor, set delivery policy, prompt, inspect, verify compact requests and handle-based replies, audit, recover, reattach, and clean up the chat-only pair. |
| `helpers/verify_queue_access.py` | `pixi run python tests/instructional/agent-cccc/helpers/verify_queue_access.py --help` | Verify the queue scenario from native queue calls, provider attempts, reply ancestry, and ordinary-delivery resumption. |
| `helpers/roles/cccc-correspondent.md` | `fixture.py prepare --system-prompt-file tests/instructional/agent-cccc/helpers/roles/cccc-correspondent.md` | General worker and CCCC correspondent role; forbids all peer-mail channels and provider administration. |

`cccc_lab.py` defaults to `$HOUMAO_MGR` and `$HOUMAO_CCCC`, then the workspace Pixi tool paths. Run any subcommand with `--help` for its exact inputs. Error output excludes credential contents and provider response bodies.

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [two-agent-chat-round-trip.md](cases/two-agent-chat-round-trip.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `peer-discovery` | Two real agents discover one another, perform file-reading work, and complete a threaded CCCC `request_reply` exchange without mail. |
| [push-batch-replies-by-handle.md](cases/push-batch-replies-by-handle.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `push`, `batching` | One compact native prompt carries two ordered requests, and the recipient authors two exact-parent replies. |
| [busy-push-waits-for-idle.md](cases/busy-push-waits-for-idle.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `push-asap` | A busy recipient receives the pending request once after becoming idle. |
| [gateway-queue-wait-and-read.md](cases/gateway-queue-wait-and-read.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `queue-access` | One recipient yields for a notification, then reads staged replies during an active turn and receives the next request when ready. |
| [gateway-reconnect-pending-delivery.md](cases/gateway-reconnect-pending-delivery.md) | `multi-agent`, `dsh-web`, `cccc-chat`, `gateway-recovery` | Gateway reattachment preserves the body and binding and delivers pending CCCC work. |

## Receiver v2 Self-Proof

On 2026-11-25, the revised five-case suite passed against commit `555e4f2d693c95fcd7046baa7779e63e3ac009e8` with the test-bundle revisions in the working tree. Two real fixture-managed DSH Web `0.2.2-rc.3` agents used self-hosted `Qwen/Qwen3.8-27B-FP8` with `xhigh` reasoning and workspace builds of `houmao-mgr 3.0.0rc8` and `houmao-cccc 0.3.0`. The isolated receiver v2 service at `127.0.0.1:18852` used all four tracked provider patches at upstream revision `d12732ebd6dfdbc260a59a286bd5e510d04d4832`; its verified binary SHA-256 was `a55d121555b794130ffd2065c97d8612cbc3637d721646e5716ddb69b924d71e`.

- Pull round trip request `ffc7e0d823c147b9a51273e392e4f0c2` used native request handle `msg_cccc.CQ58yOedNe9tyIMf`, recorded one accepted attempt `ccded319-4240-4901-8c5d-2713f178172c`, and received reply `7328f32a5f574bbc8b6923e29e3fcf70` with text `cobalt desk-eb5785` and exact parent ancestry. Both agents inspected the handoff with `chat deliveries --handle`, their receipts matched the independent lookup, and both used `members --group`.
- Timed push batch produced one native message `7eba3374-784b-4c4a-8c6c-00dee5a749ac` with one request fence, two distinct handles, original CCCC order, timestamps, and sender. Requests `3550587187a440e284c9a14b16ee3155` and `fa3413adafa148d580e9adb7763a0d11` each had one accepted attempt and one exact-parent reply.
- Busy ASAP recorded zero token occurrences in B's native transcript during a real shell turn. After readiness, request `3fd545d909c4483995fc3469f0678d5f` had one accepted handoff and reply `ca8c5b4fcd5b4514961d4c1dd1a96715`.
- Queue access completed both the yielded ordinary notification and the in-turn queue path. The two staged replies produced `gateway_tool_read` attempts `b436b9fc-00e9-48d6-bb71-0bcb4e5461c6` and `bcd096b8-4705-4883-a0bd-88a16bbb9cf2`, exact confirmations `d7453a098f0644e99df0d20bc6355826` and `49184c33f0ec43008559ea4ea76f5add`, and the follow-up moved from `offered` to `accepted` on attempt `8ab6958e-9fba-44f9-8bed-5ed63cb2db63`.
- Reconnect preserved the native body and Actor binding. Attempt `623c432c-9a4f-4d8e-ad54-1032ded9b2f9` for event `785a6f5af1b9499196e032daa129f33d` moved from `pending` to `accepted`, with fresh handle `msg_cccc.vTSyJBwqvhe3SOGH` and reply `7c71dfd930b04ed69a2e6631537c11d8`.
- All five channel audits passed. Cleanup stopped both agents and private tmux servers, revoked both grants, deleted and verified absence of the run Group, removed both external credential files, and retained all 121 evidence files.

Private evidence is under `tmp/instructional-tests/20261125T140656Z-agent-cccc-v2-queue/evidence/agent-cccc/`. Each scenario keeps its native request fence, receipt identity, reply and delivery proofs, both transcripts, CCCC history, and channel audit. The four-patch receiver service used for this run was stopped after cleanup; the persistent v1 services on ports 8848 and 8849 were not touched.

## Historical Receiver v1 Self-Proof

All three cases passed on 2026-11-25 with `houmao-mgr 3.0.0rc7`, `houmao-cccc 0.2.0`, DSH `0.2.2-rc.3`, and self-hosted `Qwen/Qwen3.8-27B-FP8` at commit `e20dc9b882f611575e2199ef89fade36e93f8a51`. The real patched CCCC protocol-1 service at `127.0.0.1:8849` matched its managed build receipt; no agents, model, provider transport, or delivery receipts were mocked.

- `two-agent-chat-round-trip`: request `2e45a2bd6ad1443b9083f08e757625a6` had one `accepted` handoff. B's native read tool returned `cobalt`, and its threaded native `send` reply `aaed2d646c944123beaae34de437be80` contained the file word and marker. The channel audit found no peer mail or provider administration.
- `busy-refusal-and-explicit-retry`: B's real `sleep 45` turn produced initial `refused`. B's transcript had no request token after it became ready. A used `chat retry`, producing chronological `refused,accepted` attempts and threaded reply `f81a11a114fa46b4a1d8749988e47c0e` on the original request.
- `gateway-reconnect-no-replay`: B's gateway detach produced initial `failed`. Reattachment preserved the binding ID, native PID, supervisor identity, and native session. B had no request token before A's explicit retry; final attempts were `failed,accepted` with threaded reply `e7895ebe386c488d89056fb0b8230a84`.
- Cleanup stopped both agents and private tmux servers, revoked both grants, deleted and verified absence of Group `g_2e3c096c7ffb`, and removed both external Actor credential files. A repeated stop returned the same clean result with both agents and sockets already absent. All 63 evidence files present at cleanup survived.

Evidence is under `tmp/instructional-tests/20261125T061701Z-agent-cccc/evidence/agent-cccc/`; each case has `round-trip.json`, `final-recheck.json`, native history/deliveries, both transcripts, and `channel-audit.json`. The durable report is `.imsight-arts/project-mgr/agent-driven-testing/reports/20261125T062600Z-agent-cccc.md`.

Three harness gaps were corrected and re-verified: initialize the run-local offline store before mailbox registration, read DSH Web's nested liveness/readiness state instead of headless-only fields, and compare CCCC's newest-first receipts in chronological order. The role was also aligned with the product's supported local plugin HTTP alternative to the CLI. A separate first setup attempt under `tmp/instructional-tests/20261125T061546Z-agent-cccc/` was cleaned without running a scenario. No product regression was observed.

The operator-only filesystem recovery channel was registered but not invoked. Other clients/models, remote CCCC deployments, provider crash/restart, CCCC Mail, and all agent-to-agent mail remain outside this suite's verified scope.
