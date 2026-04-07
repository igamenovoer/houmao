## 1. Update launch CLI surfaces

- [x] 1.1 Add `--workdir` to `houmao-mgr agents launch` and forward it as the runtime workdir, defaulting to the invocation cwd when omitted.
- [x] 1.2 Rename `houmao-mgr agents join --working-directory` to `--workdir` and update help/error handling to remove the old flag name from the public surface.
- [x] 1.3 Add `--workdir` to `houmao-mgr project easy instance launch` and plumb it as the launched agent runtime workdir.

## 2. Separate source-project resolution from runtime workdir

- [x] 2.1 Refactor managed launch plumbing so source project context, resolved roots, and runtime workdir are passed independently instead of deriving all launch state from one cwd value.
- [x] 2.2 Update `agents launch` source resolution so bare selectors use the invocation launch source context while explicit preset-path selectors use the resolved preset owner tree when a source Houmao project exists.
- [x] 2.3 Update `project easy instance launch` so overlay, specialist, runtime/jobs/mailbox roots, and source preset resolution stay pinned to the selected project overlay even when `--workdir` points elsewhere.
- [x] 2.4 Preserve the existing persisted manifest `working_directory` field and relaunch behavior while switching the CLI surface to `--workdir`.

## 3. Cover the new behavior with focused tests

- [x] 3.1 Add or update `agents launch` tests to cover omitted `--workdir`, explicit `--workdir`, source-overlay pinning, and explicit preset-path launches whose runtime workdir differs from the source project.
- [x] 3.2 Add or update `project easy instance launch` tests to cover explicit external `--workdir` while preserving the selected easy-project overlay and overlay-local roots.
- [x] 3.3 Add or update `agents join` tests and help assertions so the supported flag is `--workdir` and pane-path fallback still works when the flag is omitted.

## 4. Update docs and examples

- [x] 4.1 Update CLI reference pages for `agents launch`, `agents join`, and `project easy instance launch` to use `--workdir` and explain the source-project-versus-runtime-workdir split.
- [x] 4.2 Update relevant getting-started and easy-launch examples so operators can launch against one Houmao project while setting the agent runtime cwd explicitly.
