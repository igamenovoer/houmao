## Why

We now have a canonical `agents/brains/` + `agents/roles/` layout and a brain builder, but we still lack a repo-owned Python runtime that can reliably *launch and drive* interactive CLI tool sessions using a constructed brain and an initial role prompt. We also want CAO integration without making CAO a hard dependency, so the runtime remains usable if CAO is swapped out.

## What Changes

- Add a Python library module that:
  - loads brain recipes / blueprints and constructs a fresh brain home (or reuses one explicitly)
  - launches CLI tools with the correct brain config (home selector + allowlisted credential env vars)
  - supports interactive sessions (non-CAO) using backend-specific patterns:
    - long-lived subprocess protocols when available (e.g., `codex app-server`)
    - resumable headless CLI calls for Claude/Gemini (`json`/`stream-json` + persisted `session_id` with `--resume`)
  - supports streaming output and early interruption/termination of in-flight backend work (when the backend allows it)
  - applies a role package as the initial tool instructions (tool-specific injection: flags/config fields when supported; fallback to first user message)
  - optionally runs under CAO via its REST API boundary, while keeping CAO-coupled logic isolated
  - generates CAO agent profiles at runtime from repo roles (no committed/static CAO profiles)
  - persists a backend-specific session manifest JSON (including reconnect fields such as `session_id`, process identity, or CAO terminal IDs) for audit/resume/stop
  - schema-validates all runtime-generated manifest/config artifacts before write and on read/load
  - stores JSON Schema files in the runtime package under `src/gig_agents/.../schemas/`
- Provide a small CLI surface for common operations (build brain, start session, send prompts, stop session).

## Capabilities

### New Capabilities

- `brain-launch-runtime`: Construct brains and launch/drive interactive CLI sessions with role-first initialization, with optional CAO-backed terminals and runtime-generated CAO profiles.

### Modified Capabilities

- (none)

## Impact

- New Python modules under `src/gig_agents/` for brain+role composition and interactive session control.
- Optional integration with a locally running CAO server (`http://localhost:9889`) via REST; no direct imports from CAO runtime are required.
- New generated runtime artifacts under `tmp/` (homes, manifests, session metadata, transcripts/snapshots depending on backend).
