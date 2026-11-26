Houmao 3.0 brings managed run modes, scoped gateway access, and independent email and CCCC delivery to the stable release.

## Added

- **Managed run modes and execution profiles.** Select `headless`, `service`, `tui`, or `web` on supported tools. Execution profiles route lifecycle operations to the owning account or context. Launch profiles select a tmux server, and the gateway dashboard links to supported native Web sessions. [Session Lifecycle](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/)
- **Versioned agent files and public skills.** Edit drafts on enabled skill and MCP mounts and publish against an expected base. The bundled public skills cover gateway access, agent work loops, and operator workflows. [Versioned File Edits](https://igamenovoer.github.io/houmao/reference/gateway/operations/versioned-file-edits/) · [Public Skills](https://github.com/igamenovoer/houmao-skills/tree/v3.0.0)
- **Backend mail filtering.** Offline registry and online Stalwart bindings work independently, including on keyed gateways. On qualified bindings, the mailbox backend applies owner-signed rules and files matching new mail directly in Archive, even while the gateway is stopped. [Agent Mail CLI](https://igamenovoer.github.io/houmao/reference/cli/agents-mail/)
- **Optional CCCC integration.** The independently installed `houmao-cccc` 0.3.0 plugin supports push ASAP by default, timed push batches, scheduled pull, gatewayless pull, and queued chat peek and pop. CCCC requires the patched external receiver protocol 2. [CCCC Integration](https://igamenovoer.github.io/houmao/reference/gateway/cccc/)

## Changed

- **Gateway authorization.** Retained policy supports signed identities, exact grants, and per-principal default fallback. Quoted work requests, direct prompts, and native commands use separate effects. Existing release-candidate observer assignments migrate to exact status grants with fallback disabled for the principal. [Authorization Policy](https://igamenovoer.github.io/houmao/reference/gateway/operations/authorization-policy/)
- **Mailbox API.** Select the `offline` or `online` channel and supply the current `expected_binding_id`. Mail writes return compact receipts. Recipient gateway roles no longer determine ordinary mail delivery. [Gateway Mailbox Contract](https://igamenovoer.github.io/houmao/reference/gateway/contracts/protocol-and-state/)

## Upgrade Notes

- Stop 2.4 agents with 2.4, retain their runtime data, and launch fresh sessions with 3.0. Use `defaults.posture.mode` for launch posture. Move legacy DSH settings to `tool-params.yaml` or `tool_params` and use `tool_params.permissions.sandbox: workspace-write` to retain the earlier DSH workspace boundary. [Launch Profiles](https://igamenovoer.github.io/houmao/getting-started/launch-profiles/) · [Launch Policy](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/)
- Enroll an administrator key before exposing a gateway that requires signed access. An initialized empty roster allows open administration. Replace retired `agent.prompt` grants with the appropriate exact effects. [Gateway Access](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/) · [Prompt Grant Migration](https://igamenovoer.github.io/houmao/reference/gateway/operations/authorization-policy/#migrate-prompt-grants)
- Protected mail filtering requires separate owner and backend authorities. Stalwart 0.15.5 passed native Archive filing, and an ordinary mailbox-owner login was refused for protected rule application. A deployment with restricted runtime credentials still needs qualification. [Stalwart Qualification](https://igamenovoer.github.io/houmao/reference/mailbox/operations/stalwart-qualification/#recipient-policy-qualification)

## Installation

```bash
uv tool install 'houmao==3.0.0'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0
```

[Compare v2.4.0 and v3.0.0](https://github.com/igamenovoer/houmao/compare/v2.4.0...v3.0.0)
