## Why

Reusable launch profiles already capture birth-time launch context such as identity, workdir, auth, mailbox, prompt posture, and prompt overlays. Operators also need a deterministic way to initialize an agent's `houmao-memo.md` and supporting `pages/` at launch without turning durable memo content into prompt text or asking the model to copy setup notes after it starts.

## What Changes

- Add an optional **memo seed** to the shared launch-profile object family used by easy profiles and explicit recipe-backed launch profiles.
- Support memo seeds from inline text, a Markdown file, or a directory shaped like the managed memo tree with `houmao-memo.md` and `pages/`.
- Store memo seed content as catalog-managed content references rather than inline SQLite payloads or absolute source paths.
- Apply memo seeds during profile-backed launch after managed-agent identity and memo paths are resolved, and before the runtime session is published or started.
- Add an explicit memo seed policy so the default initialization path does not overwrite existing agent memo state unexpectedly.
- Surface memo seed create, patch, inspect, replacement, and clear behavior through both `project agents launch-profiles ...` and `project easy profile ...`.
- Update launch-profile documentation and CLI reference material to describe memo seeds using memo terminology only.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-launch-profiles`: Add memo seeds as durable birth-time launch-profile defaults, including storage, inspection, patch, replacement, and lane-boundary behavior.
- `brain-launch-runtime`: Apply resolved memo seeds at managed launch time before session publication/start and record secret-free profile provenance.
- `houmao-mgr-agents-launch`: Ensure explicit launch-profile-backed launches apply stored memo seeds while preserving direct override precedence for other launch inputs.
- `houmao-mgr-project-agents-launch-profiles`: Add explicit launch-profile CLI options for memo seed source, policy, inspection, and clearing.
- `houmao-mgr-project-easy-cli`: Add easy-profile CLI options for memo seed source, policy, inspection, and clearing.
- `agent-memory-freeform-memo`: Clarify that an explicit profile-owned memo seed is a caller-authorized memo/page write at launch time, while ordinary memory creation and page mutations still do not mutate the memo implicitly.
- `agent-memory-pages`: Reuse the managed `pages/` containment contract for directory memo seeds.
- `docs-launch-profiles-guide`: Document memo seeds in the launch-profile conceptual guide without using the old “memory seed” terminology.

## Impact

- Catalog schema and projection rendering for launch profiles.
- Launch-profile resolution payloads and secret-free provenance payloads.
- `houmao-mgr project agents launch-profiles add|set|get`.
- `houmao-mgr project easy profile create|set|get` and profile-backed easy instance launch.
- Managed launch runtime path that resolves `houmao-memo.md` and `pages/`.
- Tests for catalog persistence/projection, CLI shape, launch-time seed application, containment validation, and docs wording.
- Documentation for launch profiles, easy profiles, CLI reference, and managed memo behavior.
