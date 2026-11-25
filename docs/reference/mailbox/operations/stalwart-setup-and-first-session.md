# Stalwart Setup and First Session

This guide is for an operator with a running Houmao agent and an existing normal Stalwart account. Attach the account through its gateway companion. Account attachment does not require management credentials, provision an account, rotate its password, or restart the body.

To start Stalwart and Cypht from a fresh checkout, follow the bundled development stack setup. [Local Email System](https://github.com/igamenovoer/houmao/blob/main/dockers/email-system/README.md)

## Identity and Storage Authority

Stalwart occupies the agent's `online` slot. Its filesystem `offline` slot can remain configured at the same time. Both belong to the persisted globally unique agent ID; the account login and sending address remain separate values.

Canonical mail identity uses the configured online address, including during an outage. After online detach, it uses the offline address when present. Explicit `--channel offline` or `--channel online` selects delivery. Houmao does not bridge the channels or switch channels after failure.

Stalwart owns online messages, delivery, flags, and reply ancestry. Houmao owns the runtime binding, immutable private credential copies, connection epochs, gateway routing, and notifier admission. Filesystem mailbox rules, symlink views, and mailbox-local SQLite state apply to offline mail only.

## Prepare an Existing Account

Have the account administrator provide its normal login, authorized sending address, and JMAP session-discovery URL. An explicitly selected account ID is required when discovery has multiple eligible accounts. Login and address may differ. The sender must match an authorized identity in the selected account.

Put the password in an owner-private JSON file **outside the checkout**, on the host running the agent's gateway:

```json
{"password": "<normal-account-password>"}
```

Set file permissions to `0600`. Pass its absolute path as `--credential-source`; never pass the password itself as a command argument, tracked profile, `--env-set` value, example, or script. API requests carry this protected path reference, never password contents. A passive-server proxy resolves the reference on the gateway host.

Prefer an explicit discovery URL. The development service uses `http://127.0.0.1:10080/.well-known/jmap`. `--base-url http://127.0.0.1:10080` derives that standard discovery path. The advertised JMAP method endpoint can differ; Houmao follows validated discovery rather than treating the discovery endpoint as the method endpoint. See [Project Services](../../../../SERVICES.md) for the running development service.

## Attach the Gateway and Account

Set `agent_id` to the running agent's stable ID. The gateway companion is required for online control commands:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway attach
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online status
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online attach \
  --address research@example.test --login-identity research-login \
  --credential-source /private/houmao/research-account.json \
  --jmap-url http://127.0.0.1:10080/.well-known/jmap
```

The operator commands work for `agents self` as well. Each mutation pins an online slot revision. Pass `--expected-revision "$revision"` to pin a previously inspected snapshot. If omitted, the command reads status once and pins that revision; concurrent changes still conflict. A failed candidate leaves the current binding and its private credential copy unchanged. Selecting a different account requires explicit `attach --replace`, which allocates a fresh binding ID.

Successful attachment validates credentials, account access, sending identity, and required mail capabilities before publication. Houmao copies the selected source into a private immutable session file. It then closes old admission, drains admitted operations within the finite deadline, and atomically updates only the online slot. Body PID, conversation, stable agent identity, and offline mail remain intact.

A result with `committed: true` and warnings means the authoritative binding changed, even if a derived connection or discovery projection requires reconciliation. Inspect status before repeating a control. A retirement timeout reports failure without activating the candidate.

## Refresh, Reconnect, and Detach

After replacing the selected source file with a new password for the same account:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online refresh
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online reconnect
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online detach
```

Refresh reopens the explicit source, copies it into a new immutable private file, and validates the same account and address. Use `refresh --credential-source /private/houmao/rotated-account.json` to choose a new source. The binding ID and account-scoped sync checkpoints remain stable; the slot revision and connection epoch change. A credential that selects a different account fails refresh and requires explicit replacement.

Reconnect validates the current immutable copy and changes the connection epoch without changing the binding ID or slot revision after the one-time adoption of a launch-created binding. It does not reopen a rotated external source; use refresh for that. A gateway restart recovers the current shared epoch and sync checkpoints.

Detach removes only online configuration, cancels unstarted old reminders, and fences old observations. It leaves provider mail, externally owned source files, and offline mail intact. Retired Houmao-owned credential copies are cleaned after admitted operations drain. Already-started sends and replies retain their old binding and explicit `confirmed`, `rejected`, or `uncertain` acknowledgement. An uncertain result requires reconciliation; Houmao does not resend automatically.

Cross-process admission also covers ordinary direct manager online operations. Attaching a companion is an operator control prerequisite, not a requirement that all ordinary mail calls pass through HTTP. Slow provider requests do not hold the gateway's terminal lock. An admitted notifier body effect also holds online admission through prompt submission. A synchronous headless submission can remain active for its current turn; a control whose retirement deadline expires reports busy/uncertain and keeps the old binding. Retry the control after that turn finishes. Old poll results can finish after detach or replacement but cannot publish a checkpoint or wake the new binding.

## Inspect and Use Mail

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail status
pixi run houmao-mgr agents single --agent-id "$agent_id" mail resolve-live
pixi run houmao-mgr agents single --agent-id "$agent_id" mail list \
  --channel online --expected-binding-id "$binding_id" --limit 10
pixi run houmao-mgr agents single --agent-id "$agent_id" mail read \
  --channel online --expected-binding-id "$binding_id" --message-ref "$message_ref"
pixi run houmao-mgr agents single --agent-id "$agent_id" mail send \
  --channel online --expected-binding-id "$binding_id" \
  --to reviewer@example.test --subject "Review request" --body-content "Please review the result."
pixi run houmao-mgr agents single --agent-id "$agent_id" mail archive \
  --channel online --expected-binding-id "$binding_id" --message-ref "$message_ref"
```

Copy the online `binding_id` from status and retain message references as opaque values. Lists return finite metadata pages, never bodies. Fetch content explicitly with `peek` or `read`; inspect content completeness and limit fields. All mail lifecycle HTTP requests use schema version `3` and `expected_binding_id`, including fresh sends. Online operator `post` remains unsupported.

The operator HTTP routes are `GET|PUT|DELETE /v1/mail/online/binding` and `POST /v1/mail/online/binding/refresh|reconnect`. Mutation requests carry `expected_revision`; attach additionally carries address, login identity, endpoint, and the protected `credential_source_ref`. Responses omit credential paths, references, login names, passwords, and authorization inputs. Gateway mail routes remain loopback-only. Authorized passive-server routes proxy the same controls under `/houmao/agents/{agent_ref}/mail/online/binding`.

## Enable Periodic Reminders Separately

Configured mail does not automatically enable notifier service. Enable it on the live gateway:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier enable \
  --channel online --interval-seconds 60 --mode any_inbox
```

Read and answered flags do not substitute for archive completion. Eligible unchanged inbox work continues producing periodic reminders. Bounded metadata observation and account-scoped checkpoints support those reminders without reading every retained message body.

## Administrative Launch-Time Provisioning

An operator explicitly authorized to create Stalwart accounts can still use a provisioning profile. This workflow additionally requires the management API URL and private management authorization. Load that authorization from an explicitly selected external local environment file. Never store it in a tracked profile, preset, or `--env-set` record.

```bash
pixi run houmao-mgr project profile create \
  --name research-online --specialist worker --agent-name research --mode headless \
  --mail-transport stalwart --mail-address research@example.test \
  --mail-jmap-url http://127.0.0.1:10080/.well-known/jmap \
  --mail-management-url http://127.0.0.1:10080/api
pixi run houmao-mgr project agents launch --profile research-online --name research --mode headless
```

A declaration can independently populate both slots:

```yaml
mailboxes:
  offline: null
  online:
    transport: stalwart
    address: research@example.test
    jmap_url: http://127.0.0.1:10080/.well-known/jmap
    management_url: http://127.0.0.1:10080/api
```

Only this explicit launch-time administrative path ensures the account. Resume reads the persisted binding and does not provision an account or rotate its password. Existing launch-created bindings are pinned to a validated account and sending identity on their first managed connection, preserving their binding ID.

## References

- [Agents Mailbox CLI](../../cli/agents-mailbox.md)
- [Runtime Contracts](../contracts/runtime-contracts.md)
- [Gateway Mailbox Facade](../../gateway/operations/mailbox-facade.md)
- [Stalwart Backend](../../../../src/houmao/mailbox/stalwart.py)
- [Online Binding Controls](../../../../src/houmao/mailbox/online_binding.py)
