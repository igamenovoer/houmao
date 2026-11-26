# Stalwart Qualification and Load Plan

Use a deliberately selected normal test account and protected credential file. Keep credentials, generated homes, gateway databases, corpus files, and run directories outside the checkout. The project service location is documented in [SERVICES.md](../../../../SERVICES.md); record the running release rather than assuming it matches `extern/orphan/stalwart`.

## Representative Checks

The [client runner](../../../../scripts/qualification/stalwart-mail/client.py) validates account/sending identity, bounded metadata, explicit content, and change methods. Its optional `--exercise-self-mail` sends only to the selected sandbox account, replies, and archives those test deliveries. Provisioning is a separate administrative workflow. These normal-account commands require no management credential.

```bash
pixi run python scripts/qualification/stalwart-mail/client.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login '<selected normal-account login>' \
  --address '<authorized sending address>' \
  --credential-file /external/private/account.json \
  --service-release '<actual running release>' \
  --output /external/private/client-report.json
```

The [observation runner](../../../../scripts/qualification/stalwart-mail/observe.py) performs only readonly bounded observation. Select the test agent/binding identifiers and an external work directory. Its SQLite cache is qualification-owned derived state; it is not the live gateway's binding authority.

```bash
pixi run python scripts/qualification/stalwart-mail/observe.py \
  --discovery-url http://127.0.0.1:10080/.well-known/jmap \
  --login '<selected normal-account login>' \
  --address '<authorized sending address>' \
  --credential-file /external/private/account.json \
  --agent-id '<test agent id>' --binding-id '<online binding id>' \
  --service-release '<actual running release>' \
  --work-dir /external/private/observation-run --cycles 5
```

The report measures actual attempted HTTP requests, request-body bytes, response-body bytes read, JMAP method counts, cycle p50/p95 latency, process peak RSS, and time to first idle checkpoint. Payload-byte counts exclude headers, TLS framing, and unread error bodies. Initialization methods are separate from the observation budget. Cache counts are bounded samples. Optional declared corpus sizes are labels supplied by the operator, not totals established by an account scan.

This runner has no agent body or gateway scheduler. It reports reminder count as unavailable rather than zero. Measure real reminder admission separately through gateway request/audit records and the runtime qualification below. A two-cycle hermetic subprocess test verifies that the runner records counts and makes no `Email/set` or submission calls; it does not establish live target-scale capacity.

## Runtime Acceptance

Use [the development launcher](../../../../skillset/dev/houmao-dev-launch-agents/commands/attach-online-mail.md) for a selected self-hosted or cloud-API agent fixture, then attach normal online mail to its active gateway. Keep the body PID and conversation marker before/after attach, refresh, reconnect, and detach. Check offline mail remains configured and operational throughout.

Exercise both keyed setup orders. First attach an account to a gateway with an enrolled administrator. Then start with an open gateway, attach the account, and enroll its first administrator. Verify the binding survives enrollment and gateway restart. Exercise metadata pages, selected peek and read, send, reply, flag changes, authorized archive, same-account credential refresh, and expired-state recovery. Test the body both ready and busy. Count due cycles, admitted reminders, and dispatched prompts separately. Unchanged eligible mail permits later reminders. A same-cycle retry preserves one admission. Reconnect, cache eviction, and rebase preserve compaction history for continuously eligible work. Verify provider outcomes before retrying an uncertain mutation.

## Authenticated Gateway Checks

The HTTPS integration tests run a gateway in the foreground and in a separate detached process. Both modes use a verified TLS proxy with a path prefix, independent caller signers, and a separate mailbox service. The offline checks start `houmao-passive-server offline-registry` in its own process. The online checks provision two disposable normal accounts in a selected Stalwart binary. [Authenticated gateway mailbox integration tests](../../../../tests/integration/mailbox/test_authenticated_gateway_mail.py)

The 2026-11-18 run passed against Stalwart 0.15.5 on Linux aarch64. It verified delivery, reply, explicit read, archive, stale binding refusal, and authenticated attach, refresh, reconnect, and detach. The offline registry run verified signed delivery, owner-file attachment access, reply, and stale membership binding refusal. The proxy, gateways, and mailbox services ran on one host with separate process and state roots. Cross-host and container deployment remain separate qualification lanes. [Stalwart 0.15.5 release assets](https://github.com/stalwartlabs/stalwart/releases/expanded_assets/v0.15.5)

Select a local executable to include the disposable Stalwart cases in a run.

```bash
env -u TMUX -u TMUX_PANE HOUMAO_TEST_STALWART_BIN=/external/stalwart \
  pixi run pytest tests/integration/mailbox/test_authenticated_gateway_mail.py
```

## Target-Scale Workload Plan

The target is approximately 100 independently scoped agents and millions of retained messages. This is a plan until executed. Begin with one account, then a small multi-account run, before the target deployment. Use isolated provisioned accounts and an explicitly approved corpus generator; never seed a personal mailbox or mix the model API key with mail credentials.

Separate retained archive size from eligible inbox backlog. Increase archive corpus through representative small, medium, and million-message levels while holding active inbox work fixed. Separately increase active inbox backlog while holding archive size fixed. A large retained archive alone is not a large active-work test.

| Scenario | Controlled Input | Measurements and Required Observation |
| --- | --- | --- |
| Idle | Fixed small inbox, increasing retained archive | Warmed request/method and payload counts remain bounded; no bodies or archive enumeration |
| New work | Finite arrivals during/after a filtered query | Time to eligible observation, intermediate checkpoint continuity, bytes and request count |
| Busy body | Same inbox, admission temporarily blocked | Sync continues; no successful-admission count is invented; work survives until readiness |
| Unchanged open work | Stable eligible message across reminder intervals | Repeated later reminders, one admission per cycle, no permanent digest suppression |
| Reconnect/restart | Same account with new connection/gateway process | Preserved checkpoint scope, bounded validation/recovery traffic, no full retained-history bootstrap |
| Expired state | Deliberately stale checkpoint or oversized query delta | Bounded rebase, visible progress/limitations, no body scan or unbounded delta retry |
| Cache pressure | Eligible set larger than metadata cache | Has-more/sample semantics, continued server pagination, no compaction reset from eviction |
| Concurrent agents | Independent bindings/accounts and staggered arrivals | Aggregate and per-agent p50/p95, RSS, request/byte rates, fairness, and backlog recovery time |

Collect provider release/configuration, actual accounts and messages created, active inbox sizes, host CPU/RAM, topology/TLS policy, operational budgets, concurrency, and sample duration. Report warm and cold connection epochs separately. Measure per-cycle and aggregate HTTP requests, JMAP methods, payload bytes, p50/p95 latency, per-process/aggregate RSS, time to current work, time to idle checkpoint, and reminder/compaction counts. Retain only sanitized summaries in the repository.

Pass/fail checks include the configured per-cycle method/time bounds, complete reconciliation before checkpoint advancement, metadata-only selection, no scope leakage, preserved periodic reminders, and one-shot compaction continuity. Performance percentiles need a stated sample count and acceptance threshold chosen for the actual deployment. A representative one-account report cannot substantiate 100-agent or million-message capacity.

## Recipient Policy Qualification

Ordinary online attachment works on open and keyed gateways with normal mailbox credentials. Protected rule application has separate prerequisites. Qualify them for the deployed Stalwart release and topology before enrolling the connector target. The earlier authenticated gateway run exercised ordinary mailbox operations. It did not exercise this protected deployment.

The 2026-11-26 Stalwart v0.15.5 run on Linux aarch64 verified native JMAP Sieve compilation, update, readback, and delivery straight to Archive with the gateway stopped. Rule application and removal preserved existing Inbox and Archive membership. The ordinary Stalwart account could still change placement through JMAP, so the protected runtime check refused it.

The protected connector updates a dedicated existing `houmao-protected-archive` personal Sieve script through owner-side JMAP credentials. In the exact recipient account, prepare the Archive role and an active wrapper that includes this script before any delivery action. The connector pins the account, Archive role, active wrapper blob, and initial managed script blob. It preserves unrelated rules by updating only the included script. The runtime may read Inbox, submit mail, and update ordinary flags through its separate credential. Keep all provider permissions to modify rules or override folder placement outside runtime authority. [Stalwart Sieve](https://stalw.art/docs/sieve/) · [Connector Authority](../../../../src/houmao/mailbox/stalwart_policy_authority.py)

Submit matching and nonmatching messages across the enabled delivery paths with the gateway stopped. Include SMTP, JMAP, aliases, list expansion, spam handling, and any local route that reaches the account. Verify the matched message is in Archive without Inbox membership and that an unaffected message is in Inbox. Use both uppercase and lowercase domains in the sender address to check normalization. Match address metadata as a mail rule. SMTP authentication and gateway key identity remain separate. Apply and remove the rule against a seeded Inbox and Archive and verify prior placement stays unchanged. Verify matching and nonmatching submissions have the same accepted sender receipt.

Use runtime credentials against every enabled provider API to verify that rule administration, opening protected Archive content, and placement mutations are refused. Include JMAP, IMAP, ManageSieve, and provider administration surfaces as applicable. Keep connector state, management credentials, and owner authorization outside the gateway's host account and storage. If any delivery path or runtime credential bypasses protected placement, leave that target unenrolled. Protected apply reports unsupported for an unenrolled target. Ordinary attachment remains available.

The gateway's owner-private access configuration can set `stalwart_policy_url` to the trusted connector's HTTPS origin. Forward `POST /v1/mail/online/policy/apply` for the exact binding with an independently signed mail-only update. The connector verifies the signature against its private owner enrollment and confirms the provider effect before recording an applied revision. Verify a receipt independently through the connector's private database. [Online Binding and Mail Policy](stalwart-setup-and-first-session.md)

### Run the Qualified Connector

From a separate provider-management account, prepare the personal script `houmao-protected-archive` with an empty body or comment. Add `require "include";` to the active script's declarations and `include :personal "houmao-protected-archive";` before its first delivery action. Keep the existing active script's unrelated rules. The connector updates only the included script. Use provider-authorized JMAP `SieveScript/get` to obtain the active script and initial include `blobId` values. Use `Mailbox/get` to obtain the bound account's Archive role ID.

Place the settings JSON and database under a private directory of the separate connector account. The settings select the exact runtime `binding_id`, a stable connector `backend_id`, `jmap_url`, management `login_identity` and `credential_file`, `account_id`, `archive_id`, `active_script_blob`, `initial_policy_blob`, and `database`. Use a provider HTTPS endpoint and private provider password file. The gateway receives only the connector URL.

Provide `runtime_jmap_url`, `runtime_login_identity`, `runtime_credential_file`, and `runtime_sender_address` so the connector can check the actual restricted endpoint and login. It refuses protected application if that login can change mailbox placement, read Archive, or access JMAP Sieve. Deployment qualification covers other enabled protocols and account routes.

Stalwart requires account membership for JMAP submission. A stock mailbox-owner login therefore does not meet the protected runtime test. A deployment that uses a restricted JMAP access service must keep the provider login at that service, grant only the intended runtime actions, and independently verify the resulting boundary. The disposable native filing test did not qualify such a deployment.

```bash
pixi run python scripts/qualification/stalwart-mail/policy_connector.py \
  --settings /private/connector/settings.json owner-set --public-key /private/connector/owner.pub
pixi run python scripts/qualification/stalwart-mail/policy_connector.py \
  --settings /private/connector/settings.json serve --host 192.0.2.10 \
  --certificate /private/connector/tls.pem --tls-key /private/connector/tls-key.pem
pixi run python scripts/qualification/stalwart-mail/policy_connector.py \
  --settings /private/connector/settings.json receipt "$operation_id"
```

Use the same `owner-set` command to rotate authority. Use `owner-set --revoke` to revoke the enrolled key and preserve the committed policy. After an uncertain update, check its exact receipt independently. An exact retry can verify the installed script and record its result without resending a native update.
