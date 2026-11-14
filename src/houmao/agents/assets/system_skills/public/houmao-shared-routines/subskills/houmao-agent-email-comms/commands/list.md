# List Mail Through The Gateway

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `POST /v1/mail/{channel}/list` to inspect the current mailbox state through the live shared gateway facade.

Listing returns metadata only and does not mark read. Start with 50 results; the hard maximum is 200 and the provider may return fewer. Never add the removed `include_body` field or `--include-body` flag. Use peek/read for selected content.

Typical unread page:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/list" \
  -H 'content-type: application/json' \
  --data '{"schema_version":3,"expected_binding_id":"<selected binding_id>","box":"inbox","read_state":"unread","answered_state":"any","archived":false,"limit":50}'
```

When no live gateway facade is available, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail list --channel <channel> --expected-binding-id <binding_id> --box inbox --limit 50
```

Read `messages` as the returned metadata page. `message_count`, `open_count`, and `unread_count` apply only to that page; an exact `total_count` is optional. `has_more=true` and `next_cursor` mean more matching work exists. `complete=true` means this page exhausted that query, not that the agent completed the work.

Use the same binding, filters, and finite limit with `cursor: "<next_cursor>"` for an explicitly authorized next page. The manager equivalent adds `--cursor <next_cursor>`. Cursors remain opaque. A changed filter/account or stale query state interrupts this page chain; do not combine it with a fresh query or switch bindings automatically.

Set a page/message budget before continuing. Without an explicit paging budget, inspect one page and leave additional work for a later round. Select relevant messages from metadata, then peek/read those messages only.
