## 1. Root CLI Behavior

- [x] 1.1 Add a root `--version` option to `houmao-mgr` that reports the packaged Houmao version and exits successfully without requiring a subcommand.
- [x] 1.2 Reuse the existing Houmao version helper so the root CLI and packaged metadata resolve version text through one canonical path.

## 2. Documentation

- [x] 2.1 Update `docs/reference/cli/houmao-mgr.md` so the root synopsis and root option coverage include `--version`.
- [x] 2.2 Document that `houmao-mgr --version` prints the packaged Houmao version and exits successfully without requiring a subcommand.

## 3. Verification

- [x] 3.1 Add unit coverage for `houmao-mgr --version` success behavior.
- [x] 3.2 Add unit coverage showing `houmao-mgr --help` includes the root `--version` option.
