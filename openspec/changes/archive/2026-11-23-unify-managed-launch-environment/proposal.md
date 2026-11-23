# Proposal

## Why

Two Web agents launched against a shared registry discovered stale agents from the account-default registry because their selected Houmao roots never reached tmux or the native processes. Backend-specific environment assembly also makes declared settings and credentials behave differently across launch modes. [Issue #93](https://github.com/igamenovoer/houmao/issues/93)

## What Changes

- Resolve the registry, shared runtime and mailbox roots, project overlay, and declared environment under the execution owner. Apply supported root overrides before project defaults.
- Publish the same non-secret launch values to the owning tmux session before provider startup and to the native process environment across Headless, Service, TUI, and Web.
- Keep provider credentials and other launch secrets in the existing owner-private paths. Validate attempts to override runtime-owned names and credential bindings through publishable settings.
- **BREAKING** Replace implicit forwarding of arbitrary manager environment variables with an approved owner baseline and declared inputs. Use persistent env records or `--env-set` for custom non-secret values.
- Keep one-off values for the live generation. Rebuild the environment from durable inputs on relaunch, including exact chat resume, and remove expired values from tmux.

## Capabilities

### New Capabilities

### Modified Capabilities

- `brain-launch-runtime` covers resolved launch inputs, private credentials, and environment lifetime across reattach and relaunch.
- `project-aware-local-roots` covers root precedence and publication of the selected project context.
- `tmux-integration-runtime` covers publication before startup, credential exclusion, and session-scoped replacement of expired values.

## Impact

Project and ordinary managed launch entrypoints, launch plans, private runtime launch inputs, tmux-backed provider startup, and CLI and gateway relaunch share this contract. Verification covers DSH and Kimi Web peer discovery, other supported modes, and the Codex TUI proxy behavior from [issue #60](https://github.com/igamenovoer/houmao/issues/60). The launch and lifecycle references document the source and lifetime of each input.
