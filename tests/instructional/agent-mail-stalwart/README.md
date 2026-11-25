# Instructional Agent Mail Over a Real Stalwart Service

Agent-driven verification for a managed DSH Web agent that receives and answers real email through a Stalwart server. The suite exercises the online mailbox binding, gateway mail-notifier, provider-side delivery, agent reply and archive, and a two-agent round trip. It uses run-owned accounts and never starts, stops, resets, or reconfigures the selected mail service.

## Baseline Preconditions & Isolation

- Realwork checkout: Houmao repository root on `devel` (`$REPO_ROOT`, resolved via `git rev-parse --show-toplevel`).
- Manager: select a `houmao-mgr` built from this checkout, such as the editable Pixi or uv installation. Set `HOUMAO_MGR` to the selected executable.
- Model lane: self-hosted Qwen at `http://127.0.0.1:14888/v1`, model `Qwen/Qwen3.8-27B-FP8`, context window `262144`, maximum output tokens `8192`, reasoning map `{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}`, compatibility `{"supports_developer_role":false}`.
- DSH executable: the qualified build `0.2.2-rc.3` at `$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js`.
- Mail service: select an already-running Stalwart deployment. The bundled stack publishes JMAP discovery at `http://127.0.0.1:10080/.well-known/jmap` by default. [Local stack setup](../../../dockers/email-system/README.md)
- Accounts: select a sandbox domain that supports JMAP sending identities. The product provisioner creates two run-owned mailboxes with verified sending identities and Archive roles. Use a separate domain from the bundled development accounts on `houmao.localhost`.
- Endpoints: provide `trusted_jmap_origins` only for the exact origins approved for this run. Default loopback discovery and same-origin advertised endpoints require no extra approvals.
- Project-local temporary root: `$REPO_ROOT/tmp/instructional-tests/<run-id>/`. Store temporary scripts, runtime state, and proof artifacts under this Git-ignored directory.
- Isolation: each fixture prepares with `--tmux-server new` and owns a separate tmux socket, registry, runtime root, home, gateway port, and native Web origin. The run-owned mail accounts have unique fixture prefixes. Never touch the caller's default tmux server or any agent this run did not create.
- Concurrency: an agent accepts one active prompt at a time. Two runs against the same service must not share accounts; the run prefix and provider account isolation provide that separation.

## Shared-Service Boundary

The suite treats the Stalwart deployment as shared infrastructure. It does not start, stop, reset, or reconfigure the service, and it does not touch accounts or mail it did not create.

- Administrative authorization comes from the explicitly selected private credential file. Provisioning uses management authorization to ensure the domain and principals, then authenticates as each mailbox user to verify JMAP readiness. Live attachment uses each normal account credential source.
- `provision` creates the selected domain when absent. Use `--require-existing-domain` to require a domain prepared by the service owner. The run retains the shared domain and records `domain_created` in `provision.json`.
- `stop` verifies canonical principal names, ownership, and absence after deletion. After interrupted setup, stop any launched fixtures and use `deprovision` for provider cleanup.

## Launch

Use a private scratch directory for the fixture and its evidence.

```bash
umask 077
unset TMUX TMUX_PANE TMUX_TMPDIR
export REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"
export BUNDLE_ROOT="$REPO_ROOT/tests/instructional/agent-mail-stalwart"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-agent-mail"
export RUN_TMP="$REPO_ROOT/tmp/instructional-tests/$RUN_ID"
export HOUMAO_MGR="${HOUMAO_MGR:-$(command -v houmao-mgr || echo "$HOME/.local/share/uv/tools/houmao/bin/houmao-mgr")}"
export DSH_EXECUTABLE="${DSH_EXECUTABLE:-$REPO_ROOT/tmp/dsh/npm-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js}"
export BASE_URL="http://127.0.0.1:14888/v1"
export MODEL="Qwen/Qwen3.8-27B-FP8"
export EVIDENCE="$RUN_TMP/evidence/agent-mail-stalwart"
mkdir -p "$RUN_TMP/scripts" "$RUN_TMP/runtime/runs-a" "$RUN_TMP/runtime/runs-b" "$RUN_TMP/runtime/mail" "$EVIDENCE"
git check-ignore -q "$RUN_TMP" || { echo "RUN_TMP is not Git-ignored: $RUN_TMP" >&2; exit 1; }
chmod 700 "$RUN_TMP"
curl -fsS "$BASE_URL/models" >/dev/null
test -x "$DSH_EXECUTABLE"
```

Select the provider in an owner-private `$RUN_TMP/runtime/mail/service.json`. For the bundled stack, use the active Stalwart HTTP port and select its admin username and password from the stack's private configuration. Write those values into a separate owner-private JSON file with `user` and `password` keys. The configuration below uses a relative credential reference.

```json
{
  "jmap_url": "http://127.0.0.1:10080/.well-known/jmap",
  "management_url": "http://127.0.0.1:10080/jmap",
  "admin_credential_file": "admin.json"
}
```

Set the config and admin credential files to mode `0600`.

Provision the run-owned pair using an explicitly selected sandbox domain. The helper passes the configuration to the product provisioner and writes protected mailbox credential references into the private output config. Use a unique prefix. Pass `--require-existing-domain` when the provider owner has already prepared the domain.

```bash
export MAIL_PREFIX="houmao-e2e-$(date -u +%Y%m%dt%H%M%Sz)-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
export MAIL_CONFIG="$RUN_TMP/runtime/mail/mail-config.json"
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" provision \
  --mail-config "$RUN_TMP/runtime/mail/service.json" \
  --accounts-dir "$RUN_TMP/runtime/mail/accounts" \
  --output-config "$MAIL_CONFIG" \
  --domain houmao-jmap.example.com \
  --prefix "$MAIL_PREFIX" > "$EVIDENCE/provision.json"
```

To attach two existing normal accounts, prepare both with a usable sending identity, Inbox, Sent, and Archive, and provide an owner-private config with the following fields. The suite retains those accounts during cleanup. For an intranet HTTP deployment or an alternate advertised API or upload origin, add the operator-approved exact origins to `trusted_jmap_origins`. An HTTP entry sends the mailbox credential in plaintext to that origin.

```json
{
  "jmap_url": "https://mail.example.org/.well-known/jmap",
  "trusted_jmap_origins": ["https://jmap.example.org"],
  "accounts": {
    "a": {"login": "sender-login", "address": "sender@example.org", "credential_file": "/external/private/sender.json"},
    "b": {"login": "peer-login", "address": "peer@example.org", "credential_file": "/external/private/peer.json"}
  }
}
```

Prepare both agents from the tracked correspondent role.

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode unattended --tmux-server new \
  --role mail-a \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/mail-correspondent.md" \
  --run-root "$RUN_TMP/runtime/runs-a" > "$EVIDENCE/a-prepare.json"
export RUN_A="$(jq -r '.run_dir' "$EVIDENCE/a-prepare.json")"
test -f "$RUN_A/run.json"
```

Repeat for the peer with `--role mail-b` and `--run-root "$RUN_TMP/runtime/runs-b"`:

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model "$MODEL" --base-url "$BASE_URL" \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"low":"low","medium":"medium","off":"none","xhigh":"xhigh"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$DSH_EXECUTABLE" --prompt-mode unattended --tmux-server new \
  --role mail-b \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/mail-correspondent.md" \
  --run-root "$RUN_TMP/runtime/runs-b" > "$EVIDENCE/b-prepare.json"
export RUN_B="$(jq -r '.run_dir' "$EVIDENCE/b-prepare.json")"
test -f "$RUN_B/run.json"
```

Launch both agents, then attach the run-owned accounts to their live gateways. `configure` passes the selected discovery URL and any explicit approvals to the supported attach command, pins each online slot revision, and records the verified binding and origins in `$RUN_TMP/run-meta.json`.

```bash
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$RUN_A" > "$EVIDENCE/a-launch.json"
pixi run python "$REPO_ROOT/scripts/agents/test-fixtures/fixture.py" \
  launch --run-dir "$RUN_B" > "$EVIDENCE/b-launch.json"

export RUN_META="$RUN_TMP/run-meta.json"
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" configure \
  --run-a "$RUN_A" --run-b "$RUN_B" \
  --run-meta "$RUN_META" \
  --evidence-root "$EVIDENCE" \
  --mail-config "$MAIL_CONFIG" > "$EVIDENCE/configure.json"
export TAG="$(jq -r '.tag' "$RUN_META")"
```

## Doctor

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" doctor \
  --run-meta "$RUN_META" --mail-config "$MAIL_CONFIG" | tee "$EVIDENCE/doctor.json"
```

Doctor exits zero when the service liveness probe and any configured admin check pass, both JMAP accounts authenticate with an authorized sending identity, both agents are `available` with `gateway_health=healthy`, and both online bindings are `configured`, `available`, and match the run handle. It also reports inbox sample counts and any foreign unread mail that could wake a notifier.

## Drive

Resolve the run handles once. Every case command uses these variables rather than re-deriving IDs by hand.

```bash
export AGENT_A="$(jq -r '.agent_a_id' "$RUN_META")"
export AGENT_B="$(jq -r '.agent_b_id' "$RUN_META")"
export BINDING_A="$(jq -r '.online.a.binding_id' "$RUN_META")"
export BINDING_B="$(jq -r '.online.b.binding_id' "$RUN_META")"
export ADDR_A="$(jq -r '.mail.accounts.a.address' "$RUN_META")"
export ADDR_B="$(jq -r '.mail.accounts.b.address' "$RUN_META")"
```

Use the helper to target the recorded run, binding, and tag. Agent prompts are normal operator requests; do not include evaluation vocabulary in prompts seen by the agents.

## Evidence

Save every artifact under `$RUN_TMP/evidence/agent-mail-stalwart/<scenario-slug>/`.

| Artifact | Required evidence |
| --- | --- |
| `provision.json` | The run-owned account names, addresses, and the service domain. |
| `configure.json` / `run-meta.json` | Both online binding IDs, addresses, slot revisions, gateway URLs, and the verified discovery and API origins. |
| `doctor.json` | Service liveness, admin check, both JMAP identities, both agent availabilities, and both binding checks. |
| `notifier-*.json` | The enabled mode, interval, appendix, and later `last_notification_at_utc` / `open_count` advances. |
| `peer-send.json` | The provider submission receipt and the selected subject and recipients. |
| `b-inbox-*.json`, `b-archive.json` | The tagged provider message before handling and its Archive membership afterward. |
| `a-inbox-reply.json` | The reply message in the peer account, with sender, subject, and thread metadata. |
| `b-transcript-0.jsonl` | The recipient's actual DSH session transcript showing the mailbox tool calls and reply. |
| `stop.json` | Agent stop receipts, private tmux cleanup, verified principal absence, and the surviving evidence root. |

A pass requires the triggering action and the resulting state from two views: the agent transcript or command receipt, plus a read-only provider mailbox read. Cleanup must preserve `evidence/`.

## Cleanup

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" stop \
  --run-meta "$RUN_META" | tee "$EVIDENCE/stop.json"
find "$EVIDENCE" -type f | sort > "$EVIDENCE/evidence-check.txt"
```

`stop` targets the recorded pair and their verified private tmux servers. By default it deletes the run-owned principals, checks that they are absent, and preserves the evidence and shared domain. After partial setup, stop any launched fixtures and run `mail_lab.py deprovision --mail-config "$MAIL_CONFIG"` to verify provider cleanup.

To stop the agents but retain the accounts and mail for operator review, pass `--keep-accounts`:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" stop   --run-meta "$RUN_META" --keep-accounts | tee "$EVIDENCE/stop.json"
```

The stop receipt records `account_retention` with each address, login, and credential-file path. Review provider mail without relaunching agents:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" observe   --run-meta "$RUN_META" --role a --box inbox
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" observe   --run-meta "$RUN_META" --role a --box archive
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" content   --run-meta "$RUN_META" --role a --email-id "<provider id from observe>"
```

Retained accounts are intentional test state. Delete them with `deprovision` and the selected mail config when review is complete.

## Helpers

| Helper | Invocation | Purpose |
| --- | --- | --- |
| `helpers/mail_lab.py` | `pixi run python tests/instructional/agent-mail-stalwart/helpers/mail_lab.py doctor --help` | Provision run-owned accounts, attach online mail, run Doctor, drive provider and agent mail, copy transcripts, and stop the run. |
| `helpers/roles/mail-correspondent.md` | `fixture.py prepare --system-prompt-file tests/instructional/agent-mail-stalwart/helpers/roles/mail-correspondent.md` | General respondent role for both agents; not a narrow smoke-test role. |

The helper defaults to `$HOUMAO_MGR`, then `houmao-mgr` on `PATH`, then the uv tool path. Pass `--help` to list the setup, mail, evidence, and cleanup commands. Credential inputs are file references, and command receipts omit credential contents.

## Case Index

| Case | Capability tags | User-visible behavior |
| --- | --- | --- |
| [online-notifier-round-trip.md](cases/online-notifier-round-trip.md) | `multi-agent`, `dsh-web`, `online-mail`, `notifier` | A real email arrives from an external account, the managed agent wakes, reads it, replies, and archives it; the peer account receives the reply. |
| [two-agent-online-round-trip.md](cases/two-agent-online-round-trip.md) | `multi-agent`, `dsh-web`, `online-mail`, `peer-delivery` | Two managed agents exchange a work request and reply through the real mail service, each driven by its own notifier. |

## Last Self-Proof

Both cases passed on 2026-11-25 with `houmao-mgr 3.0.0rc7` from the development checkout, DSH `0.2.2-rc.3`, and the selected self-hosted Qwen model. The isolated Stalwart v0.15.5 stack used HTTP port 50001 for discovery, API calls, and uploads. Product provisioning supplied both account pairs with verified sending identities and Archive roles. Each pair attached directly to the advertised loopback origin under the default connection policy.

- `online-notifier-round-trip` used a provider-side send. The recipient's notifier woke it, and the provider recorded a single `confirmed` reply with matching RFC Message-ID references. The original moved from Inbox to Archive. The recipient transcript shows the list, read, reply, and archive operations.
- `two-agent-online-round-trip` used an agent-composed send. Both notifiers woke their agents, and the two provider mailboxes showed a single threaded reply with the request and reply read and archived. Both agent transcripts show their mail operations.
- Cleanup verified absence of all four run-owned principals and stopped all four private tmux servers. The second pair required the existing sandbox domain. A separate mixed-case cleanup check resolved canonical provider names and verified absence on repeat.

Evidence is under `tmp/instructional-tests/jmap-direct-proof.bLwJ0l/`. Find the case-specific provider proofs and transcripts under `round1/evidence/agent-mail-stalwart/` and `round2/evidence/agent-mail-stalwart/`. Each run includes a `stop.json` cleanup receipt, and `transcript-proof.json` records checks across the transcripts.

### Live-Service Rerun

Both cases were rerun on 2026-11-25 against the running project Stalwart at `http://127.0.0.1:10080` with `houmao-mgr 3.0.0rc7` at commit `e20dc9b8`. The service advertises `http://mail.houmao.localhost:10080`; the run approved that exact origin through `trusted_jmap_origins`, attached directly with `--trust-jmap-origin`, and used no proxy. The product provisioner created both account pairs with verified sending identities and Archive roles.

- Round 1 (`tmp/instructional-tests/20261125T042120Z-agent-mail-e2e/`): `provision` created `houmao-jmap.example.com`. Provider message `eaaaaab` reached the recipient; the notifier advanced at `2026-11-25T04:22:20Z`; reply `eaaaaac` carried body `confirmed` with matching `In-Reply-To` and `References`; the original moved to Archive. The recipient transcript shows the list, read, reply, and archive operations. Cleanup verified both run-owned principals absent.
- Round 2 (`tmp/instructional-tests/20261125T042259Z-agent-mail-e2e-r2/`): provisioning used `--require-existing-domain` and reported `domain_created=false`. Agent A sent subject `Mailbox path path-98b815`; agent B replied and archived the request; agent A's notifier archived the reply without another send. Both transcripts show their mail operations, and each side produced at most one reply. Cleanup verified both run-owned principals absent.
- `doctor` exited zero in both rounds with direct discovery, both JMAP identities valid, both agents `available`, and both online bindings `configured`. The shared domain `houmao-jmap.example.com` was retained by both rounds.
