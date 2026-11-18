Houmao 3.0.0rc1 is the first release candidate for 3.0. It adds authenticated per-agent gateways, owner-aware lifecycle commands, and independent offline and online mailbox bindings.

## Upgrade from 2.4

- **Enroll gateway admins and update clients.** Private routes require signed proof from a current managed session or an enrolled admin, including on loopback. Admin routes require enrolled admin proof once the roster contains a key. Anyone who can reach a gateway with an empty roster can invoke admin operations. Provision keys before exposing the listener, and configure remote clients to verify HTTPS. [Gateway Access Guide](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/)
- **Select a channel and binding ID for gateway mailbox calls.** Offline registry and online Stalwart bindings are independent. List calls return metadata. Fetch message bodies through the read operation. [Gateway Mailbox Facade](https://igamenovoer.github.io/houmao/reference/gateway/operations/mailbox-facade/)
- **Recreate managed sessions for 3.0.** Stop existing sessions using 2.4 and back up their runtime data before launching fresh sessions. The current runtime uses manifest schema v5 and registry schema v4, with no in-place migration from older records.

## Other Changes

- Public gateway notifications and enabled public prompts accept one-way submissions.
- Owner-aware execution profiles route supported launch, lifecycle, and gateway operations through sudo, SSH, or Docker exec.
- DSH supports managed headless ACP and interactive Web sessions.
- Operators can inspect a managed agent's native home and refresh supported state without a session restart.
- Finalized usage records are available through the runtime and gateway.
- The gateway plugin SDK supports declared routes and capabilities. The optional `houmao-cccc` distribution adds CCCC chat and deferred mail.

## Install the Candidate

```bash
python -m pip install houmao==3.0.0rc1
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc1
```

## Validation

- The unit suite passed 4,702 tests with 14 skipped. Lint, type checks, the strict docs build, wheel and source distribution builds, Twine validation, and installed-wheel smoke checks passed.
- Gateway qualification exercised prefixed HTTPS across separate OS accounts on one host, with Stalwart, offline mailbox, and CCCC coverage. Cross-host and container gateway deployments remain unqualified for this candidate.

[Compare v2.4.0 and v3.0.0rc1](https://github.com/igamenovoer/houmao/compare/v2.4.0...v3.0.0rc1)
