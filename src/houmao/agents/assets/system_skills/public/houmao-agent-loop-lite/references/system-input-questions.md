# System Input Questions

## Missing Runtime Inputs

When a Houmao runtime or artifact-location input is missing, ask with separate sections:

```text
Required:
- <missing required value>

Optional:
- <helpful optional value or none for this step>
```

## Rules

- Ask for `<loop-dir>` before creating or changing loop files.
- Do not invent filesystem roots, runtime roots, agent names, credentials, or workdirs.
- Do not impose this shape on ordinary user-task or domain-intent clarification unless the missing value is a Houmao runtime or artifact-location input.
