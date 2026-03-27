# Review via Copilot

Use this prompt when you want GitHub Copilot CLI to review a specific target such as:

- an OpenSpec change directory under `openspec/changes/...`
- one code file
- one source or docs directory

Use Copilot with:

- model: `claude-opus-4.6`
- reasoning effort: `high`

## Prompt Template

Replace `<TARGET>` with the path you want reviewed.

```text
Review `<TARGET>`.

Use GitHub Copilot CLI with model `claude-opus-4.6` and high reasoning effort.

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

## Copilot CLI Template

This command uses the repository's Copilot helper overlay so the run keeps `reasoning_effort: high` while explicitly selecting `claude-opus-4.6`.

```bash
skill_dir="magic-context/skills/cli-agents/copilot-invoke-once"
tmp_cfg="$(python3 "$skill_dir/scripts/compose_config.py" --preset "$skill_dir/presets/reasoning-high.json")"
trap 'rm -rf "$tmp_cfg"' EXIT

copilot --config-dir "$tmp_cfg" --model claude-opus-4.6 -p "$(cat <<'PROMPT'
Review `<TARGET>`.

Use GitHub Copilot CLI with model `claude-opus-4.6` and high reasoning effort.

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
)" --yolo --no-ask-user --silent --stream on
```

Replace `<TARGET>` in the prompt before running the command.
