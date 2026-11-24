# Open a Live Managed Web Agent

## Workflow

1. **Verify the target**. Require an explicit agent ID or name in its execution owner's context and confirm the attached gateway and live Web mode.
2. **Select caller proof**. Use the valid initialized empty-roster path or a signer authorized for `web.enter`. See [Command Shapes](#command-shapes).
3. **Issue one entry link** through the scoped manager only when the user requests browser entry and can receive the link privately.
4. **Use the private result** in a browser that reaches both the owner-local gateway and native Web app. Report only safe outcome fields.

If the request does not map cleanly to this workflow, use the native planning tool to resolve the owner context, live target evidence, and private browser handoff before executing.

## Command Shapes

Use the manager launcher selected by the parent. The owner-local command accepts an explicit agent ID or name. A valid initialized empty roster permits unsigned issuance.

```bash
houmao-mgr agents single --agent-id "$AGENT_ID" gateway web-entry
```

In keyed mode use the owner-configured `admin_signer_path` or pass an absolute private key path for an enrolled signer with `web.enter`.

```bash
houmao-mgr agents single --agent-name "$AGENT_NAME" gateway web-entry --signer "$SIGNER"
```

The command returns `url` and `expires_at_utc`. The URL is a bearer secret valid for one redemption within 60 seconds. Open it through the exact owner-local address or a private forward that reaches both services. If the gateway, mode, or policy is unavailable, report the blocker. The lifecycle operation handles separately requested gateway attachment.

## Guardrails

- DO NOT use a pair port or an advertised public proxy URL for this owner-local browser handoff.
- DO NOT expose the returned URL in shared logs, mail, prompts, or ordinary result summaries.
- DO NOT choose a private signer merely because a file or an SSH agent is available.
