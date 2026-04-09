## Context

Gateway reminder behavior already exists in the live gateway itself through `/v1/reminders`, with typed local client support in `GatewayClient` and stable gateway reminder models in `gateway_models.py`. By contrast, the operator-facing `houmao-mgr agents gateway ...` tree currently stops at prompt control, raw send-keys, TUI inspection, and mail-notifier control, and the pair-managed `/houmao/agents/{agent_ref}/gateway...` proxy surface likewise stops short of reminders.

That split has three practical consequences:

- operators and automation must discover the exact live gateway URL and handcraft reminder HTTP requests,
- pair-managed targets cannot use `--pair-port` parity for reminder work even though nearby gateway features support it,
- Houmao-owned skills and docs must currently teach reminders as an exception to the usual managed-agent CLI surface.

This change is cross-cutting because it touches the native CLI, pair proxy API, skill guidance, and reference docs, but it does not change the gateway reminder model itself.

## Goals / Non-Goals

**Goals:**

- Provide a native `houmao-mgr agents gateway reminders ...` CLI family that fits the existing gateway command tree and selector model.
- Support reminder operations for both local managed-agent targets and pair-managed targets addressed through `--pair-port`.
- Keep ranking numeric while reducing operator friction through “prepend to highest priority” and “append to lowest priority” convenience flags.
- Preserve the direct `/v1/reminders` contract as the underlying live gateway API while making the CLI and managed-agent proxy the preferred operator surface.
- Update Houmao-owned skill and reference docs so reminder work is taught consistently with the rest of the gateway family.

**Non-Goals:**

- Changing gateway reminder scheduling semantics, ranking rules, pause semantics, or durability boundaries.
- Introducing durable reminder persistence across gateway restart.
- Exposing batch reminder authoring as a first-class CLI workflow in v1.
- Replacing or removing the direct `/v1/reminders` routes.

## Decisions

### 1. Add a `reminders` subgroup under `agents gateway`

The CLI surface will be:

- `houmao-mgr agents gateway reminders list`
- `houmao-mgr agents gateway reminders get --reminder-id <id>`
- `houmao-mgr agents gateway reminders create ...`
- `houmao-mgr agents gateway reminders set --reminder-id <id> ...`
- `houmao-mgr agents gateway reminders remove --reminder-id <id>`

Rationale:

- reminders are gateway-owned live state, so the reminder surface belongs beside `mail-notifier`, `prompt`, and `send-keys`,
- the group aligns with existing managed-agent selector behavior in `agents gateway`,
- `list/get/create/set/remove` fits Houmao’s existing CLI naming style better than raw HTTP verbs.

Alternatives considered:

- Keep reminders HTTP-only: rejected because it preserves the current inconsistency and keeps pair-managed targets second-class.
- Add a top-level `reminders` family: rejected because it weakens the gateway ownership boundary and duplicates target selection logic outside `agents gateway`.

### 2. Provide pair-managed reminder parity instead of a local-only CLI

The CLI will support the same selectors as the rest of `agents gateway`, including explicit managed-agent selectors, `--current-session`, `--target-tmux-session`, and `--pair-port`. To support that contract cleanly, the pair API will add managed-agent gateway reminder proxy routes under `/houmao/agents/{agent_ref}/gateway/reminders...`, plus matching server-client and pair-client methods.

Rationale:

- operators already expect `agents gateway` subcommands to work through either local controller authority or pair-managed authority,
- `mail-notifier` already proves that gateway-owned control can be proxied safely through the managed-agent pair seam,
- a local-only reminder CLI would create surprising partial support inside one command family.

Alternatives considered:

- Local-only CLI that rejects `--pair-port`: rejected because it would make reminder commands behave differently from adjacent gateway commands and would keep distributed operator workflows on raw HTTP.

### 3. Keep reminder ranking numeric, with two placement convenience modes

`create` will require exactly one ranking input:

- `--ranking <int>`
- `--before-all`
- `--after-all`

`set` will treat ranking change as optional, but if provided it must use the same mutually exclusive ranking modes.

Placement mode resolution:

- `--before-all` computes `min(existing_ranking) - 1`
- `--after-all` computes `max(existing_ranking) + 1`
- when the live set is empty, both convenience modes resolve to `0`

Rationale:

- the gateway model already treats lower integer values as higher priority,
- keeping raw integers avoids inventing another priority vocabulary,
- prepend/append flags solve the common “put this at the top/bottom” workflow without making users pick numbers manually.

Alternatives considered:

- Named priority buckets such as `high|normal|low`: rejected because they hide the real ranking model and reduce precision.
- Silent default-only ranking with no convenience flags: rejected because users still need predictable relative placement.

### 4. `create` is single-reminder oriented, and `set` is patch-like at the CLI layer

The CLI will accept one reminder definition per `create` invocation rather than raw batch JSON. `set` will behave like a partial update at the CLI layer: it will fetch the existing reminder, apply only the supplied field overrides, validate the full effective model locally, then send the resulting full replacement to the gateway’s existing `PUT /v1/reminders/{reminder_id}` contract.

Rationale:

- single-reminder commands are easier to teach, document, and combine with ranking convenience flags,
- the underlying gateway API already supports full replacement, so CLI-side patch semantics can be added without changing the gateway model,
- operator workflows usually mutate one reminder at a time.

Alternatives considered:

- Expose raw batch JSON directly on `create`: rejected for v1 because it makes normal usage harder and complicates prepend/append ranking semantics.
- Require full reminder restatement on every `set`: rejected because it is noisy and error-prone for simple pause, rerank, or retime edits.

### 5. Preserve direct gateway semantics and reuse gateway models end to end

The CLI and pair proxy will remain thin adapters over the current reminder models:

- `GatewayReminderCreateBatchV1`
- `GatewayReminderPutV1`
- `GatewayReminderV1`
- `GatewayReminderListV1`
- `GatewayReminderDeleteResultV1`

Direct gateway validation, including backend-specific `422` rejection for unsupported `send_keys` reminder delivery, will pass through unchanged.

Rationale:

- reminder behavior already exists and is tested at the gateway layer,
- changing the model would expand scope from “operator interface” into “gateway semantics”.

### 6. Add reminder-specific renderers for plain and fancy output

`--print-json` will continue to emit the underlying structured payloads. Plain and fancy output will gain reminder-aware rendering:

- `list` should emphasize `effective_reminder_id` and summarize each reminder’s ranking, paused state, selection state, delivery state, next due time, and title,
- `get`, `create`, and `set` should show one reminder plus the current effective reminder id,
- `remove` can stay compact, similar to other success payloads.

Rationale:

- the current gateway renderers only cover status and prompt result,
- reminder inspection is hard to read as raw key-value lines without surfacing the effective-versus-blocked model.

## Risks / Trade-offs

- [Concurrent reminder edits can race with `--before-all` and `--after-all`] → compute ranking from the latest observed reminder list, document that convenience placement is best-effort rather than globally atomic, and return the concrete ranking in command output.
- [CLI-side patch semantics can overwrite concurrent updates] → fetch the latest reminder immediately before `set`, merge only explicit overrides, and keep the command targeted at operator workflows where occasional last-write-wins behavior is acceptable.
- [Pair-managed reminder projection increases API surface area] → mirror the already-established mail-notifier proxy pattern and reuse the same reminder models end to end rather than introducing special pair-only payloads.
- [Docs and skills currently teach reminders as HTTP-only] → update the CLI reference, gateway reference, and Houmao-owned skill guidance in the same change so operator guidance flips consistently.

## Migration Plan

This change is additive.

1. Add local CLI reminder commands on top of the existing direct gateway client.
2. Add pair-managed reminder proxy routes and client methods so server-backed `agents gateway reminders ...` commands use the same selector contract as other gateway commands.
3. Update plain/fancy renderers for reminder output.
4. Update the packaged `houmao-agent-gateway` skill and repo docs to present the new CLI and pair surfaces as the preferred operator path.
5. Preserve direct `/v1/reminders` support as the low-level contract throughout rollout.

Rollback is straightforward: remove the new CLI and proxy wrappers while leaving the direct gateway reminder API intact.

## Open Questions

None at proposal time. The main product choices for v1 are settled:

- reminder ranking stays numeric,
- `--before-all` and `--after-all` are the only convenience ranking modes,
- pair-managed reminder support is included rather than deferred.
