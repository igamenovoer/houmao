## Why

We verified that Codex itself can run the Yunwu custom-provider flow without any `auth.json` present in `CODEX_HOME`, yet the current brain-builder contract still forces Codex credential profiles to carry a placeholder `files/auth.json`. That extra requirement is misleading for env-backed profiles and keeps the repo coupled to a login-state artifact that the custom-provider path does not actually need.

## What Changes

- Extend credential file projection so tool adapters can declare optional credential-file mappings instead of treating every listed file as mandatory.
- Make that schema explicit as `required: true` by default, with `required: false` for optional file mappings.
- Update the Codex tool adapter and builder path so env-backed Codex profiles can omit `files/auth.json` while still projecting it when a profile provides one.
- Preserve the two valid Codex launch paths: a valid `auth.json` login state or an `OPENAI_API_KEY` present in the runtime environment.
- Refuse to launch Codex when neither a valid `auth.json` nor `OPENAI_API_KEY` is available.
- Treat placeholder `auth.json` files such as `{}` as unusable login state so the runtime still requires `OPENAI_API_KEY` in that case.
- Remove repo docs and fixture guidance that currently tell custom OpenAI-compatible Codex profiles to create an empty `auth.json`.
- Reconcile the earlier Yunwu change docs with the new optional-file contract so the spec tree remains internally consistent.
- Re-verify the Yunwu-backed Codex profile and brain build flow without `auth.json`, while keeping backward compatibility for profiles that still include a real login-state file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `component-agent-construction`: Brain construction and Codex launch preparation should support optional credential files so env-backed Codex profiles do not need a placeholder `auth.json` when authentication is fully provided by config and env vars, while still rejecting launches that lack both a usable login-state file and `OPENAI_API_KEY`.

## Impact

- Affected code: `src/gig_agents/agents/brain_builder.py`, `src/gig_agents/agents/brain_launch_runtime/backends/codex_bootstrap.py`, and the Codex tool-adapter fixture/schema usage under `tests/fixtures/agents/brains/tool-adapters/`.
- Affected tests: brain-builder tests plus any fixture/runtime tests that currently assume missing Codex `auth.json` must fail or that do not yet validate the “auth.json or OPENAI_API_KEY” launch contract.
- Affected fixtures/docs: Codex credential-profile docs, the Yunwu Codex profile guidance, the earlier Yunwu change spec, and any repo examples that currently describe `{}` as a required compatibility file.
- Dependencies: no new external dependency is required; the change refines the existing brain-builder projection contract and Codex fixture behavior.
