## Why

Today, CAO-backed sessions already persist the CAO API base URL in the session manifest, but resumed operations (`send-prompt`, `stop-session`) still require (and honor) an external `--cao-base-url` value. This is redundant and can silently target the wrong CAO host, making “resume by manifest” unreliable.

## What Changes

- **BREAKING**: Remove `--cao-base-url` from `send-prompt` and `stop-session`; a CAO-backed session is addressed only by its session manifest.
- **BREAKING**: Remove any resume-time CAO base URL override in the Python API; for CAO-backed sessions the manifest’s `cao.api_base_url` is the only endpoint used.
- Make “session manifest = complete address” explicit for CAO sessions: `{cao.api_base_url, cao.session_name, cao.terminal_id}` come from the manifest and are used consistently for prompt sending and shutdown.
- Fail fast on unusable/inconsistent CAO manifests: require non-blank `cao.api_base_url` and `cao.terminal_id`, and require `cao.api_base_url == backend_state.api_base_url`.
- Guarantee error semantics: local manifest validation failures raise `SessionManifestError`; CAO network/HTTP failures remain `BackendExecutionError`.
- Update docs and demo scripts to follow the new pattern.
- Add unit coverage to prevent regressions (resume uses manifest URL; CLI surface no longer exposes an override).
- (Deferred) Consider removing `--cao-profile-store` from `send-prompt`/`stop-session` in a follow-up to keep “manifest pointer is enough” coherent.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `brain-launch-runtime`: CAO-backed resumed operations are addressed solely by session manifest; CLI/API no longer accept CAO base URL overrides.

## Impact

- `src/gig_agents/agents/brain_launch_runtime/`: CLI and resume orchestration signature changes for CAO flows.
- `docs/reference/brain_launch_runtime.md`: update examples to remove `--cao-base-url` from resumed operations.
- `scripts/demo/*`: update CAO demo packs and any helper scripts that currently pass `--cao-base-url` for resumed operations.
- Downstream scripts and docs that call `send-prompt`/`stop-session` with `--cao-base-url` must be updated.
