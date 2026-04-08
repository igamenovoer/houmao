## 1. Protocol And Address Policy

- [x] 1.1 Update mailbox address derivation and validation so newly derived managed-agent mailbox addresses use `<agentname>@houmao.localhost` while reserving `HOUMAO-*` local parts for Houmao-owned system principals.
- [x] 1.2 Add the operator-origin mailbox models and message metadata needed to represent `post`, including the reserved sender `HOUMAO-operator@houmao.localhost` and explicit one-way provenance markers.
- [x] 1.3 Add protocol-level and model-level tests for the new default address policy, reserved-name rejection, and operator-origin message semantics.

## 2. Filesystem Mailbox Root And Reserved Operator Account

- [x] 2.1 Update filesystem mailbox bootstrap so each initialized mailbox root provisions or confirms the reserved operator registration `HOUMAO-operator@houmao.localhost`.
- [x] 2.2 Update filesystem mailbox lifecycle flows (`register`, `unregister`, `cleanup`, accounts inspection, and project-mailbox wrappers) so the reserved operator account is visible but protected from generic destructive removal.
- [x] 2.3 Implement filesystem operator-origin delivery and reply-rejection behavior, including self-healing of the reserved operator registration when the mailbox root is otherwise valid.

## 3. Gateway, Server Proxy, And Native CLI Surfaces

- [x] 3.1 Add `POST /v1/mail/post` end to end across gateway models, client, service, and filesystem mailbox adapter, and return explicit unsupported results for non-filesystem transports.
- [x] 3.2 Add managed-agent server and passive-server proxy support for `POST /houmao/agents/{agent_ref}/mail/post` using the new gateway request model.
- [x] 3.3 Add `houmao-mgr agents mail post` and route it through authoritative pair-owned, manager-owned, or gateway-backed mail authority without allowing TUI submission fallback.

## 4. Docs And Verification

- [x] 4.1 Update `docs/reference/cli/agents-mail.md` and the mailbox reference pages to document `post`, the reserved sender namespace, the `@houmao.localhost` default address policy, and the filesystem-only `stalwart` stub boundary.
- [x] 4.2 Add or update targeted tests for reserved operator-account lifecycle, CLI/gateway/server `post` behavior, reply rejection, and explicit unsupported behavior on `stalwart`.
- [x] 4.3 Run focused Pixi-based test coverage for mailbox protocol, filesystem mailbox lifecycle, gateway mail routes, passive/server proxies, and CLI mail commands, then fix any regressions those checks expose.
