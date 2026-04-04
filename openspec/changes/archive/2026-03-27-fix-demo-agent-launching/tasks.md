## 1. Shared Launch Recovery

- [x] 1.1 Inventory the affected demo and tutorial packs by launch pattern and identify the launch-critical caller in each pack that still depends on legacy recipe or blueprint inputs.
- [x] 1.2 Update shared demo launch helpers and compatibility adapters so demo startup can resolve current preset-backed build/start inputs without requiring `brains/brain-recipes/` or `blueprints/` as authoritative launch sources.

## 2. Demo Launch Migrations

- [x] 2.1 Migrate the script- and helper-driven demo packs to current launch inputs for startup only, including mail ping-pong gateway, skill invocation, mailbox roundtrip tutorial, gateway stalwart/cypht interactive, and TUI mail gateway flows.
- [x] 2.2 Migrate the native or local runtime demo packs to current launch inputs for startup only, including passive-server parallel validation, Houmao server agent API, Houmao server interactive full pipeline, CAO interactive, and Houmao server dual shadow watch flows.
- [x] 2.3 Update tracked demo launch-input files and config documents that still block startup because they point at legacy blueprint or recipe-era artifacts.

## 3. Launch-Focused Verification

- [x] 3.1 Add or update launch-focused tests for each repaired launch pattern so they assert successful build/session startup and startup metadata without requiring post-launch behavior.
- [x] 3.2 Run the relevant demo and runtime verification suites, confirm the repaired demos can complete their launch path, and record any explicitly deferred post-launch gaps for follow-up changes.
