## Why

The all-in-one LLM Wiki skill currently names the wiki root schema file `CLAUDE.md`, which incorrectly couples an agent-neutral knowledge-base pattern to one agent provider. The skill should present a clean, provider-neutral contract before it is installed or documented as a tracked dependency.

## What Changes

- **BREAKING**: Rename the required wiki root schema and operating-contract file from `CLAUDE.md` to `README.md`.
- Remove all `CLAUDE.md` references from the all-in-one skill instructions, scaffold output, reference guides, workflow notes, and viewer deployment troubleshooting.
- Update the scaffold helper so new wikis create `README.md` only.
- Keep the root schema semantics unchanged: the file still defines scope, naming conventions, current articles, open questions, research gaps, audit posture, and LLM-facing operating notes.
- Do not add compatibility behavior, fallback lookup, or legacy wording for `CLAUDE.md`.

## Capabilities

### New Capabilities
- `llm-wiki-all-in-one-skill`: User-facing contract for the tracked all-in-one LLM Wiki skill, including its required wiki root files, scaffold behavior, and documentation terminology.

### Modified Capabilities

## Impact

- Affects the tracked `extern/tracked/llm-wiki-skill` submodule content on its `all-in-one` branch.
- Affects skill instructions under `llm-wiki-all-in-one/SKILL.md`.
- Affects bundled helper scripts, especially `llm-wiki-all-in-one/scripts/scaffold.py`.
- Affects reference documentation under `llm-wiki-all-in-one/references/` and `llm-wiki-all-in-one/subskills/`.
- Existing wiki roots that only contain `CLAUDE.md` will no longer match the documented contract; migration compatibility is intentionally out of scope.
