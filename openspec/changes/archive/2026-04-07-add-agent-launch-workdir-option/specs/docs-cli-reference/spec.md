## ADDED Requirements

### Requirement: Managed-launch CLI reference documents `--workdir` and source-project pinning
The CLI reference pages that document `houmao-mgr agents launch`, `houmao-mgr agents join`, and `houmao-mgr project easy instance launch` SHALL describe `--workdir` as the current public runtime-cwd flag.

That coverage SHALL describe the default behavior as using the invocation cwd for launch-time runtime workdir and tmux-pane current path for join-time adopted workdir when `--workdir` is omitted.

That coverage SHALL explain that `--workdir` sets the launched or adopted agent cwd and does not retarget launch source project resolution.

For `agents launch`, that coverage SHALL explain that when launch originates from a Houmao project, source overlay selection and overlay-local runtime/jobs roots remain pinned to that source project rather than following `--workdir`.

For `project easy instance launch`, that coverage SHALL explain that the selected easy-project overlay and specialist source remain authoritative even when `--workdir` points somewhere else.

That coverage SHALL NOT present `--working-directory` as part of the current public CLI for `agents join`.

#### Scenario: Reader sees `--workdir` on the managed launch surfaces
- **WHEN** a reader opens the CLI reference for `houmao-mgr agents launch`, `houmao-mgr agents join`, or `houmao-mgr project easy instance launch`
- **THEN** the documented runtime-cwd flag is `--workdir`
- **AND THEN** the reference does not describe `--working-directory` as the current join flag

#### Scenario: Reader understands source-project pinning for managed launch
- **WHEN** a reader looks up `houmao-mgr agents launch --workdir`
- **THEN** the reference explains that `--workdir` changes the launched agent cwd
- **AND THEN** it explains that source overlay/runtime/jobs resolution remains pinned to the launch source project when one exists

#### Scenario: Reader understands easy launch keeps the selected overlay even with external workdir
- **WHEN** a reader looks up `houmao-mgr project easy instance launch --workdir`
- **THEN** the reference explains that the selected project overlay and specialist source remain authoritative
- **AND THEN** it explains that `--workdir` only changes the launched agent cwd
