# Missing Inputs

Use this page whenever the selected subskill still lacks required command inputs.

## Recovery Order

1. Recover values from the current user prompt.
2. Recover values from recent chat context only when the user stated them explicitly.
3. Inspect existing Houmao definitions only when the subskill says inspection is needed to disambiguate a stored resource.
4. Ask the user for exactly the missing fields that remain.

## Question Shape

- Use a short bullet list when one or two values are missing.
- Use a compact Markdown table when the lane or several required fields are unclear.
- Name the command you intend to run.
- Keep the question scoped to the selected lane.

## Guardrails

- Do not infer names, tools, credential values, workdirs, profile lanes, or update fields from partial matches.
- Do not ask for optional fields unless the user requested behavior that needs them.
- Do not continue from partially inferred auth values, mailbox identities, or runtime posture.
