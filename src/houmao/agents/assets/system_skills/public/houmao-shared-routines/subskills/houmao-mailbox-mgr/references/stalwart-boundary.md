# Stalwart Boundary and Online JMAP Readiness

Use this reference whenever a mailbox-administration request mentions `stalwart` or `mailbox online`.

## Offline Root Lanes vs Online Agent Binding

- **Filesystem-only root and account lanes**: `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` administer offline filesystem mailbox roots, registrations, structural projections, and exports only. They never provision Stalwart servers, domains, or server-side user accounts.
- **Managed-agent Stalwart online binding (`mailbox online`)**: `houmao-mgr agents single --agent-id|--agent-name ... mailbox online {attach|detach|reconnect|refresh|status}` (and verified `houmao-mgr agents self mailbox online ...`) binds an **existing** Stalwart account to a running managed agent through its live gateway companion without restarting the agent body or modifying its `offline` slot. See [../commands/agent-binding-online.md](../commands/agent-binding-online.md).

An authorized operator can attach the account on an already keyed gateway or enroll the first gateway administrator after attaching the account. Gateway key enrollment preserves the bound provider account.

## Online JMAP Attachment Requirements

1. **Owner-private credentials**: pass `--credential-source <file>` pointing to an owner-private password JSON file on the agent host; never pass passwords as CLI arguments.
2. **JMAP discovery and origin trust**: supply `--jmap-url <exact-url>` or `--base-url <server-base>` (`/.well-known/jmap`), and pass `--trust-jmap-origin <scheme://host:port>` when approving a non-default or HTTP intranet JMAP origin.
3. **Mailbox role readiness**: the Stalwart account must expose `Inbox`, `Sent`, and `Archive` roles. Verify Inbox read and flag-update rights, authorized sending identity, and writable submission to Sent on `attach`, `reconnect`, and `refresh`. `mailbox online status` reads configured local metadata. Runtime placement requires additional authority.
4. **Server bootstrap reference**: for external Stalwart server deployment or first-account provisioning outside Houmao's CLI, consult `docs/reference/mailbox/operations/stalwart-setup-and-first-session.md`.

## Protected Mail Policy

Protected filtering requires a separately qualified Stalwart connector with provider-native control and runtime placement isolation. An authorized gateway caller can relay `POST /v1/mail/online/policy/apply` to that connector using an independently owner-signed update for the exact binding and rule revision. The owner retains signing and provider management authority outside the gateway, and verifies the applied receipt through the backend.

Stalwart files matching new mail directly into Archive at delivery. Rule changes preserve existing folders. On a protected binding, use independently authorized owner access for Archive review and for filing processed Inbox mail. Stalwart qualification and ordinary attachment are independently reported.

## Guardrails

- DO NOT invent `houmao-mgr mailbox ...` or `houmao-mgr project mailbox ...` root or account CRUD commands for Stalwart.
- DO NOT inline Stalwart passwords on the command line or approve HTTP `--trust-jmap-origin` origins without explicit caller intent.
