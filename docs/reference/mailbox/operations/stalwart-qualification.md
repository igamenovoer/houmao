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

Exercise metadata pages, one selected peek/read, send/reply/mark/archive, same-account credential refresh, gateway restart, and expired-state recovery. Test the body both ready and busy. Count due reminder cycles, accepted gateway reminders, and actual dispatched prompts separately. An unchanged eligible message should permit later periodic reminders; same-cycle retries must not duplicate admission. Reconnect, cache eviction, and rebase must not repeat compaction for continuously eligible work. Record provider-side delivery outcomes before retrying any uncertain mutation.

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

Treat Stalwart account authentication and provider submission receipts as evidence of submission. Keyed Houmao policy requires authorization after final recipient routing and before each inbox deposit through SMTP, JMAP, and local delivery. The included Stalwart adapter cannot qualify all of those paths. Houmao refuses attaching or using a provider inbox under a keyed roster, and requires detaching an existing provider binding before first-key enrollment. Existing keyed deployments with online inboxes can detach them and continue using qualified offline delivery. The external provider remains responsible for its own inbox and routing configuration.
