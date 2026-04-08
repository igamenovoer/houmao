## ADDED Requirements

### Requirement: Legacy backend documentation carries an unmaintained deprecation banner

Any run-phase reference page that describes the `cao_rest` or `houmao_server_rest` backends SHALL open the relevant section with a prominent, bold-prefixed deprecation banner identifying the content as unmaintained and possibly incorrect.

At minimum, `docs/reference/realm_controller.md` SHALL include such a banner immediately before the descriptive content for `cao_rest` and immediately before the descriptive content for `houmao_server_rest`. The same banner SHALL appear on `docs/reference/codex-cao-approval-prompt-troubleshooting.md` after it is moved out of the retired agents subtree.

The banner SHALL state, at a minimum:

- that the backend remains in the codebase as a legacy escape hatch,
- that the documentation is no longer actively maintained,
- that the content below may be incorrect or stale,
- and that readers should prefer the current maintained backends (for example `local_interactive`) for new work.

The banner SHALL appear before any descriptive prose, option tables, or workflow diagrams for the deprecated backend. Inline mentions of `cao_rest` or `houmao_server_rest` in lists or tables (for example a backend enumeration) do not by themselves require the banner — only dedicated sections that describe how to use, configure, or troubleshoot the backend trigger the banner requirement.

#### Scenario: Reader opens the realm_controller reference page and reaches the cao_rest section

- **WHEN** a reader scrolls to the `cao_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the realm_controller reference page and reaches the houmao_server_rest section

- **WHEN** a reader scrolls to the `houmao_server_rest` section of `docs/reference/realm_controller.md`
- **THEN** a bold-prefixed deprecation banner appears before any descriptive prose
- **AND THEN** the banner states the backend is unmaintained and the content may be incorrect

#### Scenario: Reader opens the moved codex CAO approval troubleshooting page

- **WHEN** a reader opens `docs/reference/codex-cao-approval-prompt-troubleshooting.md`
- **THEN** a bold-prefixed deprecation banner appears at the top of the page
- **AND THEN** the banner states the content is retained only as historical troubleshooting for the deprecated `cao_rest` backend and may be incorrect
