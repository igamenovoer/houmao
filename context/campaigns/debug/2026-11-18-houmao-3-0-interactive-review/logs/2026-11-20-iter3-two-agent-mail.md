# Iteration 3: Two-Agent Local Filesystem Mail and Notifier

Date: 2026-11-20. Status: M1 and M2 passed end to end on Houmao `3.0.0rc5` with a DSH Web sender and a Kimi Web receiver, then the reverse. M3 is partial: notifier disable was verified, busy-skip was not exercised. The agents remain running for operator inspection; teardown is pending.

Plan: [Iteration 3](../iterations/2026-11-20-plan-3-mailbox-two-agent.md). Question: [KQ-4](../key-questions/KQ-4-local-mailbox-and-notifier.md).

## Target

- Houmao: uv-installed `houmao-mgr 3.0.0rc5` on Python 3.13.
- DSH: `0.2.2-rc.3`, mode `web`, backend `dsh_web`.
- Kimi: `2.6.0`, mode `web`, backend `kimi_web`.
- Model: `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`; Kimi's credential bundle recorded `KIMI_MODEL_NAME=Qwen/Qwen3.8-27B-FP8` and `KIMI_MODEL_BASE_URL=http://127.0.0.1:14888/v1`.
- Shared root: `tmp/houmao-30-iter3-mailbox/`.
- Shared registry: `tmp/houmao-30-iter3-mailbox/registry/`.
- Shared mailbox: `tmp/houmao-30-iter3-mailbox/mailbox/`.
- Notifier: `offline`, interval `30s`, mode `unread_only`.

| Item | DSH agent | Kimi agent |
| --- | --- | --- |
| Agent ID | `b6061ec2-d61e-459c-90e2-5e2c2225ae31` | `060bcdea-9b08-4eeb-a848-0acac039833e` |
| Name | `dsh-mailer` | `kimi-mailer` |
| Address | `dsh-mailer@houmao.localhost` | `kimi-mailer@houmao.localhost` |
| Offline binding | `reg-75207f251a7f442299a36775cb1f172c` | `reg-792e2775fb1b4fd3af2f5e1c46bf6edf` |
| Gateway | `http://127.0.0.1:37405` | `http://127.0.0.1:37406` |
| Native origin | `http://127.0.0.1:43637` | `http://127.0.0.1:42783` |
| Native session | `session-47be914a-0a5c-42eb-a780-87633e3417cc` | `session_c3b0f0ce-0637-4d86-b163-3b5dd551c6ff` |
| Tmux session | `HOUMAO-dsh-mailer-1795163599024` | `HOUMAO-kimi-mailer-1795163611074` |
| Tmux socket | `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-web-manager-afbcc18168bc` | `/tmp/tmux-1001/houmao-fixture-self-hosted-kimi-web-manager-c3a0be7f97a8` |

Run directories:

- `tmp/houmao-30-iter3-mailbox/runs/self-hosted-dsh-web-manager-afbcc18168bc`
- `tmp/houmao-30-iter3-mailbox/runs/self-hosted-kimi-web-manager-c3a0be7f97a8`

## Progress

- `08:33:19Z` DSH Web launch; `08:33:31Z` Kimi Web launch.
- `08:33:45Z` and `08:33:51Z` both offline notifiers enabled at `30s` / `unread_only`.
- `08:35:08Z` DSH sent the first message.
- `08:35:22Z` Kimi notifier enqueued; `08:35:29Z` Kimi replied and archived.
- `08:35:46Z` DSH notifier enqueued; `08:35:53Z` DSH replied and archived.
- `08:36:04Z` and `08:36:05Z` both notifiers disabled to stop the reply chain.
- After a further 35 seconds, no new notifier request existed; Kimi's inbox retained one unread DSH reply.

## Setup Path

The maintained fixture prepares each run with its own registry root, so the stock `fixture.py launch` cannot place two agents in one offline authority. The campaign launched each prepared run through a local shared-root launcher, `tmp/houmao-30-iter3-mailbox/bin/launch_shared.py`, which:

1. loads the prepared run's private environment and tmux shim,
2. overrides `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, and `HOUMAO_GLOBAL_MAILBOX_DIR` to the shared root,
3. calls the maintained in-process manager with `--gateway-background --mode web --mail-transport filesystem --mail-root <shared root>`.

The shared authority was initialized once:

```bash
houmao-mgr mailbox init \
  --registry-root tmp/houmao-30-iter3-mailbox/registry \
  --mailbox-root tmp/houmao-30-iter3-mailbox/mailbox
```

Both launch identities reported `mailbox_root` at the shared root and an active offline binding. `mailbox offline status` returned `activation_state: active` for both agents.

Attach and login helpers:

- `tmp/houmao-30-iter3-mailbox/attach-dsh-mailer.sh`
- `tmp/houmao-30-iter3-mailbox/attach-kimi-mailer.sh`
- `tmp/houmao-30-iter3-mailbox/login-dsh-mailer.sh`
- `tmp/houmao-30-iter3-mailbox/login-kimi-mailer.sh`

The attach scripts resolve the tmux session and socket from the manifest with `load_session_manifest()` at execution time. The login scripts issue a fresh `gateway web-entry` link and write it to a private `0600` file.

## M1: DSH to Kimi

At `08:35:08Z`, DSH sent:

```text
To: kimi-mailer@houmao.localhost
Subject: Mailbox wake test
Body: Reply with MAIL-OK and archive this message.
```

The send result was `status: verified`, `authoritative: true`, `transport: filesystem`, `execution_path: gateway_backed`.

Kimi's notifier:

- `08:35:22Z` audit row `outcome: enqueued`, `unread_count: 1`, request `gwreq-20261120-083522Z-f4fc705f`.
- The gateway request completed at `08:35:33Z`.
- Kimi's native turn read the message, replied with `MAIL-OK: acknowledged Mailbox wake test (2026-11-20). Message will be archived.`, and archived the original.
- Kimi's inbox was empty afterward; its sent box contained the reply.

The Kimi native journal shows the exact API sequence: `GET /v1/mail/status`, `POST /v1/mail/offline/list`, `POST /v1/mail/offline/read`, `POST /v1/mail/offline/reply`, then `POST /v1/mail/offline/archive`.

## M2: Kimi to DSH

Kimi's reply arrived in DSH's inbox at `08:35:29Z`. DSH's notifier:

- `08:35:46Z` audit row `outcome: enqueued`, `unread_count: 1`, request `gwreq-20261120-083546Z-187fbe09`.
- The gateway request completed at `08:35:56Z`.
- DSH's native turn read the reply, replied with `MAIL-OK: acknowledged "Re: Mailbox wake test" from kimi-mailer (2026-11-20). Round processed; original message archived.`, and archived the reply.
- DSH's inbox was empty afterward; its sent box held both the original message and the reply to Kimi.

The DSH native journal shows the same API sequence with `POST /v1/mail/offline/reply` and `POST /v1/mail/offline/archive`.

Both gateways recorded exactly one completed `mail_notifier_prompt` request each:

| Agent | Request | Accepted | Completed | State |
| --- | --- | --- | --- | --- |
| Kimi | `gwreq-20261120-083522Z-f4fc705f` | `08:35:22Z` | `08:35:33Z` | `completed` |
| DSH | `gwreq-20261120-083546Z-187fbe09` | `08:35:46Z` | `08:35:56Z` | `completed` |

## Errors Observed

The notifier prompt's fallback API summary is only:

```text
Mailbox API: `GET /v1/mail/status`; `POST /v1/mail/list|peek|read|reply|send|post|mark|move|archive`.
```

It does not include request-body fields. Both agents therefore guessed the schemas and made one failed call per operation before correcting themselves.

### DSH and Kimi: reply with `body`

Request body used:

```json
{"expected_binding_id": "...", "message_ref": "...", "body": "..."}
```

Gateway response:

```json
{"detail":[{"type":"missing","loc":["body","body_content"]},{"type":"extra_forbidden","loc":[]}]}
```

The correct field is `body_content`. Both agents retried successfully with that field. The shell result was marked `isError: false` because `curl -s` exits zero on HTTP 422; the agent inferred the failure from the JSON body.

### DSH and Kimi: archive with `message_ref`

Request body used:

```json
{"expected_binding_id": "...", "message_ref": "..."}
```

Gateway response:

```json
{"detail":[{"type":"missing","loc":["body","message_refs"]},{"type":"extra_forbidden","loc":[]}]}
```

The correct field is `message_refs` with a list value. Both agents retried successfully with that shape.

### DSH: list body probing

Before the first successful list, DSH tried two incomplete bodies and received:

```json
{"detail":[{"type":"missing","loc":["body"]}]}
```

```json
{"detail":[{"type":"missing","loc":["body","expected_binding_id"]}]}
```

A body containing only `expected_binding_id` succeeded. This is the same root cause: the fallback summary names endpoints but not their required request fields.

### Campaign launcher: specialist path

The first shared-root launch failed before creating an agent:

```text
Error: --specialist must not contain path separators.
```

Cause: `run.json` stores the specialist as an object, and the launcher passed the whole object instead of `run["specialist"]["specialist"]`. This is a campaign-helper bug, fixed before the successful launch; it is not a Houmao defect.

### DSH Web entry: 401 under plain curl

A fresh `gateway web-entry` URL returned `401` at the DSH origin when fetched with `curl -L` without cookie storage. With a cookie jar, the same entry returned `200` and the `DeepSeek Harness` page. The one-time entry relies on browser cookie handling; this is a verification detail, not a confirmed product bug.

### Kimi Web state: missing model metadata

`agents single state` reported `web.model: null` for Kimi although the credential bundle selected `Qwen/Qwen3.8-27B-FP8` and the native turns used it. This is an observability gap in the Kimi Web state surface.

### Reply chain

The test role replies to every wake-up and archives. Kimi replied to DSH's original, DSH replied to Kimi's reply, and DSH's reply remained unread in Kimi's inbox as new eligible mail. Re-enabling Kimi's notifier would wake it and repeat the pattern. Both notifiers were disabled before the next wake-up. This is a role-design issue rather than a notifier defect, but it is a real risk for mailbox-driven loops that lack a stop rule.

## Bug and Design-Flaw Classification

- **Product design-flaw candidate: notifier fallback schema gap.** The notifier prompt's fallback API summary names endpoints but not request fields. Both agents made one failed `reply` and one failed `archive` call, and DSH probed `list` bodies twice. The backend returned clear 422 errors, but an agent without the mailbox skill pack wastes turns guessing. Candidate fix: include a compact schema for `list`, `reply`, and `archive` in the fallback, or ensure the managed mailbox skill pack is always present. Source: `gateway_service.py:683` renders the summary.
- **Product observability gap: Kimi Web model is null.** `agents single state` shows `web.model: null` while the configured provider is Qwen. Candidate fix: surface the effective configured model on the Kimi Web state.
- **Product behavior to document: notifier repeats until eligibility ends.** `unread_only` wakes once per unread message, and every reply creates new eligible mail. This is documented as repeat-notification behavior, but the campaign's first two-agent test exposed the practical reply-loop risk. Candidate fix: document a loop-termination rule in the mailbox skill guidance, or add a "do not reply to replies" convention.
- **Test-harness defect: shared-root launcher specialist object.** The launcher passed the whole specialist object and failed with `--specialist must not contain path separators`. Fixed in the campaign helper; not a product defect.
- **Verification false alarm: DSH entry 401 without cookies.** A plain `curl -L` does not persist the entry cookie. A browser or a cookie jar succeeds. Not a confirmed product bug.
- **No product defect: shared registry requirement.** Offline filesystem mail requires one registry authority. The maintained fixture isolates a registry per run, so a shared-root launch path was required. This is a test-harness constraint, not a Houmao defect.

## Notifier Behavior

- Both agents reported `supported: true` before any mail.
- Both notifiers produced `empty` audit rows while the inbox was empty.
- `unread_only` selected the unread original and the unread reply, one wake-up per eligible message.
- The notifier disabled cleanly on both agents at `08:36:04Z` and `08:36:05Z`.
- After disable, a 35-second observation produced no new notifier request. The Kimi inbox still held DSH's second reply, unread, with no wake-up.
- `mail peek` on that unread reply returned the body and preserved `read: false` / `unread: true`.

## Findings

1. **Shared offline authority works across different Web backends.** A DSH Web agent and a Kimi Web agent can share one registry and mailbox root, hold distinct addresses, and exchange filesystem mail in both directions.
2. **Gateway notifier wake-up works on both Web backends.** Each side's notifier enqueued one internal prompt, the native turn ran, and the mail round completed. The gateway request records show no duplicate admission or replay.
3. **The notifier prompt is sufficient without the managed agent skill pack.** The fixture set `system_skills.mode: none`, so neither agent had `houmao-agent-entrypoint` or the mailbox skills. Both agents used the notifier's inline API summary and completed the round through direct `/v1/mail/offline/*` calls.
4. **The fallback API summary lacks exact field names.** Both agents first tried `archive` with `message_ref` and `reply` with `body`; the endpoints expect `message_refs` and `body_content`. Each recovered after one failed call. See **Errors Observed** for the exact 422 bodies. A normal managed launch with the mailbox skill pack may avoid it; this run does not qualify that path.
5. **The reply policy creates a repeating reply chain.** The role instructed every wake-up to reply to the sender and archive. Kimi replied to DSH's original, DSH replied to Kimi's reply, and DSH's reply remained unread in Kimi's inbox as new eligible mail. Both notifiers were disabled before the next wake-up. This is expected behavior for the role, not a notifier defect, but future mail tests need an explicit stop rule such as "reply only to non-`Re:` subjects" or "archive without replying after the first round."
6. **`unread_only` plus archive is clean.** Archiving the original removed it from eligibility. A reply that arrived after the recipient's poll remained unread and did not wake after the notifier was disabled.
7. **Kimi Web state does not expose the selected model.** `agents single state` reported `web.model: null` for Kimi, while the credential bundle selected Qwen and the native turns used it. This is an observability gap, not a routing failure.
8. **Gateway Web entry works for both agents.** Kimi's one-time entry reached `Kimi Code Web` at the bound session. DSH's one-time entry needed a cookie jar under `curl`; without cookie storage the native origin returned `401`, and with it the page returned `DeepSeek Harness` at `200`. A real browser stores the cookie normally.
9. **Busy-skip is not tested.** No message was sent while a target was mid-turn, so M3's `busy_skip` outcome remains unverified.

## Next Steps

- Add a stop rule to the mail-test role and repeat a two-message exchange without a reply loop.
- Run one busy-skip case: send mail while the target is processing an unrelated long turn, then inspect the notifier audit for `busy_skip` and later eligibility.
- Decide whether the notifier fallback should name exact request fields for `reply` and `archive`, or whether all managed agents should receive the mailbox skill pack.
- Inspect Kimi Web state/model reporting and close the `web.model: null` gap.
- Tear down both agents after operator inspection and record the final G4 result.

## Reproduction Commands

```bash
export ROOT=/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox
export HOUMAO_GLOBAL_REGISTRY_DIR="$ROOT/registry"
export HOUMAO_GLOBAL_MAILBOX_DIR="$ROOT/mailbox"
export M=/home/huangzhe/.local/share/uv/tools/houmao/bin/houmao-mgr

"$M" --print-json agents single --agent-id b6061ec2-d61e-459c-90e2-5e2c2225ae31 state
"$M" --print-json agents single --agent-id 060bcdea-9b08-4eeb-a848-0acac039833e state
"$M" --print-json agents single --agent-id b6061ec2-d61e-459c-90e2-5e2c2225ae31 mailbox offline status
"$M" --print-json agents single --agent-id 060bcdea-9b08-4eeb-a848-0acac039833e mailbox offline status
"$M" --print-json agents single --agent-id 060bcdea-9b08-4eeb-a848-0acac039833e gateway mail-notifier status --channel offline
"$M" --print-json agents single --agent-id b6061ec2-d61e-459c-90e2-5e2c2225ae31 gateway mail-notifier status --channel offline
```
