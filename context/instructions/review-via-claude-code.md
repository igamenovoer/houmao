# Review via Claude Code

Use this prompt when you want Claude Code CLI to review a specific target such as:

- an OpenSpec change directory under `openspec/changes/...`
- one code file
- one source or docs directory

Use Claude Code with:

- model: `opus 4.6`
- effort: `high`

## Prompt Template

Replace `<TARGET>` with the path you want reviewed.

```text
Review `<TARGET>`.

Use Claude Code with Opus 4.6 and high effort.

Review mode:
- If `<TARGET>` is an OpenSpec change, review proposal, design, specs, and tasks for completeness, internal consistency, implementation readiness, testability, and mismatch with the current repository behavior.
- If `<TARGET>` is a code file or directory, do a code review focused on bugs, behavioral regressions, incorrect assumptions, edge cases, missing validation, missing tests, and maintainability risks.

Output rules:
- Findings first, ordered by severity.
- Use concrete file references when possible.
- Keep summaries brief.
- If there are no findings, say that explicitly.
- Do not modify files.
- Do not spend time praising the code or spec.

For each finding, include:
1. Severity
2. Location
3. Why it is a problem
4. What change or follow-up would resolve it
```

## Claude Code CLI Template

This command uses the repository's documented Claude Code headless flow and requests high effort on the Opus model.

```bash
claude --model opus --effort high -p "$(cat <<'PROMPT'
Review `<TARGET>`.

Use Claude Code with Opus 4.6 and high effort.

Review mode:
- If `<TARGET>` is an OpenSpec change, review proposal, design, specs, and tasks for completeness, internal consistency, implementation readiness, testability, and mismatch with the current repository behavior.
- If `<TARGET>` is a code file or directory, do a code review focused on bugs, behavioral regressions, incorrect assumptions, edge cases, missing validation, missing tests, and maintainability risks.

Output rules:
- Findings first, ordered by severity.
- Use concrete file references when possible.
- Keep summaries brief.
- If there are no findings, say that explicitly.
- Do not modify files.
- Do not spend time praising the code or spec.

For each finding, include:
1. Severity
2. Location
3. Why it is a problem
4. What change or follow-up would resolve it
PROMPT
)" --output-format json
```

If your local Claude wrapper or install expects model pinning through environment variables instead of `--model`, set `ANTHROPIC_MODEL` to your local Opus 4.6 model value and keep `--effort high`.

Replace `<TARGET>` in the prompt before running the command.
