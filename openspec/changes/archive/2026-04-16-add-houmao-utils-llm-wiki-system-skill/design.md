## Context

Houmao's packaged system skills are runtime assets under `src/houmao/agents/assets/system_skills/`, declared by `catalog.toml`, and projected into Claude, Codex, Copilot, and Gemini homes by `houmao-mgr system-skills`. The newly tracked `extern/tracked/llm-wiki-skill` submodule provides an all-in-one LLM Wiki skill with scripts, references, subskills, and a bundled local web viewer. The previous change renamed its wiki root schema contract to `README.md`.

The all-in-one skill is useful as a general utility, not as core managed-agent control. It should be installable through Houmao's system-skill catalog but should not appear in managed homes or default external-home installs unless explicitly selected.

## Goals / Non-Goals

**Goals:**
- Package the all-in-one LLM Wiki workflow as `houmao-utils-llm-wiki`.
- Ship the full all-in-one payload, including `viewer/`, scripts, references, and subskills.
- Adapt visible skill text to Houmao naming and installation context.
- Add a `utils` named set for explicit installation.
- Keep all auto-install and CLI-default selections unchanged.
- Keep helper examples using `python3`.

**Non-Goals:**
- Do not add runtime Python APIs or CLI commands for LLM Wiki operations.
- Do not install Node dependencies, build viewer artifacts, or include generated `node_modules/` content in the packaged skill asset.
- Do not preserve upstream attribution text in the packaged Houmao system skill.
- Do not add `utils` to managed launch, managed join, or CLI-default install selections.
- Do not make this skill a prerequisite for existing Houmao agent-management workflows.

## Decisions

- Copy and adapt the submodule's `llm-wiki-all-in-one/` directory into `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.
- Rename only the packaged skill identity and Houmao-facing prose. Preserve the core wiki operations: `compile`, `ingest`, `query`, `lint`, and `audit`.
- Keep bundled scripts and viewer source in the skill asset so installed homes have the same all-in-one capabilities as the source skill.
- Add `[sets.utils]` with only `houmao-utils-llm-wiki`, and leave `auto_install` lists unchanged so users opt into the utility skill with `--skill-set utils` or `--skill houmao-utils-llm-wiki`.
- Update tests and docs from the catalog outward because the catalog is the source of truth for install, status, uninstall, and inventory reporting.

## Risks / Trade-offs

- Larger package artifacts → Ship source-only viewer assets and avoid generated dependencies or build outputs.
- Drift from the tracked submodule source → Treat the submodule as the import source and keep the packaged Houmao copy intentionally adapted.
- Users may expect default install to include every packaged skill → Document that `utils` is explicit-only and show direct install examples.
- The utility skill may be mistaken for an agent-management skill → Place it under a `utils` set and describe it as a knowledge-base utility rather than a Houmao lifecycle/control surface.
