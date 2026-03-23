## 1. Mailbox Reader Path

- [x] 1.1 Add `docs/reference/mailbox/operations/stalwart-setup-and-first-session.md` with Houmao-side prerequisites, transport comparison, direct `mail` verification steps, and gateway-preference guidance.
- [x] 1.2 Update `docs/reference/mailbox/quickstart.md` so it exposes the filesystem-versus-Stalwart choice near the start and routes Stalwart readers into the dedicated operator page.
- [x] 1.3 Update `docs/reference/mailbox/index.md` and `docs/reference/mailbox/internals/runtime-integration.md` so they explain the direct-versus-gateway mailbox path and point readers to the exact contract pages for payload details.

## 2. Gateway And System-Files Coverage

- [x] 2.1 Add `docs/reference/gateway/operations/mailbox-facade.md` covering `/v1/mail/*`, adapter resolution from `attach.json` and `manifest.json`, loopback-only availability, and notifier polling through the shared facade.
- [x] 2.2 Update `docs/reference/gateway/index.md` so the mailbox facade is part of the gateway "start here" path and clearly linked to mailbox and system-files references.
- [x] 2.3 Update `docs/reference/system-files/agents-and-runtime.md` to document secret-free mailbox manifest persistence, `credential_ref`, durable credential-related artifacts, and session-local materialized credential files.

## 3. Cross-Linking And Validation

- [x] 3.1 Review the touched mailbox, gateway, and system-files pages to ensure responsibility tables, persisted-versus-secret guidance, and cross-links are consistent and do not duplicate contract schemas unnecessarily.
- [x] 3.2 Validate the OpenSpec change artifacts and perform the appropriate docs validation or lint pass for the touched files.
