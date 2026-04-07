## ADDED Requirements

### Requirement: CLI reference documents the root `houmao-mgr --version` option
The CLI reference page `docs/reference/cli/houmao-mgr.md` SHALL document `--version` as a root option on `houmao-mgr`.

That page SHALL include `--version` in the root synopsis or root option coverage alongside the existing root options.

That page SHALL explain that `houmao-mgr --version` prints the packaged Houmao version and exits successfully without requiring a subcommand.

#### Scenario: Reader sees `--version` in the houmao-mgr root option coverage
- **WHEN** a reader opens `docs/reference/cli/houmao-mgr.md`
- **THEN** the page documents `--version` as a root `houmao-mgr` option
- **AND THEN** the page does not imply that version reporting requires a subcommand

#### Scenario: Reader understands what the version option returns
- **WHEN** a reader looks up `houmao-mgr --version` in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page explains that the command prints the packaged Houmao version
- **AND THEN** it explains that the command exits successfully after reporting that version
