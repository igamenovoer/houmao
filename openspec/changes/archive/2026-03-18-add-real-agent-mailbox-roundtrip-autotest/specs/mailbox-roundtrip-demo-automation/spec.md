## MODIFIED Requirements

### Requirement: Mailbox roundtrip demo SHALL expose pack-local automation commands
The mailbox roundtrip tutorial pack SHALL expose pack-local automation through `run_demo.sh`, `autotest/run_autotest.sh`, and helper-owned scripts under `scripts/demo/mailbox-roundtrip-tutorial-pack/`.

`run_demo.sh` SHALL support command-style entrypoints for `auto`, `start`, `roundtrip`, `inspect`, `verify`, and `stop`.

`autotest/run_autotest.sh` SHALL be reserved for opt-in real-agent hack-through-testing cases and SHALL support case selection through `--case <case-id>`.

The default invocation of `run_demo.sh` MAY remain equivalent to the existing deterministic `auto` path, but the real-agent HTT path SHALL remain discoverable through the pack-owned `autotest/run_autotest.sh` harness rather than through an external wrapper only.

Each supported real-agent case SHALL also have an implemented companion pair under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/`: one `case-*.sh` file and one same-basename `case-*.md` companion document.

Shared shell libraries and reusable helper functions used by multiple cases SHALL live under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/helpers/`.

#### Scenario: Harness accepts explicit real-agent case execution
- **WHEN** a maintainer invokes `autotest/run_autotest.sh --case real-agent-roundtrip --demo-output-dir <path>`
- **THEN** the harness routes to the corresponding pack-owned real-agent testplan implementation
- **AND THEN** the selected case has a matching `autotest/case-real-agent-roundtrip.sh` executable and `autotest/case-real-agent-roundtrip.md` companion document in the tutorial-pack directory
- **AND THEN** any shared shell logic needed by that case comes from `autotest/helpers/` rather than being duplicated ad hoc across case scripts
- **AND THEN** the selected case writes its evidence under that same selected demo output directory
- **AND THEN** the caller does not need a separate manual script to access the canonical pack-owned HTT path

### Requirement: Stepwise automation SHALL reuse one selected demo output directory
The mailbox roundtrip demo automation commands SHALL operate against one caller-selected demo output directory and SHALL preserve the demo-local worktree, mailbox root, runtime root, and reusable state needed between commands.

`autotest/run_autotest.sh` SHALL either use the caller-selected demo output directory or create one case-owned output directory using a documented pack-local convention. In either path, the harness result SHALL report the exact demo output directory that contains the resulting mailbox evidence.

#### Scenario: Harness result reports the owned demo output directory
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-roundtrip`
- **THEN** the selected case records the exact demo output directory it used
- **AND THEN** the maintainer can inspect the finished mailbox artifacts from that reported location without re-running the demo
