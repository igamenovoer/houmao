# Iteration 3 R9: Fresh Agents With Concise Coordination Rules

Date: 2026-11-23. Status: stopped 2026-11-24 and replaced by [R10 launch-profile xhigh](2026-11-24-iter3-two-agent-mail-r10-launch-profile-xhigh.md). No R9 prompt or mail was sent. The R9 reasoning diagnosis remains the reference for the launch-profile correction applied in R10.

Previous run: [R8 default system prompt](2026-11-23-iter3-two-agent-mail-r8-default-system-prompt.md).

## Clean Start and Prompt Rules

R8 Kimi's notifier was disabled and its owned native Web host stopped successfully. R8 DSH was already stopped by its own recovery cascade. Its maintained gateway-detach path refused the inactive registry record, so the controller verified and terminated only the remaining R8 gateway process with `SIGTERM`. Both gateway ports were free before R9 launch.

R9 uses a new root with fresh registry, mailbox, runtime homes, and native conversations:

```text
tmp/houmao-30-iter3-mailbox-r9/
```

The manager remains `3.0.0rc5+local.9c66cb3`, with DSH `0.2.2-rc.3`, host Kimi `2.7.2`, and self-hosted `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`. The default managed agent system-skill policy remains enabled.

Both agents received this prompt file through `--system-prompt-file`:

```text
tmp/houmao-30-iter3-mailbox-r9/inputs/coordination-rules.txt
```

Its complete rules are:

1. For anything Houmao-related, load and follow `houmao-agent-entrypoint` first.
2. Use mail to contact other agents by default unless the operator specifies another method.
3. For other agents, use read-only inspection only. Do not modify their tmux, processes, lifecycle, homes, or runtime state unless the agent was started as the actor's child or the operator explicitly requests the manipulation in a direct prompt. Otherwise, do not attempt peer recovery implicitly; report the failure instead.

No acknowledgement-only role, `MAIL-OK` instruction, smoke-test role, or other campaign role was added.

## Fresh Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `881c142e-4765-4c1d-bd0c-b14982242e89` | `c5e1a379-cf7e-4629-85fd-44e687e100ae` |
| Name | `dsh-mailer-r9` | `kimi-mailer-r9` |
| Address | `dsh-mailer-r9@houmao.localhost` | `kimi-mailer-r9@houmao.localhost` |
| Offline binding | `reg-92a0f7c3189f4d78b6821e45fea4ec4a` | `reg-fd4e700ba5dc4eccb9d6d90bc5c4b491` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:40733` | `http://127.0.0.1:35337` |
| Native session | `session-052a434f-bc5a-4ee3-8dd6-3b9fce51d44b` | `session_e83c570a-d108-4b5f-8570-fc54fb809d3d` |
| Runtime session | `dsh_web-20261123-114657Z-09eaa1f2` | `kimi_web-20261123-114701Z-9ea3a97c` |
| Tmux session | `HOUMAO-dsh-mailer-r9-1795434417083` | `HOUMAO-kimi-mailer-r9-1795434421967` |
| Prepared run | `runs/self-hosted-dsh-web-manager-30b8db30b7a5` | `runs/self-hosted-kimi-web-manager-7871923bafec` |

Both gateways report healthy, connected, idle, `queue_depth: 0`, and `request_admission: open`. Dashboard roots return HTTP 200 and both `/v1/web/enter` routes return HTTP 302.

Ticketless entrance links:

```text
http://127.0.0.1:37605/v1/web/enter
http://127.0.0.1:37606/v1/web/enter
```

Manifest-based watch and login helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r9/attach-dsh-mailer-r9.sh
tmp/houmao-30-iter3-mailbox-r9/attach-kimi-mailer-r9.sh
tmp/houmao-30-iter3-mailbox-r9/login-dsh-mailer-r9.sh
tmp/houmao-30-iter3-mailbox-r9/login-kimi-mailer-r9.sh
```

Both attach helpers passed `--print-target` checks. Login helpers passed shell-syntax checks but were not used to issue ticket URLs.

## Prompt Verification

Both live runtime manifests contain all three requested rules, including the child-agent and direct-operator exceptions. Neither manifest contains `MAIL-OK` or `server-api-smoke`.

## Notifier State Before Mail

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true`. Their first observed polls completed with `last_error: null`:

- DSH: `2026-11-23T11:47:42Z`, no notification.
- Kimi: `2026-11-23T11:47:42Z`, no notification.

The local mailbox root is `tmp/houmao-30-iter3-mailbox-r9/mailbox/`. Do not claim request execution, delivery, reply, archive, or teardown until those events are observed in R9.

## Reasoning Configuration Errors

The R9 launch used the native default thinking level `off` for both agents. This was a controller error: the intended level was `xhigh`, but no reasoning override was supplied. The DSH mapping declares positive slots `low=1`, `medium=2`, and `xhigh=3`, with `off=0` handled separately (`src/houmao/agents/model_mapping_policy.py:448-492`). The fixture exposes `--reasoning-effort xhigh` for Kimi and maps it to `KIMI_MODEL_THINKING_EFFORT` (`scripts/agents/test-fixtures/fixturelib/prepare.py:277-278`), but that flag was omitted.

Kimi's disabled thinking selector is a related but distinct launch-metadata problem. Its live `/api/v1/models` response identifies the temporary env-defined model as `__kimi_env_model__` with only `capabilities: ["tool_use"]`. It advertises no thinking capability and no supported-effort catalog. The fixture defaults to `tool_use` and wrote `KIMI_MODEL_CAPABILITIES=tool_use`; no `thinking` capability or `KIMI_MODEL_THINKING_EFFORT` was supplied.

Houmao's own Kimi mapping path explicitly rejects launch-owned reasoning levels for env-defined models because they expose no ordered effort catalog (`src/houmao/agents/model_mapping_policy.py:521-539`). Forcing an effort through the env var and offering an operator-selectable effort catalog are therefore separate concerns. A config-backed model alias with `support_efforts` is the documented path for an ordered catalog; `KIMI_MODEL_THINKING_EFFORT` is the fixture's direct xhigh input.

Official Kimi references checked during diagnosis:

- [Environment variables](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/env-vars.html): `KIMI_MODEL_CAPABILITIES` and `KIMI_MODEL_THINKING_EFFORT`, including `xhigh`.
- [Configuration files](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/config-files.html): model `capabilities`, `support_efforts`, `default_effort`, and `[thinking]`.
- [Providers and models](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/providers.html): OpenAI reasoning support and capability detection.

No R9 restart or reasoning correction has been applied yet.
