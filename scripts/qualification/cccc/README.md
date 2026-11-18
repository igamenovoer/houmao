# CCCC Qualification Utilities

These utilities test independent distributions and actual provider behavior. They are development tools, outside both released Python distributions. Runtime state, installed environments, model homes, and credentials must remain outside the checkout.

## Prepare the Provider

Follow [the native deployment instructions](../../../tools/cccc/README.md#prepare-the-compatible-receiver-service) to prepare the tracked patch and start the compatible service. Select the dedicated loopback instance explicitly. A stock CCCC health response does not establish receiver compatibility.

```bash
HOUMAO_CCCC_TEST_URL=http://127.0.0.1:8849 \
  pixi run pytest -q tests/integration/cccc/test_receiver_provider.py
HOUMAO_CCCC_TEST_URL=http://127.0.0.1:8849 \
HOUMAO_CCCC_STOCK_TEST_URL=http://127.0.0.1:8848 \
  pixi run pytest -q tests/integration/cccc/test_email_coexistence.py
```

Crash recovery starts and kills only owned disposable instances. It requires the compatible binary and an external scratch parent:

```bash
HOUMAO_CCCC_TEST_BINARY="$HOME/.local/share/houmao-cccc-receiver/target/debug/cccc" \
HOUMAO_CCCC_RECOVERY_ROOT=/tmp/houmao-cccc-recovery \
  pixi run pytest -q tests/integration/cccc/test_receiver_recovery.py
```

The lease-expiry case waits for the actual 45-second expiry. The recovery parent must be short enough for CCCC's native Unix-domain socket path. Each instance has a private disposable home. No shared development daemon is stopped. Missing explicit prerequisites fail setup.

## Qualify Independent Wheels

Preparation builds core, plugin, and stand-in fixture wheels and downloads binary dependency wheels. The run installs offline into a fresh external virtual environment, copies the utility runner outside the checkout, and uses only the installed product imports:

```bash
pixi run python scripts/qualification/cccc/installed.py prepare \
  --wheelhouse /external/private/cccc-wheelhouse
pixi run python scripts/qualification/cccc/installed.py run \
  --wheelhouse /external/private/cccc-wheelhouse \
  --work-root /external/private/cccc-installed-run \
  --endpoint http://127.0.0.1:8849
```

Each run requires a fresh work root. Its retained `venv/bin/python` and `venv/bin/houmao-cccc` can run the real-agent smoke. Stand-in fixtures exercise both supported gateway process modes and deterministic failures. They do not satisfy the separate real-agent acceptance gate.

The current-wheel run connects to the selected CCCC service with distinct Actor grants. It verifies ordinary Chat and Mail using signed self and admin calls, verifies the connection control before and after first-key registration, and dispatches to a broader receiver with explicit settings and a seeded admin. The installed Mail CLI uses `--signer-binding` with an owner-private fixture file.

## Run Two Real Coding Agents

Use the supported [local agent fixture configuration](../../agents/test-fixtures/README.md) and choose a real client/profile explicitly. For the cloud-api DeepSeek example, keep `DEEPSEEK_API_KEY` and the matching client base URL in the selected private `.env`; the driver delegates credential loading to the fixture helper.

```bash
/external/private/cccc-installed-run/venv/bin/python -I \
  scripts/qualification/cccc/real_agents.py \
  --source-root "$PWD" \
  --work-root "$HOME/.local/state/houmao/cccc-real-chat" \
  --endpoint http://127.0.0.1:8849 \
  --env-file "$PWD/.env" --case cloud-api --client claude --model deepseek-flash
```

Keep the normal developer `PATH` so the supported launcher captures the actual client and real tmux. Invoke the installed Python by absolute path; adding the stand-in environment's entire `bin/` directory to `PATH` would select its test-only tmux wrapper. The driver imports fixture utilities from their utility directory while requiring Houmao/plugin imports from the installed environment. It creates distinct managed owners and Actor grants, attaches their gateways, asks one agent to send chat, and verifies the peer's authored reply and native ancestry. Cleanup targets only captured agent identities and the owned Group.

The driver prints a sanitized result. Native agent output and detailed failure traces remain in the private work root. A failed real-client or model request is an unresolved gate, even when stand-in tests pass.

See [the scenario acceptance map](../../../docs/reference/gateway/cccc-acceptance.md) for the distinction between unit, provider, installed, and real-agent evidence.

## Qualify Deferred Mail

The second provider patch and plugin version 0.2 add Mail qualification. Native journal tests and the actual provider suites distinguish non-consuming inspection from explicit reads, including durable empty decisions, native-reader races, crash recovery, and ledger archival:

```bash
HOUMAO_CCCC_TEST_URL=http://127.0.0.1:8849 \
  pixi run pytest -q tests/integration/cccc/test_mail_provider.py
HOUMAO_CCCC_TEST_BINARY="$HOME/.local/share/houmao-cccc-receiver/target/debug/cccc" \
HOUMAO_CCCC_RECOVERY_ROOT=/tmp/houmao-cccc-mail-recovery \
  pixi run pytest -q tests/integration/cccc/test_mail_recovery.py
```

Use a fresh wheelhouse containing one core wheel, one 0.2 plugin wheel, fixture wheels, and their dependencies. Preserve the separately qualified 0.1 wheel for an actual gateway-only upgrade. The Mail run starts with held controllers, lets the gateway update their native conversations, and requires upgrade to preserve those newer persisted conversations and body PIDs:

```bash
pixi run python scripts/qualification/cccc/installed.py run-mail \
  --wheelhouse /external/private/cccc-mail-wheelhouse \
  --previous-plugin-wheel /external/private/chat-wheelhouse/houmao_cccc-0.1.0-py3-none-any.whl \
  --work-root /external/private/cccc-mail-installed-run \
  --endpoint http://127.0.0.1:8849
```

Run the real-agent driver with `--mode mail` using a separate installed 0.2 environment. An upgrade run temporarily installs 0.1 during each mode, so its environment must remain exclusive until it finishes. The Mail smoke asks one real agent to send, then explicitly asks its peer to read one batch and author a Mail reply. It verifies native deferred mode, the authoritative read receipt/cursor boundary, reply ancestry, and cleanup. A successful chat run is a separate gate.

The actual Stalwart coexistence test additionally requires explicit normal-account references. Set `HOUMAO_CCCC_STALWART_URL` to the selected discovery URL. Supply `HOUMAO_CCCC_STALWART_LOGIN`, `HOUMAO_CCCC_STALWART_ADDRESS`, and `HOUMAO_CCCC_STALWART_CREDENTIAL_FILE`, plus corresponding `HOUMAO_CCCC_STALWART_PEER_LOGIN`, `HOUMAO_CCCC_STALWART_PEER_ADDRESS`, and `HOUMAO_CCCC_STALWART_PEER_CREDENTIAL_FILE` for the second account. Credential files must be private and outside the checkout. No password appears in these environment references.

```bash
HOUMAO_CCCC_TEST_URL=http://127.0.0.1:8849 \
  pixi run pytest -q tests/integration/cccc/test_mail_email_coexistence.py
```

That test sends only uniquely identified owned fixtures to the selected normal accounts. A private fault proxy drops a response after a real successful email submission, then models an outage without stopping Stalwart. It verifies no CCCC mirroring/fallback, explicit CCCC send/read/reply during the fault, unchanged email identity/compaction state, and two eligible reminder cycles per channel per agent after real observation backoff. It archives its own email fixtures during cleanup. Email turn completion is deterministic; this does not substitute for the separate two-real-agent Mail smoke.

See [the Mail acceptance map](../../../docs/reference/gateway/cccc-mail-acceptance.md) for exact source identities, journal interruption scope, and executed/unexecuted gates.
