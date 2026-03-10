## Why

The repo already has a brain-first workflow for Codex agents, but it does not yet provide an implementation-ready profile for running Codex against a custom OpenAI-compatible endpoint such as Yunwu. Right now the checked-in Codex fixture config stays on the default first-party setup, while the local-only credential profile and recipe shape needed for a Yunwu-backed agent are missing.

## What Changes

- Add a repo-owned Codex brain profile for an OpenAI-compatible provider named `yunwu-openai`, with secret-free `config.toml` settings that bypass built-in OpenAI login and use `wire_api = "responses"`.
- Add a local-only credential profile convention for `tests/fixtures/agents/brains/api-creds/codex/yunwu-openai/` that carries the plain-text env values needed by the existing Codex adapter (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) plus any required local bootstrap files.
- Add or update a Codex brain recipe so developers can select the Yunwu-backed Codex profile without embedding secrets into recipes or blueprints.
- Update docs and fixture guidance so the supported setup for custom OpenAI-compatible Codex agents is clear, including any temporary compatibility constraints around `auth.json`.
- Define end-to-end acceptance around a live Codex smoke test: launch Codex with the Yunwu-backed profile, send the prompt `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`, and confirm the agent returns exactly `YUNWU_CODEX_SMOKE_OK`.

## Capabilities

### New Capabilities

- `codex-openai-compatible-brain-profile`: Defines the repo-owned Codex config, credential-profile shape, and recipe/documentation expectations for launching Codex agents against an env-backed OpenAI-compatible endpoint such as Yunwu.

### Modified Capabilities

None.

## Impact

- Affected fixtures: `tests/fixtures/agents/brains/cli-configs/codex/`, `tests/fixtures/agents/brains/api-creds/codex/`, and `tests/fixtures/agents/brains/brain-recipes/codex/`.
- Affected docs: agent brain fixture docs and any Codex setup guidance that currently assumes first-party login or stale custom-provider wiring.
- Affected runtime expectations: Codex brain homes built from the new profile must continue to rely on local-only credential env files, must remain secret-free in committed config, recipes, and manifests, and must be verifiable through a live exact-match smoke prompt against the configured provider.
- Dependencies: no new external dependency is required; the change builds on the existing Codex adapter, credential-env injection, and runtime-home bootstrap flow.
