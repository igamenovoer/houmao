## 1. Registry Model And Storage

- [x] 1.1 Add lifecycle-aware managed-agent registry models with active, stopped, relaunching, and retired states.
- [x] 1.2 Add a v3 registry JSON schema with durable identity/runtime fields and active-only liveness metadata.
- [x] 1.3 Add compatibility loading that maps existing v2 live-agent records to active lifecycle records.
- [x] 1.4 Split registry storage helpers into all-record, active-record, relaunchable-record, and cleanup-record resolution paths.
- [x] 1.5 Update registry publication to reject conflicting active generations while allowing stopped/retired lifecycle records to remain durable.
- [x] 1.6 Add unit tests for v2 compatibility, v3 active records, v3 stopped records, retired records, and lifecycle validation failures.

## 2. Launch And Active Discovery

- [x] 2.1 Update local `agents launch` publication to write active lifecycle-aware registry records.
- [x] 2.2 Update `agents list` default behavior to show active records only.
- [x] 2.3 Add lifecycle-inclusive list filtering for stopped and retired records.
- [x] 2.4 Update active command target resolution for prompt, interrupt, state, stop, and gateway operations to require active records.
- [x] 2.5 Add explicit stopped-record errors for live-only commands with guidance to relaunch or cleanup.
- [x] 2.6 Update selector ambiguity messages to include lifecycle state and registry/runtime locators.
- [x] 2.7 Add integration/unit tests for active discovery, stopped-record rejection, active-only list output, and lifecycle-inclusive list output.

## 3. Stop Lifecycle Transition

- [x] 3.1 Update local tmux-backed `agents stop` to capture durable relaunch and cleanup locators before terminating live resources.
- [x] 3.2 Change successful local relaunchable stops to transition registry records to `stopped` instead of deleting them.
- [x] 3.3 Clear active liveness and live gateway endpoint metadata on stopped registry records.
- [x] 3.4 Preserve last-known tmux session name, manifest path, session root, agent-definition directory, identity, mailbox identity metadata, and relaunch policy on stopped records.
- [x] 3.5 Keep non-local or non-relaunchable stop behavior explicit when lifecycle preservation is unavailable.
- [x] 3.6 Add tests proving stop preserves stopped lifecycle records and no longer leaves stopped agents as active prompt/gateway targets.

## 4. Stopped Relaunch Revival

- [x] 4.1 Add relaunch target resolution that accepts active records and stopped relaunchable records.
- [x] 4.2 Add a runtime stopped-session revival path that recreates tmux authority without rebuilding the managed runtime home.
- [x] 4.3 Update revived manifests with the new live tmux session name, relaunch authority, and registry generation state.
- [x] 4.4 Reuse existing provider-start relaunch plan rebuild logic during stopped-session revival.
- [x] 4.5 Forward explicit and stored relaunch chat-session selectors through stopped-session revival.
- [x] 4.6 Publish an active lifecycle registry record after successful stopped-session revival.
- [x] 4.7 Retain stopped-manifest scan as a migration fallback for pre-change stopped sessions and republish recovered sessions as lifecycle records.
- [x] 4.8 Add tests for local interactive stopped relaunch, headless stopped relaunch, `tool_last_or_new` continuation forwarding, non-relaunchable failure, and migration fallback.

## 5. Cleanup And Retirement

- [x] 5.1 Update `agents cleanup` resolution to prefer stopped lifecycle registry records over runtime-root scans.
- [x] 5.2 Add default stopped-record retirement after successful session cleanup.
- [x] 5.3 Add explicit purge behavior for operators who want cleanup to delete the registry record.
- [x] 5.4 Ensure dry-run cleanup reports planned registry lifecycle actions without mutating registry state.
- [x] 5.5 Preserve existing live-session cleanup safeguards so active records are not retired or purged accidentally.
- [x] 5.6 Add tests for cleanup-by-name on stopped records, ambiguity handling, retire behavior, purge behavior, dry-run behavior, and active-record safety.

## 6. Documentation And Skills

- [x] 6.1 Update CLI reference docs for `agents list`, `agents stop`, `agents relaunch`, and `agents cleanup` lifecycle semantics.
- [x] 6.2 Update registry reference docs to describe lifecycle-aware managed-agent records and active-only liveness.
- [x] 6.3 Update system skills that describe managed-agent stop/relaunch/cleanup so they do not treat stopped relaunch as fresh launch.
- [x] 6.4 Add migration notes for existing v2 live records and pre-change stopped runtime manifests.

## 7. Verification

- [x] 7.1 Run focused registry, managed-agent command, runtime, and cleanup unit tests.
- [x] 7.2 Run `pixi run test` after focused suites pass.
- [x] 7.3 Run `pixi run lint` and address any changed-code lint findings.
- [x] 7.4 Run `pixi run typecheck` for strict type coverage of registry model and resolver changes.
- [x] 7.5 Manually smoke-test stop then relaunch with `--chat-session-mode tool_last_or_new` for a local interactive fixture agent when credentials are available.

Notes:

- `pixi run typecheck` still fails only in the pre-existing wiki helper scripts under `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/scripts/`; no current change files are implicated.
