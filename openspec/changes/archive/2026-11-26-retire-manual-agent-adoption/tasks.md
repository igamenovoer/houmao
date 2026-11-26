# Tasks

## 1. Retired Manifest Authority

- [x] 1.1 Recognize the saved `joined_tmux` origin before reconstructing managed authority. Use a distinct retired diagnostic with owning-release and fresh-launch guidance. Verify rejection of both adopted modes and a partially saved envelope that retains either origin marker.
- [x] 1.2 Keep the native v6 reader, writer, and packaged schema aligned. Test manifests with explicit null and omitted adoption fields, then verify valid native resume, pane binding, and manifest round-trip.

## 2. Discovery, Control, and Cleanup

- [x] 2.1 Carry the retired result through manager ID, name, and current-session resolution, including stopped-runtime and degraded-terminal fallbacks. Test that a selected retired record receives the retirement diagnostic without substituting another local, external, or pair target.
- [x] 2.2 Apply the same cutoff to active manager listing, passive discovery and known-address routing, managed-self proof, gateway bootstrap, and notifier enablement. Test a fresh retired record with cached attach and gateway metadata and verify that it confers no live endpoint or operation authority. Exercise a supported managed launch and independent known-address and mailbox delivery paths as positive cases.
- [x] 2.3 Preserve retired envelopes and referenced artifacts in selected and bulk cleanup. Test ID, manifest, and session-root selection, active/degraded and missing-registry fixtures, purge, and bulk dry-run and apply. Assert zero native or tmux teardown, deletion, or registry edits for retired targets and existing cleanup behavior for supported owned artifacts.

## 3. Remove Adoption Entry Points and Runtime Paths

- [x] 3.1 Remove `agents self join` for TUI and headless use, its placeholder materializer, and join-only CLI arguments and helpers. Update CLI help and shape tests to verify absence at root, single, and self scopes. Exercise managed launch and verified self identity as the lifecycle path.
- [x] 3.2 Remove adopted launch reconstruction, pane selection, and joined-only lifecycle, observation, refresh, and environment interpretation now fenced by the reader. Keep native relaunch, terminal handoff, and headless chat continuation covered. Verify native socket and pane authority, gateway attachment, and same-session operator handoff on isolated fixtures.
- [x] 3.3 Remove the packaged `agent-instance join` route, adoption actor handoff, and managed-join installation lane from the manifest, schema, and installer. Test packaged skill validation, retained actor gates and managed launch skill defaults. Update the developer behavior-test references for the removed adoption fixture and retain actor-spoof coverage.
- [x] 3.4 Update README, Quickstart, CLI and runtime references, operational docs, and packaged skill examples to direct local lifecycle management through managed launch. Document how to identify saved joined records, wind down their gateways through the owning release, and preserve manual processes and files when desired. Review maintained help and examples against the supported launch, external registration, and offline mailbox join commands.

## 4. Integrated Verification

- [x] 4.1 Run the focused manager CLI, runtime authority and reattach, cleanup, passive/gateway discovery, and system-skill suites. Exercise one managed TUI and one managed headless lifecycle across current discovery and stop. Clear `TMUX` and `TMUX_PANE` and use a unique tmux server when a check starts tmux.
- [x] 4.2 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and strict OpenSpec validation. Review package and help output for the two supported operator entrypoints and the removed adoption route.

## Workflow Follow-up

- At spec sync or archive, retire the empty `houmao-mgr-agents-join` capability and update the admin-entrypoint spec purpose to describe the managed-launch workflow. The deltas carry requirement changes, and purpose text is maintained in the main specs.
- Land this cutoff before the shared TUI observation tasks in [refactor-managed-runtime-boundaries](../refactor-managed-runtime-boundaries/tasks.md).
