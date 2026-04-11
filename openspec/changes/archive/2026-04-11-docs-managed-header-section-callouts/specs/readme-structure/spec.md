## MODIFIED Requirements

### Requirement: agents join is a secondary path (step 4)

Step 4 SHALL document `agents join` with the existing mermaid sequence diagram, step-by-step commands, and the capabilities table. It SHALL be introduced as the lightweight/ad-hoc path for users who already have a running coding agent and want management on top, not as the recommended starting point.

The managed-header callout block within or after step 4 SHALL describe the five-section architecture: `identity`, `houmao-runtime-guidance`, and `automation-notice` default enabled; `task-reminder` and `mail-ack` default disabled. The callout SHALL name `--managed-header-section SECTION=enabled|disabled` as the per-launch section override and `--no-managed-header` as the whole-header opt-out. The callout SHALL mention that the automation-notice section prevents interactive user-question tools and routes mailbox-driven clarification to reply-enabled mailbox threads. The callout SHALL link to the Managed Launch Prompt Header reference page.

#### Scenario: Reader understands section-level managed-header control from README

- **WHEN** a reader scans the managed-header callout block in README.md
- **THEN** they learn that the header has five sections with three on by default and two off
- **AND THEN** they see the `--managed-header-section` flag for per-launch section override
- **AND THEN** they see `--no-managed-header` for whole-header opt-out
- **AND THEN** they can follow the link to the reference page for the full section list, resolution precedence, and stored-profile policy
