# Iteration 3 R8: Fresh Web Agents With Default System Prompts

Date: 2026-11-23. Status: running with default native and Houmao-managed prompts, healthy gateways, and enabled mail notifiers. No R8 prompt or mail has been sent yet.

Previous run: [R7 unified launch environment](2026-11-23-iter3-two-agent-mail-r7-unified-launch-env.md).

## Clean Start and Prompt Neutrality

Both R7 notifiers were disabled and both owned native Web hosts stopped successfully. R8 uses a new root with fresh registry, mailbox, runtime homes, and native conversations:

```text
tmp/houmao-30-iter3-mailbox-r8/
```

The manager remains `3.0.0rc5+local.9c66cb3`, with DSH `0.2.2-rc.3`, host Kimi `2.7.2`, and self-hosted `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`. The default managed agent system-skill policy remains enabled.

The fixture always assigns a role. Omitting `--system-prompt-file` would select its built-in `server-api-smoke` role rather than no role. After preparing each temporary R8 project, the launch materials were therefore normalized through the maintained command:

```text
houmao-mgr project --project-dir <run-workdir> specialist set --name fixture-agent --clear-system-prompt
```

Both specialists then reported `system_prompt: null` before launch. No campaign role, smoke-test role, or prompt-overlay text was supplied. The default Houmao managed header and native client prompts remain enabled.

## Fresh Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `078335aa-0283-42e2-9958-fd4eb2472e82` | `b68e8683-9f6c-4284-8439-3226be4cbba8` |
| Name | `dsh-mailer-r8` | `kimi-mailer-r8` |
| Address | `dsh-mailer-r8@houmao.localhost` | `kimi-mailer-r8@houmao.localhost` |
| Offline binding | `reg-b1daec5612c44f10ab4dd67d3ec3b32e` | `reg-1820d4ca6baf41df9a7156bb1266d0fc` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:45787` | `http://127.0.0.1:33651` |
| Native session | `session-4f5f1572-40a3-4232-91e5-d62b37fe2d73` | `session_2aa0ffbe-5357-4b69-ba3e-33d09474727a` |
| Runtime session | `dsh_web-20261123-111712Z-0674bde4` | `kimi_web-20261123-111716Z-0bf9c38d` |
| Tmux session | `HOUMAO-dsh-mailer-r8-1795432632067` | `HOUMAO-kimi-mailer-r8-1795432636961` |
| Prepared run | `runs/self-hosted-dsh-web-manager-0998ab946d1a` | `runs/self-hosted-kimi-web-manager-134dd2c6971c` |

Both gateways report healthy, connected, idle, `queue_depth: 0`, and `request_admission: open`. Dashboard roots return HTTP 200 and both `/v1/web/enter` routes return HTTP 302.

Ticketless entrance links:

```text
http://127.0.0.1:37605/v1/web/enter
http://127.0.0.1:37606/v1/web/enter
```

Manifest-based watch and login helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r8/attach-dsh-mailer-r8.sh
tmp/houmao-30-iter3-mailbox-r8/attach-kimi-mailer-r8.sh
tmp/houmao-30-iter3-mailbox-r8/login-dsh-mailer-r8.sh
tmp/houmao-30-iter3-mailbox-r8/login-kimi-mailer-r8.sh
```

Both attach helpers passed `--print-target` checks. Login helpers passed shell-syntax checks but were not used to issue ticket URLs.

## Prompt Verification

Both live runtime manifests contain the default `<houmao_system_prompt>` managed header only. Neither manifest contains `<prompt_body>`, `<role_prompt>`, `MAIL-OK`, `two-agent mailbox`, or `server-api-smoke`.

Materialized prompt files:

```text
tmp/houmao-30-iter3-mailbox-r8/runtime/homes/dsh-brain-20261123-111711Z-b779e9/houmao-role.txt
tmp/houmao-30-iter3-mailbox-r8/runtime/homes/kimi-brain-20261123-111716Z-a1c96b/SYSTEM.md
```

The DSH role file is nonempty because it contains the default managed header, not because a custom role remains. Kimi's `SYSTEM.md` likewise contains the default managed header and native client prompt without the campaign role.

## Notifier State Before Mail

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true`. Their first observed polls completed with `last_error: null`:

- DSH: `2026-11-23T11:18:26Z`, no notification.
- Kimi: `2026-11-23T11:18:27Z`, no notification.

The local mailbox root is `tmp/houmao-30-iter3-mailbox-r8/mailbox/`. Do not claim request execution, delivery, reply, archive, or teardown until those events are observed in R8.

## Browser Connection-Refused Investigation

The operator reported a connection refusal and asked for diagnosis without a fix. At `2026-11-23T11:25Z`, both R8 agents and native processes were alive, both gateways were healthy, and both native ports accepted TCP connections. Following each exact R8 `/v1/web/enter` route through authentication returned HTTP 200 and the expected native application for both DSH and Kimi. The gateway entry responses carry `Cache-Control: no-store`. A direct unauthenticated DSH native-root request returned HTTP 401, not a connection refusal; its gateway-mediated authenticated flow returned 200.

The previous R7 native listeners at `127.0.0.1:39983` and `127.0.0.1:41187` now return `connect_ex=111` because R7 was stopped. The current R8 listeners are different ports, `45787` and `33651`, and return `connect_ex=0`. A stale R7 native ticket URL was an initial hypothesis, but the operator then supplied the exact failing URL and it belonged to the current R8 DSH listener, so the stale-R7 explanation does not apply to that report. No restart, reconfiguration, or new ticket was applied as a fix.

## Exact R8 URL Reproduction

The operator supplied the current R8 DSH native URL, including its authentication ticket and Houmao entry fragment. A real headless Chromium session opened that exact URL successfully: the initial navigation returned HTTP 200, the page title was `DeepSeek Harness`, the `workdir` Workspace loaded, and no console error, page error, failed request, or HTTP error response was observed. The browser displayed the managed DSH conversation interface rather than a connection error.

This rules out an invalid ticket and a dead R8 native listener for the supplied URL. The refusal is localized to the operator browser's network path to `127.0.0.1:45787`, such as a browser running on another machine or a missing native-port forward. The gateway redirect itself is not the failing operation in the reproduced browser flow. No tokens or ticket URLs are recorded here. The diagnostic script and screenshot are disposable R8 materials under `tmp/houmao-30-iter3-mailbox-r8/`; no product configuration was changed.

## Windows VS Code Port-Forward Evidence

A subsequent operator-side report supplied the missing network evidence for Kimi. On Windows, port `37606` is owned by `Code.exe`, while no Windows listener exists on native port `33651`. This is consistent with VS Code forwarding the gateway port but not the separately allocated native Web port. It is not evidence that the Linux native process is absent.

At the same time, the Linux side showed all of the following:

- `127.0.0.1:37606` accepted TCP and returned HTTP 200 for the gateway dashboard.
- `127.0.0.1:33651` accepted TCP and returned HTTP 200 for the Kimi native surface.
- Native Kimi process PID `1325045` was present and running as `kimi-code`.

The gateway status describes the managed Linux runtime, so `host_process_alive: true` and `web.availability: available` are accurate for that runtime. The Windows browser reaches a different loopback namespace. Its refusal on `127.0.0.1:33651` results from the missing Windows-side native-port listener or forward, not from an expired ticket, stale gateway health, or a dead native host. The report's statement that this is not a cross-namespace networking issue is contradicted by the `Code.exe` listener and the simultaneous Linux evidence.

Repeated `/v1/web/enter` redirects identify the existing managed native session; they are not expected to spawn a replacement listener. Relaunching the agent would not address the forwarding mismatch and could allocate another native port. No relaunch or other fix was applied.

## Kimi Direct-Prompt Recovery Cascade

The operator reported that Kimi became stuck after being asked to contact DSH. Kimi's native session shows the request `tell the dsh agent to find the most recent rsi papers via s2, tell it to find s2 keys in user's bashrc`. Kimi inspected prompt, turn, and mail help, then chose `agents single --agent-name dsh-mailer-r8 prompt --prompt ...`. It never invoked `mail send`, so this was not a blocked mailbox-delivery operation.

The direct prompt failed at approximately `2026-11-23T11:34:34Z` because the DSH registry record said `active` while its tmux-backed runtime authority was stale or missing. Kimi then entered an extended autonomous recovery sequence instead of reporting the failure:

1. It confirmed that DSH's isolated tmux session was absent while the native Web process still responded.
2. Two `relaunch` attempts failed with `DSH Web supervisor ownership has changed`.
3. The operator interrupted the first turn and asked `what is wrong`.
4. Kimi continued recovery during the diagnosis turn. It ran `cleanup session`, which removed the original DSH session root, but registry retirement was blocked by stale manifest authority.
5. A fresh `project agents launch --specialist fixture-agent --name dsh-mailer-r8 --mode web` failed with `DSH Web refuses to adopt an existing supervisor session`. It left a new native home and a partial session directory containing only a launch-environment file.
6. The operator interrupted the second turn while Kimi was inspecting the DSH Web source for that error.

The original DSH Web receipt records `created` at `2026-11-23T11:17:14Z` and `disposed` at `2026-11-23T11:35:27Z`. The disposal occurred after the initial prompt failure and during the recovery period, so it does not explain the earlier stale-tmux condition. The reason that tmux session initially disappeared remains unproven from the inspected records.

At the final inspection, Kimi was available but idle with `last_turn.result: interrupted`; it was not still executing a tool or blocked in the gateway. DSH was `stopped`, its native port `45787` refused connections, its isolated tmux server was absent, and its original gateway process remained alive on port `37605` as a remnant. The original session root had been removed by Kimi's cleanup attempt. No RSI/S2 instruction was delivered to DSH, and no mail was sent.

This was therefore an agent-driven recovery loop followed by user interruption, on top of a real DSH stale-runtime failure. It was not a hung `mail send` command or gateway queue deadlock. No corrective action was taken by the campaign controller during this diagnosis.

## R8 Controller Teardown

For the R9 restart, the controller disabled R8 Kimi's notifier and stopped its owned native Web host successfully. R8 DSH was already stopped by Kimi's recovery cascade, so the maintained `gateway detach` command refused to operate on its inactive registry record. The controller verified the remaining gateway process command line against the exact R8 gateway root and terminated only that process with `SIGTERM`; port `37605` then returned `connect_ex=111`. An initial process-identity assertion used an incorrect module path and terminated nothing; the corrected assertion matched `houmao.agents.realm_controller.gateway_service` before signaling the process. R9 uses fresh registry, mailbox, runtime homes, and native conversations.
