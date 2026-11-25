# Design

## Context

The manager has shared output styles and command-specific renderers. Generic text abbreviates nested records. Some commands also hand full read models or runtime values directly to the renderer. Project receipts at the affected command boundaries so each result carries the evidence available from its operation. [Output Formatting](../../../src/houmao/srv_ctrl/commands/output.py)

## Goals and Scope

Make the outcome and reference usable after one action. Each command uses the same receipt fields across its supported scopes and output modes. Gateway and pair payloads remain the input to the CLI projections, and the existing read commands supply detail.

## Decisions

### Project Mail Receipts from the Pinned Binding

Resolve the channel and binding ID once before dispatch. Share the CLI projection across `send`, `reply`, and `post` on the pair API, local gateway, and manager-direct paths. Take the final envelope from the response, including recipients and subject derived from the parent by the reply route. Copy the opaque reference exactly as returned.

The version-1 receipt carries `schema_version`, `operation`, `status`, `authoritative`, `execution_path`, `channel`, `binding_id`, `transport`, `principal_id`, and `address`. The principal and address identify the mailbox that owns the reference. Verified receipts add `sender_address`, `to`, `cc`, `subject`, `message_ref`, and `created_at_utc`. For an operator post, `sender_address` is the operator and the binding identifies the selected recipient. A reply also records the input `parent_message_ref` separately from the new reference.

Project the receipt without additional mailbox calls. Text displays the full references and address lists as values. JSON represents To and Cc as arrays of address strings. Keep bodies, attachments, message flags, and transport snapshots in the detail response. [Mail Routing](../../../src/houmao/srv_ctrl/commands/managed_agents.py)

### Preserve Mail Evidence and Locality

Use `verified` and `authoritative: true` for an acknowledged write. The acknowledgement refers to the filesystem commit or provider-confirmed submission. Recipient read state is separate evidence.

For TUI-mediated send and reply, project the existing lifecycle status, request ID, submission time when recorded, and read-only verification guidance. A submitted reply carries `parent_message_ref`. Include known envelope fields and leave unavailable fields absent. Keep `authoritative: false` and omit transcript previews. Authoritative manager or gateway access is required for operator post.

Keep existing nonzero errors and the provider's reconciliation identifiers and commit evidence. For example, a provider may have submitted a reply before updating its parent's flags. Each invocation dispatches at most once. [Stalwart Submission](../../../src/houmao/mailbox/stalwart.py) · [Filesystem Delivery](../../../src/houmao/mailbox/managed.py)

### Inspect the Binding that Owns the Message

Use `mail peek` with the receipt's exact reference, channel, and binding. For send and reply, inspect the writing agent's mailbox. For post, inspect the selected recipient's mailbox under the existing read authority.

```bash
houmao-mgr --print-json agents self mail peek --channel "$MAIL_CHANNEL" \
  --expected-binding-id "$BINDING_ID" --message-ref "$MESSAGE_REF"
```

When no verified reference is available, check `mail list --box sent` on the original binding for send or reply. For an uncertain post, inspect the selected recipient's inbox and archive as authorized. If the binding changed or evidence is inconclusive, preserve the unresolved outcome.

### Show Gateway Prompt Handoff Evidence

Render `status`, `action`, `admission_policy`, `sent`, and `detail` from the existing direct response. Include `operation_id`, `outcome`, and `native_prompt_id` when returned. Keep structured errors and the nonzero exit behavior. Report only the handoff and observation evidence the gateway supplies.

Document read-only observation by mode. A managed headless operation with a saved turn ID can use `turn status` and `turn events`. An authorized service client can inspect an exact request through the existing service endpoint. For Web or TUI, use the available surface state or history and preserve uncertainty when it cannot identify the exact submission. [Gateway Contract](../../../docs/reference/gateway/contracts/protocol-and-state.md)

### Acknowledge Memo and Reminder Writes

For `memory memo set|append`, return `success`, `action` (`write_memo` or `append_memo`), and `memo_file`. On the local path, acknowledge the completed file operation using its resolved path. On the pair path, project the existing write response. The caller reads the resulting contents through `memo show`.

For `gateway reminders set`, leave the existing partial-update merge and ranking placement in the pre-write phase. Project `status: updated`, `reminder_id`, `ranking`, `paused`, and `next_due_at_utc` from the successful update. The receipt needs no post-write list request. Use `reminders get` or `list` for prompt content or the effective reminder of the set.

### Serialize the Browser Outcome

Project `status`, `action`, and `detail` from the successful local browser result before handing it to the output layer. The receipt uses action `open_browser` and contains no browser URL, credentials, or bootstrap file path. Retain the existing owner verification and failure handling. [Browser Action](../../../src/houmao/srv_ctrl/commands/managed_agents.py)

## Risks and Trade-offs

- Update scripts that consume mail, memo, or reminder write JSON with the documented fields and detail commands.
- Some backends provide only submission evidence or temporarily omit the record. Teach agents to use read-only inspection and preserve uncertainty when an outcome remains unresolved.

## Migration Plan

Mail consumers read top-level `message_ref` and use `mail peek` for details. Memo consumers read `memo_file` from the write and use `memo show` for `content`. Reminder updates return the top-level reminder ID and saved schedule fields. Consumers use `reminders get` or `list` for the full reminder and set-wide fields.
