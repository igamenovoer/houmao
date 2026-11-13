# Shared Test Fixtures

For contributors creating test agents, [agent-launch/](agent-launch/README.md) defines two generic API cases: `self-hosted` for a compatible endpoint and `cloud-api` for a key plus base URL. The initial cloud descriptor references DeepSeek. Every API run requires an explicit model. No self-hosted model, account, or context window is assumed.

Use [the fixture helper](../../scripts/agents/test-fixtures/README.md) to prepare isolated Claude, Codex, or Kimi clients. Tracked files contain descriptors, prompts, adapters, setups, sanitized captures, and synthetic data. Native auth JSON and credential-bearing run state belong in private external XDG directories.

`plain-agent-def/` is the secret-free seed for direct native construction. `agent-usage-records/` retains sanitized historical provider evidence, including its actual model/version facts. A historical capture is not a default for future live runs.

The former repository-local auth tree is retired and ignored defensively. Existing operator files remain untouched. Explicitly discover and import selected vendor files with the helper; never copy a complete personal home into this checkout.
