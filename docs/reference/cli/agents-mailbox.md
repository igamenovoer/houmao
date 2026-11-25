# houmao-mgr agents single/self mailbox

Each agent can have an offline registry mailbox and an online provider mailbox simultaneously. Offline membership commands update an existing locally controlled agent without replacing its body or changing online mail.

```bash
houmao-mgr agents single --agent-id <id> mailbox offline status
houmao-mgr agents single --agent-id <id> mailbox offline join --address alice@houmao.localhost
houmao-mgr agents single --agent-id <id> mailbox offline leave
houmao-mgr agents self mailbox offline status
```

`agents single` selects a stable agent ID or an unambiguous friendly name. `agents self` resolves the current registered managed tmux session and accepts no explicit selector. Communication-only external imports do not grant local body or binding mutation authority.

## Offline Join

Local join uses the selected registry and its configured filesystem store. `--mailbox-root` selects a local store only when it matches that registry configuration. An occupied address owned by another agent fails. No force, stash, overwrite confirmation, or `--yes` option can take it over. The member owner is the persisted `agent_id`, independently of its friendly name or canonical mail address.

Remote join requires a reachable registry-only service. The registry host owns all mailbox files. Agent hosts need no shared mount:

```bash
houmao-mgr agents single --agent-id <id> mailbox offline join \
  --registry-url https://registry.example.test \
  --address alice@houmao.localhost \
  --credential-file /private/houmao/alice-member.token \
  --admin-credential-file /private/houmao/registry-admin.token
```

The caller prepares its private member credential before enrollment and reuses it when retrying a lost response. The administrator credential authorizes enrollment; neither an agent ID nor a mail address is a credential. Keep both files outside the checkout. Remote joins reject registry-host filesystem paths. Use HTTPS or an SSH tunnel to a loopback HTTP listener.

A confirmed registry claim can precede local publication. Inspect status and repeat the same join inputs to reconcile a partial result. Rejoin does not rotate credentials, allocate another registration, or replace mailbox history. [Registry-Only Setup](../mailbox/operations/offline-registry.md) documents service and credential preparation.

## Offline Status and Leave

`mailbox offline status` reports configured membership, binding ID, revision, and activation state without protected credential references. The ordinary `mail status` and `mail resolve-live` commands summarize both channels and canonical mail identity.

`mailbox offline leave --mode deactivate` explicitly releases routing while retaining history under the previous registration. `--mode purge` selects the supported local removal policy. A remote member uses its scoped release API. A later owner receives a fresh registration and cannot inherit private views or historical references. Stopping a body, losing a gateway, or attaching online mail never releases offline membership.

## Mail Follow-Up

Use explicit channel selection after joining:

```bash
houmao-mgr agents single --agent-id <id> mail status
houmao-mgr agents single --agent-id <id> mail list --channel offline
houmao-mgr agents single --agent-id <id> gateway mail-notifier enable --channel offline --interval-seconds 60
```

Offline and online mail remain separate. There is no forwarding or delivery fallback between them. See [Agents Mail](agents-mail.md), [Gateway Controls](agents-gateway.md), and [Agent Identity](../run-phase/agent-identity.md).

## Online Account Controls

Online controls require the agent's live gateway companion. They attach a normal existing account without management authorization, provisioning, password rotation, or body restart:

```bash
houmao-mgr agents single --agent-id <id> gateway attach
houmao-mgr agents single --agent-id <id> mailbox online status
houmao-mgr agents single --agent-id <id> mailbox online attach \
  --address alice@example.com --login-identity alice-login \
  --credential-source /private/houmao/alice-account.json \
  --jmap-url https://mail.example.test/.well-known/jmap
houmao-mgr agents single --agent-id <id> mailbox online refresh
houmao-mgr agents single --agent-id <id> mailbox online reconnect
houmao-mgr agents single --agent-id <id> mailbox online detach
```

The owner-private credential source is JSON containing a `password` string. It must exist on the gateway host, outside tracked files. The request contains its protected path; neither the password nor source reference appears in status. `--base-url` can replace `--jmap-url` and derives `/.well-known/jmap`. Select `--account-id` when discovery is ambiguous.

Pass `--trust-jmap-origin ORIGIN` once for each endpoint that needs an explicit approval. The default permits HTTPS or loopback HTTP discovery. Non-loopback HTTP discovery and API or upload origins that differ from discovery each need approval. Use an exact scheme, hostname, and port. Approving HTTP permits the password to travel in plaintext. Owner status reports the configured origins and any such approval.

Every control pins `--expected-revision`, or reads status once to obtain the revision when the option is omitted. Concurrent changes conflict. Changing the selected provider account, discovery endpoint, or verified API origin requires `--replace` and creates a fresh binding ID. Same-account refresh copies the selected source into a new private immutable snapshot, advances revision and epoch, and retains the binding ID, origin policy, and sync checkpoints. Refresh can select a new `--credential-source`. Reconnect keeps the credential snapshot and revision while advancing the connection epoch. All controls accept a finite `--timeout-seconds` budget.

Detach preserves provider mail, external source files, and offline membership. Old observations cannot publish after replacement. A retirement failure does not activate the candidate. `committed: true` with warnings confirms the authoritative change despite a derived publication problem; inspect status before repeating it. Already-started sends and replies preserve an explicit acknowledgement and original binding; an uncertain result is never automatically resent.

Configured online mail and enabled notifier service are separate. See [Stalwart Setup and First Session](../mailbox/operations/stalwart-setup-and-first-session.md) for protected credential preparation, account replacement, passive-server controls, and the separately authorized administrative provisioning path.
