## ADDED Requirements

### Requirement: Docs index Subsystems block surfaces 0.8.0 capability pointers

The `docs/index.md` file SHALL surface the 0.8.0 subsystem capabilities — gateway control-request coalescing, mail-notifier context-recovery policy, lifecycle-aware managed-agent registry record, and the reuse-home / stop-relaunch run-phase flow — through its existing Subsystems block (or an immediately adjacent list) without requiring the reader to first open the per-subsystem index page.

For each of those four capabilities the landing page SHALL either:

- add a short capability-named pointer line under the corresponding subsystem entry (for example, "Gateway → control-request coalescing"), OR
- extend the existing one-line description with a capability-named link that points into the reference page or section that covers it.

The four pointers SHALL reach at minimum the pages listed below; deep fragment anchors are preferred but not required, and if a heading slug is not stable the link SHALL target the page itself with the capability named inline in the surrounding description:

| 0.8.0 capability | Target page |
|---|---|
| Gateway control-request coalescing | `docs/reference/gateway/contracts/protocol-and-state.md` (or the gateway internals page that owns the coalescing section) |
| Mail-notifier context-recovery policy | `docs/reference/gateway/operations/mail-notifier.md` |
| Lifecycle-aware managed-agent registry record (active, stopped, relaunching, retired) | `docs/reference/registry/contracts/record-and-layout.md` |
| Reuse-home fresh launch / stop-relaunch run-phase flow | `docs/reference/run-phase/session-lifecycle.md` |

The landing page SHALL NOT introduce a release-note style section (for example "What's new in 0.8.0") to carry these pointers; the pointers SHALL be placed inside the evergreen Subsystems and Run-phase structure that already exists.

The existing Subsystems block rows and their existing links (gateway index, mailbox index, tui-tracking state model, lifecycle completion detection, registry index, terminal-record index, system-files index) SHALL be preserved. This requirement is additive.

#### Scenario: Reader discovers gateway coalescing from the docs landing page

- **WHEN** a reader opens `docs/index.md` and scans the Subsystems and Run-phase sections
- **THEN** they find a pointer that names gateway control-request coalescing and links into a gateway reference page that documents it

#### Scenario: Reader discovers mail-notifier context recovery from the docs landing page

- **WHEN** a reader opens `docs/index.md` and scans the Subsystems and Run-phase sections
- **THEN** they find a pointer that names the mail-notifier context-recovery policy and links to `docs/reference/gateway/operations/mail-notifier.md`

#### Scenario: Reader discovers the lifecycle-aware registry record from the docs landing page

- **WHEN** a reader opens `docs/index.md` and scans the Subsystems and Run-phase sections
- **THEN** they find a pointer that names the lifecycle states (active, stopped, relaunching, retired) and links to `docs/reference/registry/contracts/record-and-layout.md`

#### Scenario: Reader discovers reuse-home and stop-relaunch from the docs landing page

- **WHEN** a reader opens `docs/index.md` and scans the Run-phase section
- **THEN** they find a pointer that names reuse-home or stop-relaunch and links to `docs/reference/run-phase/session-lifecycle.md`

#### Scenario: Landing page does not grow a release-note section

- **WHEN** inspecting `docs/index.md`
- **THEN** the file contains no "What's new in 0.8.0" heading or release-note section carrying the 0.8.0 capability pointers
- **AND THEN** the pointers are placed inside the existing evergreen Subsystems and Run-phase structure
