## Why

Today, per-agent CLI “home directories” under `agents/<agent>/homes/<tool>/` are hand-assembled by duplicated `bootstrap.sh` scripts. This makes it hard to compose an agent from reusable components (tool + skills + config + credentials) and hard to switch credentials/accounts to balance usage.

## What Changes

- Introduce a **brain-first construction model**:
  - Select a target CLI tool (e.g., codex / claude / gemini).
  - Select skills to install.
  - Select a tool-specific config profile.
  - Select a credential profile (local-only).
  - Construct a fresh runtime CLI home directory for that tool at a configurable runtime root (not necessarily under `agents/`).
- Introduce a **brain-agnostic role model**:
  - A role is a tool-independent system prompt plus supporting files referenced by the prompt.
  - Roles are applied after the brain is constructed and the tool is started (or injected at launch).
- Restructure `agents/` into clear repositories of reusable components:
  - `agents/brains/skills/` (skill repo), `agents/brains/cli-configs/` (tool config repo), `agents/brains/api-creds/` (local-only creds), and tool-specific “adapter” definitions.
  - `agents/roles/` for role definitions.
  - Optional “blueprints” that bind a brain recipe and a role into a named agent definition.
- A generated runtime area (at a configurable runtime root) for constructed home directories and resolved manifests.
- Deprecate and eventually remove per-agent `bootstrap.sh` as the mechanism for constructing tool homes.

## Capabilities

### New Capabilities

- `component-agent-construction`: Define the on-disk layout and build semantics for constructing an agent “brain” (tool home dir) from reusable components, then applying a brain-agnostic role (system prompt + referenced files).

### Modified Capabilities

- (none)

## Impact

- `agents/` directory structure and documentation.
- Scripts and workflows that currently assume `agents/<agent>/homes/<tool>/` exist and are maintained by `bootstrap.sh`.
- Secret hygiene: introduce an explicit local-only credential store under `agents/brains/api-creds/` (gitignored) and ensure runtime homes never require committing credentials.
