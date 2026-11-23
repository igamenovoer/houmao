# Tasks

## 1. Managed Workspace Lifecycle

- [x] 1.1 Register or reuse the canonical launch workdir through DSH's native Workspace registry. Attach the exact Agent session during native setup. Verify through the native Workspace feed that a fresh launch reports one Workspace containing the bound ID before the first prompt.
- [x] 1.2 Apply the same setup to exact relaunch, new-session relaunch, and in-place reset. Verify repeated exact setup preserves the Workspace and session IDs, and each explicit replacement adds one session while retaining prior and unrelated history.
- [x] 1.3 Exercise invalid workdir, attachment failure, and retry of the same candidate. Verify an error leaves the replacement unadvertised, preserves existing records, and omits credentials from the lifecycle diagnostic.
- [x] 1.4 Document Workspace setup and exact relaunch in the DSH Web reference. Check that the documented behavior matches the lifecycle tests and the existing relaunch selectors.

## 2. Gateway Entry and Browser Startup

- [x] 2.1 Qualify a managed startup path that can select the verified existing session before stock DSH restoration can issue a create request. Check the current DSH Web floor and a newer supported build with both catalog arrival orders and delayed client activation. Record the version and observed startup calls. Record a DSH startup hook dependency if the supported extension points cannot provide this ordering.
- [x] 2.2 Carry the verified Workspace and session target through the native cookie handoff and consume it once. Verify bare entry, keyed sign-in, and ticket redemption reach the same bound target. Check that stale or wrong membership is refused and that the final URL and public outputs omit native credentials.
- [x] 2.3 Extend the maintained DSH Web browser fixture to assert the selected session before any prompt, after reload, after exact relaunch with history, after new-session relaunch, and when entering with another saved selection. Observe the selected row and native inventory without creating a Workspace or clicking the target as test setup.
- [x] 2.4 Update the DSH Web and gateway operator references for exact-session landing and subsequent native navigation. Verify the instructions cover the dashboard link and the owner-local entry routes.

## 3. Integrated Verification

- [x] 3.1 Navigate to an unrelated native conversation and trigger a controlled gateway mail notification. Reopen the managed session through the gateway and verify the notifier turn appears in the manifest-bound conversation. Compare the unrelated conversation and both Workspace memberships before and after delivery.
- [x] 3.2 Run the focused DSH Web lifecycle, browser, gateway entry, headless, and ACP regressions through Pixi. Record the commands, build, explicit fixture case and model, browser version, outcomes, and any unavailable prerequisites under the change's `logs/` directory. Use isolated tmux and clean browser contexts for the native tests.
