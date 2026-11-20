Houmao 3.0.0rc5 makes keyless gateways usable without signing and fixes pasted private-key paths in interactive Web login.

## Upgrade From 3.0.0rc4

- **An empty admin roster opens all enabled operations for the selected agent.** Enroll a key before upgrading a reachable gateway whose callers should require proof. Restart running gateways after upgrading. [Gateway Access](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/)
- Update clients that strictly parse the gateway descriptor to accept `private_proof: none` for open policy and `private_proof: unavailable` when required policy cannot be read.

## What Changed

- Anonymous callers can use private and admin routes on a gateway with a valid empty roster, including selected-agent passive operations. Enrolling the first key restores signed access. Removing the final key reopens access.
- Opening the bare owner-local `/v1/web/enter` URL with an empty roster redirects directly into DSH or Kimi Web. The scoped `gateway web-entry` command can issue its usual one-time link without a signer. Gateways with enrolled keys use interactive login or signed link issuance. [Web Entry](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-live-web-agent)
- Interactive login trims surrounding whitespace from the private-key path before generating the terminal command. Whitespace-only input selects the local SSH agent. [Issue #89](https://github.com/igamenovoer/houmao/issues/89)

## Install the Candidate

```bash
uv tool install 'houmao==3.0.0rc5'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc5
```

## Qualification

The candidate passed 5,123 unit tests with 14 skips and seven HTTPS and native DSH Web integration cases. A fresh Chromium session entered managed DSH Web from a keyless gateway. Lint, type checking, skill-version checks, the strict docs build, and distribution validation passed. [Verification Log](https://github.com/igamenovoer/houmao/blob/v3.0.0rc5/openspec/changes/open-gateway-with-empty-admin-roster/logs/verification.md)

[Compare v3.0.0rc4 and v3.0.0rc5](https://github.com/igamenovoer/houmao/compare/v3.0.0rc4...v3.0.0rc5)
