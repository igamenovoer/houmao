## MODIFIED Requirements

### Requirement: Provisioned copied dummy-project workdir SHALL expose project-local mailbox skill documents
The tracked default gateway wake-up tutorial SHALL stage the runtime-owned mailbox skill documents into the provisioned copied dummy-project workdir before the live session starts.

The provisioned workdir SHALL expose the visible `skills/mailbox/...` mailbox skill surface only.

The tutorial pack SHALL NOT rely on runtime-home hidden mailbox skill paths or on `skills/.system/mailbox/...` copies for the default unattended wake-up turn.

#### Scenario: Copied dummy-project includes mailbox skill documents before start
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** the provisioned copied dummy-project workdir contains the projected mailbox skill documents under `skills/mailbox/...`
- **AND THEN** the default wake-up turn can use that project-local mailbox skill surface without rediscovering mailbox instructions elsewhere
- **AND THEN** the provisioned workdir does not depend on `skills/.system/mailbox/...` copies for mailbox-skill discovery
