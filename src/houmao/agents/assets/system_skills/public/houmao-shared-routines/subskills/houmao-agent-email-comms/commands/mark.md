# Mark Message Flags

## Workflow

1. **Preserve actor frame, explicit `--channel` (`offline|online`), and `--expected-binding-id`** from `resolve-live` or current round context.
2. **Confirm target `--message-ref` values** and at least one explicit state flag (`--read/--unread`, `--answered/--unanswered`, or `--archived/--unarchived`).
3. **Run the scoped `mail mark` command** (or `POST /v1/mail/{channel}/mark` with `schema_version: 3` and `expected_binding_id`):

   ```bash
   houmao-mgr agents self mail mark --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" \
     --message-ref "$MESSAGE_REF" [--read | --unread] [--answered | --unanswered] [--archived | --unarchived]
   ```

   Use `agents single --agent-id <id> mail mark ...` when operating on an explicit target with authorized admin signer context.
4. **Report the updated flag state** and stop on any binding conflict or authorization refusal.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/endpoint-contract.md](../references/endpoint-contract.md) and the user request, then execute the plan.

## Guardrails

- DO NOT mark a message `--archived` before its required task and any required reply have succeeded.
- DO NOT omit `--channel` or `--expected-binding-id`, or treat `--read`/`--answered` alone as archive completion.
