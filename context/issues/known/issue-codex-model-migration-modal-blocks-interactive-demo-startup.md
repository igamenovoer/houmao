# Issue: Codex Model Migration Modal Blocks Interactive Demo Startup

## Summary

On 2026-03-11, starting the interactive CAO demo with the Codex API-key recipe (`codex/gpu-kernel-coder-yunwu-openai`) launched a live Codex TUI session, but the session did not reach the normal ready-for-input prompt. Instead, Codex stopped on a first-run model migration modal that asked the operator to choose between the old configured model and a newer recommended model.

This is currently a known issue for the interactive demo because the demo treats the session as successfully started once the CAO-backed terminal exists, while the actual tool is still blocked on an operator-choice screen inside the TUI.

## What Happened

I launched the demo with:

```bash
scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh -y start \
  --brain-recipe codex/gpu-kernel-coder-yunwu-openai \
  --agent-name chris
```

The demo reported a successful startup and persisted active state:

- `tool: codex`
- `variant_id: codex-gpu-kernel-coder-yunwu-openai`
- `agent_identity: AGENTSYS-chris`
- `terminal_id: b4c50888`

However, when I inspected the session, the live CAO terminal fetch failed and the raw terminal log showed that Codex was waiting at a migration chooser, not the normal working prompt.

## Session State Versus Tool State

The demo currently exposes two layers of state:

- session layer: `active`
- tool layer: `unknown`

This specific run landed in that split state:

- `state.json` says the session is active
- `inspect` reported `tool_state: unknown`
- the raw TUI content showed the tool was actually blocked awaiting operator input

So semantically the tool was in an operator-blocked startup state, but the current inspect contract could only report `unknown` because live CAO output retrieval failed at inspect time.

## Raw TUI Evidence

The terminal log for this run was:

- `tmp/demo/cao-interactive-full-pipeline-demo/20260311-051220-285140Z/.aws/cli-agent-orchestrator/logs/terminal/b4c50888.log`

The visible screen content in that log was effectively:

```text
Codex just got an upgrade. Introducing gpt-5.3-codex.

Choose how you'd like Codex to proceed.

1. Try new model
2. Use existing model
```

That confirms the session was blocked on a model migration prompt inside Codex.

## Local Config Evidence

There was no repo-local workspace config at `<workspace>/.codex/config*` for this run.

The launched Codex session instead used its generated `CODEX_HOME` config at:

- `tmp/demo/cao-interactive-full-pipeline-demo/20260311-051220-285140Z/runtime/homes/codex/codex-brain-20260311-051223Z-6894eb/config.toml`

Relevant contents:

```toml
model = "gpt-5"
model_provider = "yunwu-openai"
model_reasoning_effort = "high"
personality = "friendly"

[notice]
hide_full_access_warning = true
```

That local evidence strongly suggests the modal was triggered because the generated Codex home still defaulted to `model = "gpt-5"` and did not carry any stored acknowledgement for the `gpt-5` to `gpt-5.3-codex` migration.

## Upstream Codex Evidence

I checked upstream Codex sources and the installed local binary.

The prompt itself is implemented by Codex's model migration TUI screen:

- `codex-rs/tui/src/model_migration.rs`
- <https://raw.githubusercontent.com/openai/codex/main/codex-rs/tui/src/model_migration.rs>

That source shows the exact prompt flow for:

- `Try new model`
- `Use existing model`

Codex config types also define a generic migration acknowledgement map under `notice.model_migrations`:

- `codex-rs/core/src/config/types.rs`
- <https://raw.githubusercontent.com/openai/codex/main/codex-rs/core/src/config/types.rs>

Relevant upstream schema:

```toml
[notice.model_migrations]
old-model = "new-model"
```

The upstream `Notice` type describes this as:

- acknowledged model migrations stored as old-to-new model slug mappings

I also inspected the local Codex `0.114.0` binary and found matching embedded symbols for:

- `tui/src/model_migration.rs`
- `notice.model_migrations`
- `Choose how you'd like Codex to proceed.`
- `Try new model`
- `Use existing model`
- `gpt-5.3-codex`

## Impact on This Repo

- The Codex interactive demo can report startup success before the tool is actually usable.
- A fresh Codex home may block on an unhandled upgrade modal even when the demo intends hands-off automation.
- Operators may think the session is ready because `state.json` is active and tmux exists, while the real TUI is still waiting for human confirmation.

## Likely Fixes

Two likely fixes emerged from the investigation:

### 1. Prefer the new model directly

Write the generated Codex config with:

```toml
model = "gpt-5.3-codex"
```

This is the cleanest approach if the demo wants to standardize on the new model and avoid the migration prompt entirely.

### 2. Pre-acknowledge the migration in generated Codex config

If the demo intentionally keeps `model = "gpt-5"`, write:

```toml
[notice.model_migrations]
gpt-5 = "gpt-5.3-codex"
```

This should tell Codex that the migration prompt has already been acknowledged for that model pair.

## Suggested Follow-Up

- Decide whether the Codex demo should move to `gpt-5.3-codex` by default.
- If not, teach the generated Codex home config to persist the migration acknowledgement under `notice.model_migrations`.
- Consider whether demo startup readiness should detect and surface provider-level startup blockers such as migration modals, instead of treating any attached terminal as fully ready.
