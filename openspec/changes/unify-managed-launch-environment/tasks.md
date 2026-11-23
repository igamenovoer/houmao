# Tasks

## 1. Owner Root Resolution

- [x] 1.1 Resolve runtime and mailbox placement in `launch_managed_agent_locally` from the selected owner and overlay. Cover explicit `--mail-root`, shared runtime and mailbox overrides, and overlay defaults with launch command tests.
- [x] 1.2 Pass the selected overlay and shared-root selectors into runtime launch authority. Test that the recorded registry comes from the execution binding, the overlay is independent of `--workdir`, and delegated and passive-server launches retain their configured owner roots.
- [x] 1.3 Update the project-aware operations reference with the launch precedence and examples for shared and overlay-local placement. Check the examples against the supported launch options and the root resolution tests.

## 2. Launch Environment and Credential Inputs

- [x] 2.1 Resolve approved owner baseline values, persistent records, one-off assignments, and trusted runtime bindings into the launch plan. Test literal and bare-name `--env-set`, one-off precedence over a persistent value, and exclusion of undeclared manager values.
- [x] 2.2 Keep credential provenance through launch planning and use the existing owner-private launch record. Test dynamic credential binding names, runtime-owned key collisions, private record ownership, and redacted public metadata and diagnostics using synthetic secrets.
- [x] 2.3 Update the launch plan reference with the visibility of declared records and how owners supply credentials. Verify that the documented inputs match the validation and private record behavior.

## 3. Tmux and Native Startup

- [x] 3.1 Add shared session-scoped publication with managed-key removal, credential masking, and startup failure handling. Verify in isolated tmux that a fresh server receives a scrubbed environment, global keys cannot reappear in managed panes, unrelated session keys are preserved, and publication errors prevent startup with value-free diagnostics.
- [x] 3.2 Route Headless and local TUI startup through the shared publisher and explicit provider environment. Verify a worker and primary pane receive the values at startup, including Codex TUI's non-secret profile proxy env from issue #60 and provider credentials through private inputs.
- [x] 3.3 Use the same preparation and publisher for DSH Web, Kimi Web, and the Service supervisor. Test publication before native startup and verify that tool home preparation and private supervisor environment still provide the required launch values.
- [x] 3.4 Use the publisher and private terminal bootstrap for the retained CAO startup. Verify in the CAO backend tests that approved model settings reach the terminal and credentials reach the provider through the bootstrap, with synthetic values absent from tmux and the recorded pane command.

## 4. Live Reattach and Relaunch

- [x] 4.1 Restore the current generation's environment and published key set from owner-private runtime inputs. Verify that reattachment and a later Headless turn keep a one-off value even when the new controller has a different environment.
- [x] 4.2 Rebuild and republish the environment on managed relaunch from durable inputs and saved root context. Test exact native chat continuation, restoration of a shadowed persistent value, expiry of a transient-only key in both tmux and the provider, and a relaunch from a different controller directory and root environment.
- [x] 4.3 Update the lifecycle reference with live reattach, exact-chat relaunch, and the replacement of implicit ambient env forwarding. Check the documented value lifetimes against the relaunch tests.

## 5. End-to-End Verification

- [x] 5.1 Launch DSH Web and Kimi Web with the maintained fixture, using an explicit self-hosted case and compatible model, separate project overlays, shared non-default roots, and an isolated tmux server. Verify the selected roots and declared flags in tmux and via an actual shell command from each agent. Run `houmao-mgr agents global list` from both agents and verify both peers come from the selected registry.
- [x] 5.2 Reattach and relaunch the Web agents, including an exact native chat where supported. Verify durable settings and peer discovery after relaunch, current-generation settings on reattach, and credential exclusion from tmux and public artifacts. Run the focused runtime and CLI tests across all four modes with Pixi. Report the tested native versions and any unavailable live lanes separately from passing checks.
