# Move Messages Between Boxes

## Workflow

Check the selected channel's current `mail status` before changing placement. When the binding reserves placement for the owner, report the completed items for separately authorized backend filing. Keep ordinary read and answered changes within their supported scope.

1. **Preserve actor frame, explicit `--channel` (`offline|online`), and `--expected-binding-id`** from `resolve-live` or current round context.
2. **Confirm target `--message-ref` values and `--destination-box`** within the same mailbox binding.
3. **Run the scoped `mail move` command** (or `POST /v1/mail/{channel}/move` with `schema_version: 3`, `expected_binding_id`, `message_refs`, and `destination_box`):

   ```bash
   houmao-mgr agents self mail move --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" \
     --message-ref "$MESSAGE_REF" --destination-box "$DESTINATION_BOX"
   ```

   Use `agents single --agent-id <id> mail move ...` when operating on an explicit target with authorized admin signer context.
4. **Report the move result** and stop fail-closed if the provider rejects the box name or reports a binding mismatch.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/endpoint-contract.md](../references/endpoint-contract.md) and the user request, then execute the plan.

## Guardrails

- DO NOT attempt to move messages across `offline` and `online` channels or across different mailbox bindings.
- DO NOT move unfinished or reply-pending inbox work out of `inbox` as a substitute for completing the round.
