## Context

The current mailbox runtime guidance is split unevenly.

- Transport-specific mailbox skills such as `email-via-filesystem` and `email-via-stalwart` already live as packaged Markdown assets and are projected into runtime brain homes.
- The gateway mail-notifier wake-up prompt is still assembled inline in Python in `gateway_service.py`.
- The prompt currently gives the agent one nominated unread message and only a count of the remaining unread messages.
- The prompt also points at the direct Python resolver entrypoint, while the supported discovery surface for ordinary mailbox work is already `pixi run houmao-mgr agents mail resolve-live`.
- Joined sessions adopted through `houmao-mgr agents join` materialize a manifest-first runtime envelope, but they do not currently build a brain home or project the runtime-owned mailbox skill set into the adopted tool home.

That shape makes the wake-up contract harder to maintain and overfits the notifier to a single-target task queue rather than a mailbox queue. It also duplicates gateway-operation guidance across transport-specific skills and Python prompt text.

## Goals / Non-Goals

**Goals:**
- Introduce one runtime-owned common gateway mailbox skill that explains shared `/v1/mail/*` operations separately from transport-specific mailbox skills.
- Rename projected Houmao-owned mailbox skills to a `houmao-<skillname>` convention so runtime-owned Houmao skills are visibly distinct from user-authored skills.
- Make the `houmao-<skillname>` prefix the explicit trigger boundary so Houmao-owned skills activate only when the instruction text itself includes `houmao`.
- Structure that gateway skill as one index document plus action-specific subdocuments and curl-first examples.
- Make the “installed Houmao mailbox skills” assumption true for joined sessions by default instead of only for runtime-built homes.
- Make notifier prompts editable Markdown assets rendered through runtime placeholder replacement instead of hardcoded string assembly.
- Change notifier prompts to summarize all unread message headers in the current unread snapshot so the agent can decide what to inspect.
- Standardize gateway URL discovery on `pixi run houmao-mgr agents mail resolve-live` and the returned `gateway.base_url`.

**Non-Goals:**
- Adding new gateway mailbox routes beyond the existing `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`.
- Replacing transport-specific mailbox skills entirely; they still own transport-specific context, fallback, and layout guidance.
- Building a full generic skill package manager for joined sessions; this change covers only projection of Houmao-owned mailbox skills into reserved Houmao-owned paths.
- Changing notifier queue admission, deduplication, or idle-only scheduling rules outside the prompt payload they enqueue.
- Introducing a full template engine; the notifier renderer remains simple string replacement over packaged Markdown.

## Decisions

### 1. Add a common gateway mailbox skill, rename Houmao-owned skills, and narrow transport skills

The runtime-owned mailbox skill projection will always include a common gateway skill under `skills/mailbox/houmao-email-via-agent-gateway/` for mailbox-enabled sessions. Transport-specific skills remain projected alongside it.

Projected Houmao-owned mailbox skills will follow a `houmao-<skillname>` naming convention, for example:
- `skills/mailbox/houmao-email-via-agent-gateway/`
- `skills/mailbox/houmao-email-via-filesystem/`
- `skills/mailbox/houmao-email-via-stalwart/`

That prefix is not only a naming marker. It is also the invocation boundary: Houmao-owned skills should trigger only when the instruction text explicitly includes the keyword `houmao`, for example `use houmao-email-via-agent-gateway`, `use houmao to send mail`, or `send to houmao agent ...`.

The common gateway skill will use this structure:

```text
skills/mailbox/houmao-email-via-agent-gateway/
├── SKILL.md
├── actions/
│   ├── resolve-live.md
│   ├── check.md
│   ├── read.md
│   ├── send.md
│   ├── reply.md
│   └── mark-read.md
└── references/
    ├── endpoint-contract.md
    └── curl-examples.md
```

`SKILL.md` becomes a short index that tells the agent to:
- run `pixi run houmao-mgr agents mail resolve-live`,
- obtain `gateway.base_url`,
- open the action document that matches the needed mailbox operation,
- prefer curl against `/v1/mail/*` when the gateway is available.

Because this skill is projected into every mailbox-enabled runtime that has gateway-backed mailbox support, notifier prompts will treat it as already installed operational guidance for the current turn rather than as optional background reading.
Those prompts must still name the skill with the `houmao-...` prefix so the explicit `houmao` trigger word appears in the instruction itself.

The transport-specific skills continue to explain:
- how to validate the resolved transport,
- transport-specific fallback behavior when `gateway: null`,
- transport-local layout and policy guidance,
- transport-local authority for read/unread verification.

Alternative considered: keeping gateway operation guidance duplicated inside `email-via-filesystem` and `email-via-stalwart`. Rejected because the route contract is transport-neutral and should be edited in one place.

### 2. Install Houmao-owned mailbox skills during `agents join` by default

Joined sessions do not currently get a brain-home build step, so they cannot rely on runtime-owned mailbox skills already being present. This change will extend `houmao-mgr agents join` to project the Houmao-owned mailbox skill set into the adopted tool home by default.

That projection should:
- resolve the joined tool home through the existing join home resolution path,
- write only into the adapter’s skills destination,
- write only into reserved Houmao-owned skill paths such as `skills/mailbox/houmao-*`,
- avoid deleting or overwriting unrelated user-authored non-Houmao skill directories,
- fail the join explicitly when default installation is required but the adopted tool home cannot be resolved or written safely.

The join command should expose an explicit opt-out such as `--no-install-houmao-skills`. When the operator opts out, later runtime prompts must not assume the Houmao-owned mailbox skills are installed for that joined session.

Alternative considered: leaving join unchanged and expecting the gateway to install skills later. Rejected because the gateway is currently a prompt-submission component, not a home-mutating installer lifecycle.

### 3. Prefer curl-first mailbox operation guidance

The common gateway skill documents the shared mailbox routes as explicit curl commands, not just abstract JSON shapes.

The notifier prompt will reference:
- `pixi run houmao-mgr agents mail resolve-live` for discovery,
- `gateway.base_url` as the exact mailbox endpoint prefix,
- the installed common gateway skill path and an explicit instruction to use that skill for the current mailbox turn,
- explicit curl examples for check, send, reply, and mark-read.

Alternative considered: recommending custom helper scripts or Python-module entrypoints. Rejected because curl is clearer, already available, and keeps the agent on the supported public contract.

### 4. Use the manager-owned resolver as the only ordinary gateway URL discovery path

Notifier prompts and the new gateway skill will direct the agent to:

```bash
pixi run houmao-mgr agents mail resolve-live
```

The agent must obtain the live gateway endpoint from the returned `gateway.base_url`. The prompt may still inline the current `base_url` as bounded redundancy, but it will present that value as matching the resolver output rather than as an independently discovered secret.

Alternative considered: continuing to point agents at `python -m houmao.agents.mailbox_runtime_support resolve-live`. Rejected because ordinary mailbox work should stay on the manager-owned CLI contract.

### 5. Replace the nominated-target notifier prompt with an unread-summary prompt

When the notifier sees unread mail and enqueues one internal prompt, that prompt will summarize all unread messages in the current unread snapshot instead of nominating only one target.

Each summary entry will include:
- `message_ref`
- optional `thread_ref`
- `from`
- `subject`
- `created_at_utc`

The prompt will instruct the agent to:
- use the installed `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md` skill for this mailbox turn,
- resolve live bindings first,
- use curl and `/v1/mail/check` to inspect current unread details,
- decide which unread message or messages to inspect and handle,
- mark messages read only after the corresponding work succeeds.

The notifier still enqueues one prompt per unread snapshot digest and keeps deduplication keyed to the full unread set. This change affects prompt content, not queueing policy.

Alternative considered: continuing to nominate one oldest message while merely appending a lightweight summary of the rest. Rejected because it still oversteers the agent and does not match the user’s desired mailbox-triage behavior.

### 6. Store the notifier prompt as a Markdown asset template

The notifier prompt body will move to a packaged Markdown asset, for example:

```text
src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md
```

At runtime, the gateway service will:
- load the packaged template,
- pre-render dynamic blocks such as the unread header summary and curl snippets,
- replace placeholders like `{{RESOLVE_LIVE_COMMAND}}`, `{{GATEWAY_SKILL_PATH}}`, `{{TRANSPORT_SKILL_PATH}}`, `{{GATEWAY_BASE_URL}}`, and `{{UNREAD_HEADERS_BLOCK}}`,
- enqueue the rendered Markdown as the internal notifier prompt.

The rendered template should use directive wording, for example instructing the agent to use the installed `houmao-email-via-agent-gateway` skill for the turn, rather than merely listing the gateway skill path as a reference.

The renderer remains intentionally simple: plain string replacement, no branching template engine.

Alternative considered: keeping Python string assembly or introducing Jinja. Rejected because the first keeps content edits code-bound, and the second adds unnecessary templating complexity.

## Risks / Trade-offs

- [Prompt becomes longer when many unread messages exist] → Keep the unread summary to header-level fields only and rely on `/v1/mail/check` for full details.
- [Agents may process multiple unread messages in one turn unpredictably] → Phrase the prompt around triage and explicit read-state discipline rather than forcing one-message-only or all-messages-now behavior.
- [Joined-session installation can fail on unwritable tool homes] → Fail join closed by default when Houmao-owned mailbox skill projection is required and the adopted home cannot be updated safely; provide an explicit operator opt-out only when they accept a reduced contract.
- [Houmao-owned skills could trigger too broadly] → Keep the `houmao-<skillname>` prefix mandatory and require runtime prompts to include `houmao` explicitly when they intend to trigger a Houmao-owned skill.
- [Skill renaming could break existing path assumptions] → Update runtime projection, notifier wording, and tests together so Houmao-owned mailbox skill paths move consistently to the `houmao-<skillname>` convention.
- [Transport skills and gateway skill may drift] → Keep gateway route guidance only in the common gateway skill and reduce transport skills to transport-specific guidance.
- [Template placeholder drift can break prompt rendering silently] → Keep the placeholder set small, test rendered prompt text, and validate that required placeholders are fully replaced.
- [Changing prompt wording can break tests that assert literal strings] → Update tests to assert the new unread-summary contract and the new resolver/skill references rather than the old nominated-target text.
