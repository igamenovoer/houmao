# Stalwart Setup and First Session

This guide is for an operator with a running Houmao agent and an existing normal Stalwart account. Attach the account through its gateway companion. Account attachment does not require management credentials, provision an account, rotate its password, or restart the body.

To start Stalwart and Bulwark Webmail from a fresh checkout, follow the bundled development stack setup. [Local Email System](https://github.com/igamenovoer/houmao/blob/main/dockers/email-system/README.md)

## Identity and Storage Authority

Stalwart occupies the agent's `online` slot. Its filesystem `offline` slot can remain configured at the same time. Both belong to the persisted globally unique agent ID; the account login and sending address remain separate values.

Canonical mail identity uses the configured online address, including during an outage. After online detach, it uses the offline address when present. Explicit `--channel offline` or `--channel online` selects delivery. Houmao does not bridge the channels or switch channels after failure.

Stalwart owns online messages, delivery, flags, and reply ancestry. Houmao owns the runtime binding, immutable private credential copies, connection epochs, gateway routing, and notifier admission. Filesystem mailbox rules, symlink views, and mailbox-local SQLite state apply to offline mail only.

## Configure Incoming Mail Policy

Stalwart applies its own rules at delivery. Set provider-managed sender preferences in Stalwart. For Houmao's protected policy, qualify an independent Stalwart connector that uses a native Sieve include to file matching new arrivals directly into Archive. Rule changes apply to future deliveries and preserve existing folders. The gateway consumes the resulting Inbox for reminders. [Recipient Policy Qualification](stalwart-qualification.md#recipient-policy-qualification)

## Prepare an Existing Account

Have the account administrator provide its normal login, authorized sending address, and JMAP session-discovery URL. Select the account ID explicitly when discovery has multiple eligible accounts. Login and address may differ. The selected account needs writable JMAP submission, a matching sender identity, and Inbox, Sent, and Archive roles. Ordinary operation requires rights to read and update flags in Inbox and add items to Sent. Ordinary archive additionally requires the corresponding folder placement rights. Ask the provider administrator to prepare any missing identity, role, or permission reported by attach, then repeat the operation.

Put the password in an owner-private JSON file **outside the checkout**, on the host running the agent's gateway:

```json
{"password": "<normal-account-password>"}
```

Set file permissions to `0600`. Pass its absolute path as `--credential-source`; never pass the password itself as a command argument, tracked profile, `--env-set` value, example, or script. API requests carry this protected path reference, never password contents. A passive-server proxy resolves the reference on the gateway host.

Prefer an explicit discovery URL. The development service uses `http://127.0.0.1:10080/.well-known/jmap`. `--base-url http://127.0.0.1:10080` derives that standard discovery path. The advertised JMAP method endpoint can differ; Houmao follows validated discovery rather than treating the discovery endpoint as the method endpoint. See [Project Services](../../../../SERVICES.md) for the running development service.

## Attach the Gateway and Account

Set `agent_id` to the running agent's stable ID. Online attachment works with an open or keyed gateway. Attach to an already keyed gateway using the applicable caller authority, or attach on an open gateway and enroll the first administrator afterward. The gateway companion is required for online control commands.

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway attach
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online status
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox online attach \
  --address research@example.com --login-identity research-login \
  --credential-source /private/houmao/research-account.json \
  --jmap-url http://127.0.0.1:10080/.well-known/jmap
```

The operator commands work for `agents self` as well. Each mutation pins an online slot revision. Pass `--expected-revision "$revision"` to pin a previously inspected snapshot. If omitted, the command reads status once and pins that revision. Concurrent changes still conflict. A failed candidate preserves the active binding and its private credential copy. Selecting a different account, discovery endpoint, or API origin requires `attach --replace` and allocates a fresh binding ID.

For intranet HTTP, approve the exact discovery origin with `--trust-jmap-origin http://mail.example.com:10080`. Repeat the option for any distinct advertised API or upload origin with which you intend to share the mailbox credential. The scheme and effective port are part of the approval. HTTPS protects credentials in transit. HTTP approvals expose them to observers on that network. The API accepts approvals as a `trusted_jmap_origins` array. Refresh and reconnect reuse the stored approvals and verified API origin.

Successful attachment validates credentials, account access, sending identity, and required mail capabilities before publication. Houmao copies the selected source into a private immutable session file. It then closes old admission, drains admitted operations within the finite deadline, and atomically updates only the online slot. Body PID, conversation, stable agent identity, and offline mail remain intact.

A result with `committed: true` confirms that the operation committed. Warnings identify plaintext approvals or reconciliation that needs attention. Inspect status before repeating a control. A retirement timeout reports failure without activating the candidate.

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
```

When the binding and caller authorize placement, archive processed mail after the work and any required reply succeed.

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mail archive \
  --channel online --expected-binding-id "$binding_id" --message-ref "$message_ref"
```

On a protected binding, report completed items for separately authorized mailbox-owner filing through Stalwart. The runtime can continue ordinary authorized participation with restricted credentials.

Copy the online `binding_id` from status and retain message references as opaque values. Lists return finite metadata pages, never bodies. Fetch content explicitly with `peek` or `read`; inspect content completeness and limit fields. All mail lifecycle HTTP requests use schema version `3` and `expected_binding_id`, including fresh sends. Online operator `post` remains unsupported.

The operator HTTP routes are `GET|PUT|DELETE /v1/mail/online/binding` and `POST /v1/mail/online/binding/refresh|reconnect`. Mutation requests carry `expected_revision`; attach additionally carries address, login identity, endpoint, and the protected `credential_source_ref`. Responses omit credential paths, references, login names, passwords, and authorization inputs. Gateway mail routes remain loopback-only. Authorized passive-server routes proxy the same controls under `/houmao/agents/{agent_ref}/mail/online/binding`.

## Enable Periodic Reminders Separately

Configured mail does not automatically enable notifier service. Enable it on the live gateway:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" gateway mail-notifier enable \
  --channel online --interval-seconds 60 --mode any_inbox
```

The notifier reads Stalwart's authoritative Inbox. Mail filed directly into Archive at delivery stays outside that work. `any_inbox` can continue reminding while completed mail awaits owner filing. `unread_only` limits reminders to unread Inbox mail. Bounded metadata observation and account-scoped checkpoints support those reminders.

## Administrative Launch-Time Provisioning

An operator explicitly authorized to create Stalwart accounts can still use a provisioning profile. This workflow additionally requires the management API URL and private management authorization. Load that authorization from an explicitly selected external local environment file. Never store it in a tracked profile, preset, or `--env-set` record.

```bash
pixi run houmao-mgr project profile create \
  --name research-online --specialist worker --agent-name research --mode headless \
  --mail-transport stalwart --mail-address research@example.com \
  --mail-jmap-url http://127.0.0.1:10080/.well-known/jmap \
  --mail-management-url http://127.0.0.1:10080/jmap
pixi run houmao-mgr project agents launch --profile research-online --name research --mode headless
```

A declaration can independently populate both slots:

```yaml
mailboxes:
  offline: null
  online:
    transport: stalwart
    address: research@example.com
    jmap_url: http://127.0.0.1:10080/.well-known/jmap
    management_url: http://127.0.0.1:10080/jmap
```

Launch declarations accept `trusted_jmap_origins` under `mailboxes.online` for approved intranet endpoints. A base URL derives the standard discovery path, and a supplied `jmap_url` selects the exact endpoint.

Select a mail domain that the running Stalwart release accepts for JMAP sending identities. Stalwart v0.15.5 requires a recognized public suffix and rejects `.localhost` and `.test` senders for JMAP provisioning. Use a separate send-capable domain from the bundled `houmao.localhost` accounts for JMAP agent qualification.

Explicit provisioning uses administrative access to ensure the principal, then uses the mailbox credential to verify or create the sender identity and Archive role. Launch publishes the verified account, identity, and API origin with the new binding. Resume loads this configuration. Existing launch-created bindings that lack these pins record them at their first validated connection.

## References

- [Agents Mailbox CLI](../../cli/agents-mailbox.md)
- [Runtime Contracts](../contracts/runtime-contracts.md)
- [Gateway Mailbox Facade](../../gateway/operations/mailbox-facade.md)
- [Stalwart Backend](../../../../src/houmao/mailbox/stalwart.py)
- [Online Binding Controls](../../../../src/houmao/mailbox/online_binding.py)
