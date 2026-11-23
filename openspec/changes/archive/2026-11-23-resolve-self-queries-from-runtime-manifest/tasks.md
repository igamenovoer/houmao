# Tasks

## 1. Publish Query Inputs With the Runtime

- [x] 1.1 Project the existing identity response from typed manifest fields and the verified manifest path. Test identity field parity for headless, service, TUI, and Web manifests.
- [x] 1.2 Publish any missing effective query metadata and runtime locators during launch, join, and relaunch. Test that definition edits affect only later launch generations, and that public query output contains no raw credentials or provider environment values.

## 2. Verify Self Authority and Return Identity

- [x] 2.1 Resolve self to a confined manifest and verify its agent ID, owner binding, and generation against the current live record. Test stale, malformed, foreign, absent, and mismatched authority, including a valid session with no memory binding and a supported headless locator without tmux.
- [x] 2.2 Supply exact owning tmux socket and session context to Kimi Web and DSH Web tool processes. Test with `TMUX` and `TMUX_PANE` empty and a second session on an isolated test server. Verify the lookup selects the correct owner without a fixture-only tmux shim.
- [x] 2.3 Route `agents self identity` through manifest verification and projection. Test plain and JSON output with an unavailable definition directory and detached gateway, and assert that lookup does not construct a controller or write runtime state. Update the self CLI help and reference.

## 3. Remove Definition Access From Running-Session Paths

- [x] 3.1 Reconstruct live runtime adapters from the committed launch plan, role inputs, and runtime-owned artifacts. Test that a running session can be reopened for control after its definition directory becomes unavailable and that explicit relaunch still resolves its launch inputs.
- [x] 3.2 Resolve self `state`, `home`, `refresh --check`, turn evidence, and memory queries from the verified manifest. Verify fresh observations and unavailable results, and preserve the DSH workspace-restricted read-only checks. Update the runtime file reference to describe manifest-owned query facts and live evidence.
- [x] 3.3 Route current-session gateway operations from the verified manifest through existing gateway authority. Exercise status and a supported live control with the definition directory unavailable, and cover the gateway adapter and Web observation paths that currently resume a controller with that directory.
- [x] 3.4 Route self mail through the manifest-backed gateway or eligible local mailbox authority. Test status, list, read, reply, archive, detached status, rejected gateway authorization, and stale expected binding. Verify query paths neither attach a gateway nor write tmux or registry state. Update the mailbox runtime reference.

## 4. Verify Integrated Runtime Behavior

- [x] 4.1 Run a bounded notifier round on fresh Kimi Web and DSH Web fixtures with the default skill pack, an unavailable definition directory, and no manual tmux environment repair. Verify identity, status, list, read, reply, and archive through the maintained commands, with one reply and no duplicate wake.
- [x] 4.2 Run the focused resolver, runtime, gateway, and mailbox tests, then `pixi run lint`, `pixi run typecheck`, and `pixi run test`. Confirm `openspec validate resolve-self-queries-from-runtime-manifest --strict` passes.
